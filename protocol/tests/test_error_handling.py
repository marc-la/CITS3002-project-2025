# corrupted and out‑of‑sequence behaviour

import struct
import pytest
from src.packet import send_message,receive_message,Packet,PacketType,HEADER_FMT,HEADER_SIZE
from src.errors import SequenceError

class DummySocket:
    def __init__(self,chunks):
        self.chunks=list(chunks)
        self.sent=[]
    def recv(self,n):
        return self.chunks.pop(0) if self.chunks else b""
    def sendall(self,d):
        self.sent.append(d)


def make_pkt(m): return Packet(0,PacketType.DATA,m).pack()


def test_send_receive_roundtrip():
    msg=b"Hello"
    out=DummySocket([])
    send_message(out,msg)
    term=out.sent[-1]
    seq,ptype,length,cs=struct.unpack(HEADER_FMT,term[:HEADER_SIZE])
    assert ptype==PacketType.DATA.value and length==0
    raw=make_pkt(msg)+term
    inp=DummySocket([raw[:6],raw[6:]])
    assert receive_message(inp)==msg


def test_discard_corrupt():
    good=make_pkt(b"OK")
    bad=good[:HEADER_SIZE]+b"\xFF"+good[HEADER_SIZE+1:]
    term=struct.pack(HEADER_FMT,1,PacketType.DATA.value,0,0)
    sock=DummySocket([good,bad,term])
    assert receive_message(sock)==b"OK"


def test_close_header():
    sock=DummySocket([b"\x00"])
    with pytest.raises(ConnectionError): receive_message(sock)


def test_close_payload():
    hdr=struct.pack(HEADER_FMT,1,PacketType.DATA.value,4,0)
    sock=DummySocket([hdr,b"\x01"])
    with pytest.raises(ConnectionError): receive_message(sock)


def test_out_of_seq():
    p1=Packet(1,PacketType.DATA,b"A").pack()
    term=struct.pack(HEADER_FMT,1,PacketType.DATA.value,0,0)
    sock=DummySocket([p1,term])
    with pytest.raises(SequenceError): receive_message(sock)