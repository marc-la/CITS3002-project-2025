from Crypto.Cipher import AES
from .key import SHARED_KEY

def encrypt_payload(plaintext: bytes, iv: bytes) -> bytes:
    cipher = AES.new(SHARED_KEY, AES.MODE_CTR, nonce=b'', initial_value=iv)
    return cipher.encrypt(plaintext)

def decrypt_payload(ciphertext: bytes, iv: bytes) -> bytes:
    cipher = AES.new(SHARED_KEY, AES.MODE_CTR, nonce=b'', initial_value=iv)
    return cipher.decrypt(ciphertext)

if __name__ == "__main__":
    from .key import generate_iv
    plaintext = b"Hello, world!"
    iv = generate_iv()
    ciphertext = encrypt_payload(plaintext, iv)
    decrypted = decrypt_payload(ciphertext, iv)
    print("Plaintext:", plaintext)
    print("Ciphertext:", ciphertext)
    print("Decrypted:", decrypted)