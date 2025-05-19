from Crypto.Random import get_random_bytes

# Shared secret key (normally out-of-band)
SHARED_KEY = b"leweisupersecret"  # 16 bytes for AES-128

def generate_iv() -> bytes:
    return get_random_bytes(16)  # 128-bit IV for AES-CTR