import pytest
from protocol import Packet, PacketType, MAX_PAYLOAD, HEADER_SIZE
from protocol import compute_checksum
from protocol import ChecksumError, SequenceError
import struct

# --- Helper function to simulate network corruption ---
def corrupt_packet_bytes(packet_bytes: bytes) -> bytes:
    corrupted = bytearray(packet_bytes)
    corrupted[-1] ^= 0xFF  # flip last byte
    return bytes(corrupted)

def test_packet_pack_unpack_roundtrip():
    payload = b"Test payload"
    pkt_out = Packet(1, PacketType.DATA, payload)
    packed = pkt_out.pack()
    pkt_in = Packet.unpack(packed)
    assert pkt_in.seq_num == pkt_out.seq_num
    assert pkt_in.packet_type == pkt_out.packet_type
    assert pkt_in.payload == pkt_out.payload


def test_checksum_detection():
    payload = b"Corrupt me"
    pkt = Packet(42, PacketType.DATA, payload)
    corrupted_bytes = corrupt_packet_bytes(pkt.pack())

    with pytest.raises(ChecksumError):
        Packet.unpack(corrupted_bytes)


def test_out_of_order_sequence():
    from protocol import receive_message
    import socket

    # create a fake socket using socketpair
    server_sock, client_sock = socket.socketpair()

    # Send two packets manually
    pkt1 = Packet(1, PacketType.DATA, b"hello")
    pkt2 = Packet(0, PacketType.DATA, b"out of order")
    client_sock.sendall(pkt1.pack())
    client_sock.sendall(pkt2.pack())

    # Terminate message
    client_sock.sendall(Packet(2, PacketType.DATA, b"").pack())

    with pytest.raises(SequenceError):
        receive_message(server_sock)

    server_sock.close()
    client_sock.close()


def test_packet_too_large():
    with pytest.raises(ValueError):
        Packet(0, PacketType.DATA, b"x" * (MAX_PAYLOAD + 1))
