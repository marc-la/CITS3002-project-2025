from .src.checksum import compute_checksum, verify_checksum
from .src.errors import ChecksumError, SequenceError, ReplayError

###############################################################

# This is a flag to enable or disable HMAC protection
# Set to True to enable HMAC protection, False to disable it
ENABLE_HMAC_PROTECTION = True

###############################################################

if ENABLE_HMAC_PROTECTION:
    from .src.packet_fixed import Packet, PacketType, send_message, receive_message, shutdown_logging, MAX_PAYLOAD, HEADER_FMT
else:
    from .src.packet_vuln import Packet, PacketType, send_message, receive_message, shutdown_logging, MAX_PAYLOAD, HEADER_FMT