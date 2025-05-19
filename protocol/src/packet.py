import zlib
import hmac
import hashlib
import logging
import socket
import struct
import time
import os
from enum import Enum
from queue import Queue
from logging.handlers import QueueHandler, QueueListener
from .checksum import compute_checksum, verify_checksum
from .errors import ChecksumError, SequenceError, ReplayError
from ..crypto import encrypt_payload, decrypt_payload, generate_iv

# ------------------- Async Logging Setup ------------------------------
_log_queue = Queue()
_queue_handler = QueueHandler(_log_queue)
_file_handler = logging.FileHandler("protocol.log", mode="w", encoding="utf-8")
_file_handler.setLevel(logging.DEBUG)
_formatter = logging.Formatter(
    "%(asctime)s %(threadName)s %(name)s %(levelname)s %(message)s"
)
_file_handler.setFormatter(_formatter)
_listener = QueueListener(_log_queue, _file_handler, respect_handler_level=True)
_listener.start()

def shutdown_logging():
    """
    Stop the listener thread and flush all handlers.
    Call this at application exit to ensure all logs are written.
    """
    _listener.stop()
    for handler in (_file_handler,):
        try:
            handler.flush()
            handler.close()
        except Exception:
            pass

_logger = logging.getLogger("protocol.src.packet")
_logger.setLevel(logging.DEBUG)
_logger.addHandler(_queue_handler)
_logger.propagate = False

# -------------------  Packet Definition  ------------------------------
class PacketType(Enum):
    DATA = 0
    ACK = 1
    NACK = 2

# Header: seq_num (H), packet_type (B), length (H), checksum (H), freshness (Q), mac_length (B)
HEADER_FMT = ">H B H H Q B"
HEADER_BASE = struct.calcsize(HEADER_FMT)
MAC_ALGORITHM = 'sha256'
MAC_TRUNC = 16  # bytes to include
MAX_PAYLOAD = 512

class Packet:
    """
    Protocol packet with:
      - seq_num: 16-bit sequence number
      - packet_type: PacketType enum
      - length: payload length
      - checksum: 16-bit CRC truncated from CRC32
      - freshness: 64-bit timestamp or nonce
      - mac: truncated HMAC-SHA256
      - payload: up to MAX_PAYLOAD bytes
    """

    def __init__(self, seq_num: int, packet_type: PacketType, payload: bytes,
                 key: bytes, freshness: int):
        if not (0 <= seq_num < 2**16):
            raise ValueError("Sequence number must fit in 16 bits")
        if not isinstance(packet_type, PacketType):
            raise ValueError("packet_type must be a PacketType enum")
        if len(payload) > MAX_PAYLOAD:
            raise ValueError(f"Payload too large: max {MAX_PAYLOAD} bytes")

        self.seq_num = seq_num
        self.packet_type = packet_type
        self.key = key
        self.freshness = freshness

        # Encryption for DATA
        if packet_type == PacketType.DATA and payload:
            self.iv = generate_iv()
            encrypted = encrypt_payload(payload, self.iv)
            self.payload = self.iv + encrypted
            self.plaintext = payload
        else:
            self.iv = None
            self.payload = payload
            self.plaintext = payload

        self.length = len(self.payload)
        self.checksum = compute_checksum(self.payload)

        # Build header and compute MAC
        header = struct.pack(
            HEADER_FMT,
            self.seq_num,
            self.packet_type.value,
            self.length,
            self.checksum,
            self.freshness,
            MAC_TRUNC
        )
        full_mac = hmac.new(self.key, header + self.payload, MAC_ALGORITHM).digest()
        self.mac = full_mac[:MAC_TRUNC]

        _logger.debug(
            f"Packet created: seq_num={self.seq_num}, type={self.packet_type.name}, "
            f"freshness={self.freshness}, checksum={self.checksum}, mac={self.mac.hex()}, "
            f"length={self.length}, payload_preview={self.payload[:32]!r}{'...' if self.length > 32 else ''}"
        )

    def pack(self) -> bytes:
        header = struct.pack(
            HEADER_FMT,
            self.seq_num,
            self.packet_type.value,
            self.length,
            self.checksum,
            self.freshness,
            len(self.mac)
        )
        return header + self.mac + self.payload

    @classmethod
    def unpack(cls, raw: bytes, key: bytes,
               max_skew: int = None, seen_nonces: set = None):
        if len(raw) < HEADER_BASE:
            raise ValueError("Raw data too short for header")

        # Parse header and fields
        seq_num, pkt_type_val, length, recv_checksum, freshness, mac_len = struct.unpack(
            HEADER_FMT, raw[:HEADER_BASE]
        )
        pkt_type = PacketType(pkt_type_val)
        mac_start = HEADER_BASE
        mac_end = mac_start + mac_len
        recv_mac = raw[mac_start:mac_end]
        payload = raw[mac_end:mac_end + length]

        # Verify MAC
        header = raw[:mac_start]
        expected = hmac.new(key, header + payload, MAC_ALGORITHM).digest()[:mac_len]
        if not hmac.compare_digest(recv_mac, expected):
            raise ChecksumError(f"MAC mismatch on seq {seq_num}")

        # Freshness check
        if max_skew is not None:
            now = int(time.time())
            if abs(now - freshness) > max_skew:
                raise ReplayError(f"Timestamp out of skew: got {freshness}, now {now}")
        elif seen_nonces is not None:
            if freshness in seen_nonces:
                raise ReplayError(f"Nonce replay: {freshness}")
            seen_nonces.add(freshness)

        # Verify checksum
        if not verify_checksum(payload, recv_checksum):
            raise ChecksumError(f"Bad checksum on seq {seq_num}")

        # Instantiate without re-running __init__
        pkt = object.__new__(cls)
        pkt.seq_num = seq_num
        pkt.packet_type = pkt_type
        pkt.key = key
        pkt.freshness = freshness
        pkt.length = length
        pkt.checksum = recv_checksum
        pkt.mac = recv_mac
        pkt.payload = payload

        # Decrypt if DATA
        if pkt_type == PacketType.DATA and length > 16:
            iv = payload[:16]
            encrypted = payload[16:]
            decrypted = decrypt_payload(encrypted, iv)
            pkt.iv = iv
            pkt.plaintext = decrypted
        else:
            pkt.iv = None
            pkt.plaintext = payload

        _logger.debug(
            f"Packet unpacked: seq_num={pkt.seq_num}, type={pkt.packet_type.name}, "
            f"freshness={pkt.freshness}, checksum={pkt.checksum}, mac={pkt.mac.hex()}, "
            f"length={pkt.length}, payload_preview={pkt.payload[:32]!r}{'...' if pkt.length > 32 else ''}"
        )
        return pkt

