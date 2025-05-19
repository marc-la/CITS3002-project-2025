# RUN: `python3 -m protocol.stats_demo`` from root directory.

import random
from . import Packet, PacketType, MAX_PAYLOAD, ChecksumError

def inject_random_bit_error(data: bytes, probability: float = 0.01) -> bytes:
    """
    Randomly flip bits in the data with a given bit flip probability.
    """
    corrupted = bytearray(data)
    for i in range(len(corrupted)):
        for bit in range(8):
            if random.random() < probability:
                corrupted[i] ^= (1 << bit)
    return bytes(corrupted)

def simulate_packet_corruption_detection(num_trials=1000, error_prob=0.01):
    """
    Create packets, corrupt them with a given bit error probability,
    and count how many checksum mismatches are detected.
    """
    detected = 0
    undetected = 0

    for i in range(num_trials):
        payload = bytes(random.getrandbits(8) for _ in range(random.randint(20, MAX_PAYLOAD)))
        pkt = Packet(seq_num=i % 65536, packet_type=PacketType.DATA, payload=payload)
        packed = pkt.pack()

        corrupted = inject_random_bit_error(packed, probability=error_prob)

        try:
            Packet.unpack(corrupted)  # This calls verify_checksum internally
        except ChecksumError:
            detected += 1
        except Exception:
            pass  # ignore other errors for stats (e.g., bad header/format)
        else:
            if payload != corrupted[len(corrupted) - len(payload):]:
                undetected += 1  # corrupted, but not detected

    print(f"Total trials: {num_trials}")
    print(f"Checksum detected corrupted packets: {detected}")
    print(f"Undetected corrupted packets (false negatives): {undetected}")
    print(f"Detection rate: {100 * detected / num_trials:.2f}%")

if __name__ == "__main__":
    simulate_packet_corruption_detection(
        num_trials=5000,
        error_prob=0.002  # Low error rate (~1 bit every 500 bits)
    )
