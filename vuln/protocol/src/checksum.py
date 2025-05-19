# CRC32 or sum‑based checksum implementation

import zlib


def compute_checksum(data: bytes) -> int:
    """
    Compute a simple 16-bit checksum using CRC32 truncated to 2 bytes.
    """
    return zlib.crc32(data) & 0xFFFF


def verify_checksum(data: bytes, checksum: int) -> bool:
    """
    Verify that `checksum` matches the data's computed checksum.
    """
    return compute_checksum(data) == checksum