# -------------------  Transport Helpers  ------------------------------

def send_message(sock: socket.socket, message: bytes,
                 key: bytes, use_timestamp: bool = True) -> None:
    """
    Fragment message into DATA packets with freshness (timestamp or nonce), send all, then terminator.
    """
    seq = 0
    offset = 0
    while offset < len(message):
        chunk = message[offset:offset + MAX_PAYLOAD]
        freshness = int(time.time()) if use_timestamp else struct.unpack(
            ">Q", os.urandom(8)
        )[0]
        pkt = Packet(seq, PacketType.DATA, chunk, key, freshness)
        _logger.debug(f"Sending DATA seq={seq}, freshness={freshness}, size={len(chunk)}")
        sock.sendall(pkt.pack())
        offset += len(chunk)
        seq = (seq + 1) % (2**16)
    freshness = int(time.time()) if use_timestamp else struct.unpack(
        ">Q", os.urandom(8)
    )[0]
    term = Packet(seq, PacketType.DATA, b"", key, freshness)
    _logger.debug(f"Sending terminator seq={seq}, freshness={freshness}")
    sock.sendall(term.pack())


def receive_message(sock: socket.socket,
                    key: bytes,
                    max_skew: int = None,
                    seen_nonces: set = None) -> bytes:
    """
    Receive DATA packets until empty DATA packet, validate sequence, freshness, and MAC.
    Raises SequenceError, ChecksumError, ReplayError on violations.
    """
    buffers = {}
    expected_seq = 0

    while True:
        hdr = sock.recv(HEADER_BASE)
        if not hdr:
            raise ConnectionError("Socket closed during header recv")
        _, _, length, _, _, mac_len = struct.unpack(HEADER_FMT, hdr)
        mac_and_payload = sock.recv(mac_len + length)
        raw = hdr + mac_and_payload

        seq_num, pkt_type_val, _, _, _, _ = struct.unpack(
            HEADER_FMT, raw[:HEADER_BASE]
        )
        if pkt_type_val == PacketType.NACK.value:
            _logger.info(f"Received NACK for seq={seq_num}; ignoring")
            continue

        try:
            pkt = Packet.unpack(raw, key, max_skew=max_skew, seen_nonces=seen_nonces)
        except ReplayError as e:
            _logger.error(f"ReplayError: {e}")
            raise
        except ChecksumError as e:
            _logger.error(f"ChecksumError: {e}")
            raise
        except SequenceError as e:
            _logger.error(f"SequenceError: {e}")
            raise

        if pkt.packet_type == PacketType.DATA and pkt.length == 0:
            _logger.debug(f"Terminator received seq={pkt.seq_num}")
            break

        if pkt.seq_num != expected_seq:
            raise SequenceError(f"Expected {expected_seq}, got {pkt.seq_num}")

        buffers[pkt.seq_num] = pkt.plaintext
        expected_seq = (expected_seq + 1) & 0xFFFF

    return b"".join(buffers[i] for i in range(expected_seq))
