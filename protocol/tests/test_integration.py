# round‑trip and artificial corruption stats

import pytest
from src.packet import Packet,PacketType,HEADER_SIZE
from src.errors import ChecksumError

def inject_error(raw,pos):
    h=raw[:HEADER_SIZE];p=bytearray(raw[HEADER_SIZE:])
    if p: p[pos%len(p)]^=0x01
    return h+bytes(p)

def test_error_stats(sample_payload):
    pkt=Packet(2,PacketType.DATA,sample_payload)
    raw=pkt.pack()
    count=0
    for i in range(30):
        with pytest.raises(ChecksumError): Packet.unpack(inject_error(raw,i))
        count+=1
    assert count==30