# checksum generation/verification

import zlib
import pytest
from src.checksum import compute_checksum, verify_checksum

def test_compute_checksum_matches():
    data=b"ABC"
    assert compute_checksum(data)==(zlib.crc32(data)&0xFFFF)

def test_verify_true(sample_payload):
    cs=compute_checksum(sample_payload)
    assert verify_checksum(sample_payload,cs)

def test_verify_false(sample_payload):
    assert not verify_checksum(sample_payload,cs^0xFFFF)