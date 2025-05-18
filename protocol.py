import struct
import socket
import time
import logging
from config import DEBUG
from enum import IntEnum

# ----------- Protocol Constants -------------------

MAX_PAYLOAD = 32
PACKET_FORMAT = "!H B H H"  # SEQ (2 bytes), TYPE (1 byte), CHECKSUM (2 bytes), LENGTH (2 bytes)
HEADER_SIZE = struct.calcsize(PACKET_FORMAT)  # Should be 7 bytes


# ----------- Protocol Objects  -------------------

class Packet:
    """
    Class Packet.

    Represents a packet with a sequence number, type, and payload.

    Attributes:
        seq (int): Sequence number of the packet.
        pkt_type (int): Type of the packet (data, ack, etc.).
        payload (bytes): Payload data of the packet.
    """
    def __init__(self, seq, pkt_type, payload):
        self.seq = seq
        self.pkt_type = pkt_type
        self.payload = payload

    def to_bytes(self):
        header = struct.pack('!H B', self.seq, self.pkt_type)
        cs = checksum(header + self.payload)
        length = len(self.payload)
        return struct.pack(PACKET_FORMAT, self.seq, self.pkt_type, cs, length) + self.payload

    @staticmethod
    def from_bytes(data):
        seq, pkt_type, cs, length = struct.unpack(PACKET_FORMAT, data[:HEADER_SIZE])
        payload = data[HEADER_SIZE:HEADER_SIZE+length]
        header = struct.pack('!H B', seq, pkt_type)
        if checksum(header + payload) != cs:
            raise ValueError("Checksum failed")
        return Packet(seq, pkt_type, payload)

class PacketType(IntEnum):
    DATA = 0x01
    ACK = 0x02
    NACK = 0x03
    END = 0x04
    DONE = 0x05  # <-- Add this for shutdown handshake

# ---------- Protocol Functions -------------------

def checksum(data: bytes) -> int:
    return sum(data) % 65536

def build_packet(seq: int, pkt_type: int, payload: bytes) -> bytes:
    header = struct.pack('!H B', seq, pkt_type)
    cs = checksum(header + payload)
    length = len(payload)
    full_packet = struct.pack(PACKET_FORMAT, seq, pkt_type, cs, length) + payload
    return full_packet

def send_packets(message: str, conn: socket.socket, debug=DEBUG):
    message_bytes = message.encode('utf-8')
    packets = []
    seq = 0

    # Split message into multiple packets
    for i in range(0, len(message_bytes), MAX_PAYLOAD):
        chunk = message_bytes[i:i+MAX_PAYLOAD]
        packet = Packet(seq, PacketType.DATA, chunk)
        packets.append(packet)
        seq += 1

    # Add END packet to mark end of message
    end_packet = Packet(seq, PacketType.END, b'')
    packets.append(end_packet)

    acks = set()
    start_time = time.time() if debug else None
    while len(acks) < len(packets):
        for i, pkt in enumerate(packets):
            if i not in acks:
                conn.send(pkt.to_bytes())
                if debug:
                    elapsed = time.time() - start_time
                    logging.debug(f"[send][{elapsed:.3f}s] Sent packet {i}")

        try:
            conn.settimeout(0.1)
            ack_data = conn.recv(1024)
            offset = 0
            while offset + HEADER_SIZE <= len(ack_data):
                try:
                    ack_pkt = Packet.from_bytes(ack_data[offset:offset+HEADER_SIZE])
                except Exception:
                    break
                if ack_pkt.pkt_type == PacketType.ACK:
                    acks.add(ack_pkt.seq)
                    if debug:
                        elapsed = time.time() - start_time
                        logging.debug(f"[send][{elapsed:.3f}s] Received ACK for packet {ack_pkt.seq}")
                elif ack_pkt.pkt_type == PacketType.NACK:
                    if debug:
                        elapsed = time.time() - start_time
                        logging.debug(f"[send][{elapsed:.3f}s] Retransmit requested for packet {ack_pkt.seq}")
                offset += HEADER_SIZE
        except socket.timeout:
            if debug:
                elapsed = time.time() - start_time
                logging.debug(f"[send][{elapsed:.3f}s] Timeout, resending unacknowledged packets...")

    # Send final acknowledgment to indicate all packets were received
    final_ack = Packet(seq + 1, PacketType.ACK, b'')
    conn.send(final_ack.to_bytes())
    if debug:
        elapsed = time.time() - start_time
        logging.debug(f"[send][{elapsed:.3f}s] Sent final acknowledgment to server.")

    # Wait for final DONE from receiver before closing
    try:
        conn.settimeout(2.0)
        done_data = conn.recv(HEADER_SIZE)
        done_pkt = Packet.from_bytes(done_data)
        if done_pkt.pkt_type == PacketType.DONE:
            if debug:
                elapsed = time.time() - start_time
                logging.debug(f"[send][{elapsed:.3f}s] Received DONE from receiver.")
    except Exception as e:
        if debug:
            logging.debug(f"[send] Exception waiting for DONE: {e}")

    if debug:
        elapsed = time.time() - start_time
        logging.debug(f"[send] Total time elapsed: {elapsed:.3f}s")

