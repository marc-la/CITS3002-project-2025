# Packet class: header fields, pack()/unpack()

import logging
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
import socket
import struct
from enum import Enum
from .checksum import compute_checksum, verify_checksum
from .errors import ChecksumError, SequenceError
from ..crypto import encrypt_payload, decrypt_payload, generate_iv

# ------------------- Async Logging Setup ------------------------------

# 1. Create a shared, thread‑safe queue
_log_queue = Queue()  # unlimited size by default

# 2. Configure protocol logger to enqueue
_queue_handler = QueueHandler(_log_queue)

# 3. Create real handlers (file, console, etc.)
_file_handler = logging.FileHandler("protocol.log", mode="w", encoding="utf-8")
_file_handler.setLevel(logging.DEBUG)
_formatter = logging.Formatter(
    "%(asctime)s %(threadName)s %(name)s %(levelname)s %(message)s"
)
_file_handler.setFormatter(_formatter)

# 4. Start listener thread
_listener = QueueListener(
    _log_queue,
    _file_handler,
    respect_handler_level=True
)
_listener.start()  # spins off background thread

# Provide a clean shutdown hook
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
_logger.propagate = False  # Prevent propagation to root logger

# -------------------  Packet Definition  ------------------------------

class PacketType(Enum):
    DATA = 0
    ACK = 1
    NACK = 2

# Header: seq_num (H), packet_type (B), length (H), checksum (H)
HEADER_FMT = ">H B H H"
HEADER_SIZE = struct.calcsize(HEADER_FMT)
MAX_PAYLOAD = 512  # maximum bytes per packet

class Packet:
    """
    Protocol packet with:
      - seq_num: 16-bit sequence number
      - packet_type: PacketType enum
      - length: payload length
      - checksum: 16-bit CRC truncated from CRC32
      - payload: up to MAX_PAYLOAD bytes
    """

    def __init__(self, seq_num: int, packet_type: PacketType, payload: bytes):
        if not (0 <= seq_num < 2**16):
            raise ValueError("Sequence number must fit in 16 bits")
        if not isinstance(packet_type, PacketType):
            raise ValueError("packet_type must be a PacketType enum")
        if len(payload) > MAX_PAYLOAD:
            raise ValueError(f"Payload too large: max {MAX_PAYLOAD} bytes")

        self.seq_num = seq_num
        self.packet_type = packet_type

        if packet_type == PacketType.DATA and payload:
            self.iv = generate_iv()
            _logger.debug(f"[INIT] Plaintext before encryption (seq={seq_num}): {payload[:32]!r}")
            encrypted_payload = encrypt_payload(payload, self.iv)
            self.payload = self.iv + encrypted_payload
            _logger.debug(f"[INIT] Encrypted payload (seq={seq_num}): {self.payload[:32]!r}")
            self.plaintext = payload
        else:
            self.iv = None
            self.payload = payload
            self.plaintext = payload

        self.length = len(self.payload)
        self.checksum = compute_checksum(self.payload)

        _logger.debug(
            f"Packet created: seq_num={seq_num}, type={packet_type.name}, "
            f"length={len(payload)}, checksum={self.checksum}, "
            f"payload_preview={self.payload[:32]!r}{'...' if len(self.payload) > 32 else ''}"
        )

    def pack(self) -> bytes:
        header = struct.pack(
            HEADER_FMT,
            self.seq_num,
            self.packet_type.value,
            self.length,
            self.checksum,
        )
        return header + self.payload

    @classmethod
    def unpack(cls, raw: bytes) -> "Packet":
        if len(raw) < HEADER_SIZE:
            raise ValueError("Raw data too short for header")

        seq_num, pkt_type_val, length, recv_checksum = struct.unpack(
            HEADER_FMT, raw[:HEADER_SIZE]
        )
        try:
            packet_type = PacketType(pkt_type_val)
        except ValueError:
            raise ValueError(f"Unknown packet type: {pkt_type_val}")

        expected_total = HEADER_SIZE + length
        if len(raw) != expected_total:
            raise ValueError(f"Expected {expected_total} bytes, got {len(raw)}")

        payload = raw[HEADER_SIZE:]
        if not verify_checksum(payload, recv_checksum):
            raise ChecksumError(f"Bad checksum on seq {seq_num}")

        if packet_type == PacketType.DATA and length > 16:
            iv = payload[:16]
            encrypted = payload[16:]
            decrypted = decrypt_payload(encrypted, iv)
            _logger.debug(f"[UNPACK] Decrypted payload (seq={seq_num}): {decrypted[:32]!r}")
            pkt = cls(seq_num, packet_type, decrypted)
            pkt.iv = iv
            pkt.payload = payload  # still store original iv + ciphertext
            pkt.plaintext = decrypted  # store decrypted version
            return pkt
        else:
            return cls(seq_num, packet_type, payload)

# ---------====---- Transport helpers with fragmentation and reassembly ---------------

def send_message(sock: socket.socket, message: bytes) -> None:
    """
    Break message into DATA packets, send in order, then terminal DATA packet with empty payload.
    """
    seq = 0
    offset = 0
    while offset < len(message):
        chunk = message[offset:offset + MAX_PAYLOAD]
        pkt = Packet(seq, PacketType.DATA, chunk)
        _logger.debug(f"Sending DATA packet: sequence={pkt.seq_num}, payload_size={pkt.length} bytes")
        sock.sendall(pkt.pack())
        offset += len(chunk)
        seq = (seq + 1) % (2**16)
    terminator = Packet(seq, PacketType.DATA, b"")
    _logger.debug(f"Sending end-of-message marker (sequence={terminator.seq_num})")
    sock.sendall(terminator.pack())


def receive_message(sock: socket.socket) -> bytes:
    """
    Receive DATA packets until empty DATA packet received.
    Validate sequence, NACK corrupted, raise on out-of-order.
    """
    buffers = {}
    expected_seq = 0

    while True:
        hdr = sock.recv(HEADER_SIZE)
        if not hdr:
            raise ConnectionError("Socket closed before header")
        seq_num, pkt_type_val, length, checksum = struct.unpack(HEADER_FMT, hdr)
        payload = sock.recv(length) if length else b""

        _logger.debug(f"Received packet header: sequence={seq_num}, payload_length={length} bytes")

        if pkt_type_val == PacketType.NACK.value:
            _logger.info(f"Received NACK for packet {seq_num}; will retransmit that sequence")
            continue  # don’t treat as terminator

        # DATA terminator
        if pkt_type_val == PacketType.DATA.value and length == 0:
            _logger.debug(f"Received end-of-message marker (sequence={seq_num}); reassembly complete")
            break

        # Normal DATA packet
        try:
            pkt = Packet.unpack(hdr + payload)
        except ChecksumError:
            _logger.warning(f"Payload corruption detected in packet {seq_num}; issuing NACK to request retransmission")
            sock.sendall(Packet(seq_num, PacketType.NACK, b"").pack())
            continue

        if pkt.seq_num != expected_seq:
            raise SequenceError(f"Expected seq={expected_seq}, got={pkt.seq_num}")

        buffers[pkt.seq_num] = pkt.plaintext
        expected_seq = (expected_seq + 1) & 0xFFFF

    return b"".join(buffers[i] for i in range(expected_seq))