from Crypto.Cipher import AES
from .key import SHARED_KEY

def encrypt_payload(plaintext: bytes, iv: bytes) -> bytes:
    cipher = AES.new(SHARED_KEY, AES.MODE_CTR, nonce=b'', initial_value=iv)
    return cipher.encrypt(plaintext)

def decrypt_payload(ciphertext: bytes, iv: bytes) -> bytes:
    cipher = AES.new(SHARED_KEY, AES.MODE_CTR, nonce=b'', initial_value=iv)
    return cipher.decrypt(ciphertext)