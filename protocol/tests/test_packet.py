# pack/unpack tests

import pytest
import struct
from src.packet import Packet, PacketType, HEADER_FMT, HEADER_SIZE
from src.errors import ChecksumError

def test_pack_unpack(sample_payload):
    pkt=Packet(7,PacketType.DATA,sample_payload)
    raw=pkt.pack()
    pkt2=Packet.unpack(raw)
    assert pkt2.seq_num==7
    assert pkt2.packet_type==PacketType.DATA
    assert pkt2.payload==sample_payload


def test_short_header():
    with pytest.raises(ValueError):
        Packet.unpack(b"\x00")


def test_length_mismatch(sample_payload):
    pkt=Packet(0,PacketType.DATA,sample_payload)
    raw=pkt.pack()+b"X"
    with pytest.raises(ValueError):
        Packet.unpack(raw)


def test_bad_checksum(sample_payload):
    pkt=Packet(1,PacketType.DATA,sample_payload)
    raw=pkt.pack()
    bad=raw[:HEADER_SIZE]+bytes([raw[HEADER_SIZE]^0xFF])+raw[HEADER_SIZE+1:]
    with pytest.raises(ChecksumError):
        Packet.unpack(bad)