# Custom exceptions (ChecksumError, SequenceError)

class ChecksumError(Exception):
    """
    Raised when a packet's checksum verification fails.
    """
    pass


class SequenceError(Exception):
    """
    Reserved for handling out-of-sequence packets.
    """
    pass

class ReplayError(Exception):
    """
    Raised when a packet fails freshness check (replay).
    """
    pass