def recv_all(conn, n):
    data = b''
    while len(data) < n:
        chunk = conn.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Socket closed")
        data += chunk
    return data

def receive_packets(conn: socket.socket, debug=DEBUG) -> str:
    received_packets = {}
    start_time = time.time() if debug else None
    end_seq = None
    while True:
        try:
            header = recv_all(conn, HEADER_SIZE)
            seq, pkt_type, cs, length = struct.unpack(PACKET_FORMAT, header)
            payload = recv_all(conn, length) if length > 0 else b''
            try:
                pkt = Packet.from_bytes(header + payload)
            except ValueError:
                if debug:
                    elapsed = time.time() - start_time
                    logging.debug(f"[receive][{elapsed:.3f}s] Checksum failed for packet {seq}")
                nack = Packet(seq, PacketType.NACK, b'')
                conn.send(nack.to_bytes())
                if debug:
                    elapsed = time.time() - start_time
                    logging.debug(f"[receive][{elapsed:.3f}s] Sent NACK for packet {seq}")
                continue

            if pkt.pkt_type == PacketType.DATA:
                received_packets[pkt.seq] = pkt.payload
                ack = Packet(pkt.seq, PacketType.ACK, b'')
                conn.send(ack.to_bytes())
                if debug:
                    elapsed = time.time() - start_time
                    logging.debug(f"[receive][{elapsed:.3f}s] Sent ACK for packet {pkt.seq}")

            elif pkt.pkt_type == PacketType.END:
                conn.send(Packet(pkt.seq, PacketType.ACK, b'').to_bytes())
                end_seq = pkt.seq
                if debug:
                    elapsed = time.time() - start_time
                    logging.debug(f"[receive][{elapsed:.3f}s] Sent ACK for END packet {pkt.seq}")
                break  # <-- break after END

            elif pkt.pkt_type == PacketType.ACK:
                if debug:
                    elapsed = time.time() - start_time
                    logging.debug(f"[receive][{elapsed:.3f}s] Final acknowledgment received. Closing connection.")
                if received_packets:
                    break
        except socket.timeout:
            continue

    # After END, send DONE to sender to signal safe shutdown
    try:
        conn.send(Packet((end_seq or 0) + 1, PacketType.DONE, b'').to_bytes())
        if debug:
            elapsed = time.time() - start_time
            logging.debug(f"[receive][{elapsed:.3f}s] Sent DONE to sender.")
    except Exception as e:
        if debug:
            logging.debug(f"[receive] Exception sending DONE: {e}")

    if not received_packets:
        if debug:
            elapsed = time.time() - start_time
            logging.debug(f"[receive][{elapsed:.3f}s] No data packets received.")
        return ""
    ordered = [received_packets[i] for i in sorted(received_packets.keys())]
    full_data = b''.join(ordered)
    if debug:
        elapsed = time.time() - start_time
        logging.debug(f"[receive] Total time elapsed: {elapsed:.3f}s")
    return full_data.decode('utf-8')