# client_vulnerable.py
import socket, struct, time
from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA256
import binascii

KEY = b"Sixteen byte key"
NONCE = b'\x00'*8
IV0    = 0

def make_packet(seq, payload: bytes) -> bytes:
    # 1. Timestamp
    ts = int(time.time())
    # 2. Build header+payload+timestamp
    hdr = struct.pack(">I", seq)
    tsb = struct.pack(">Q", ts)
    data_to_mac = hdr + payload + tsb
    # 3. HMAC over (SEQ||payload||TS)
    h = HMAC.new(KEY, digestmod=SHA256)
    h.update(data_to_mac)
    mac = h.digest()
    # 4. Assemble plaintext
    plaintext = data_to_mac + mac
    # 5. CRC16 over all but CRC field
    crc = binascii.crc_hqx(plaintext, 0).to_bytes(2, 'big')
    full = plaintext + crc
    # 6. Encrypt
    cipher = AES.new(KEY, AES.MODE_CTR, nonce=NONCE, initial_value=IV0)
    return cipher.encrypt(full)

def main():
    seq = 1
    payload = b"FIRE 3 4"

    pkt = make_packet(seq, payload)

    # Send via attacker proxy
    s = socket.create_connection(('localhost', 4000))
    print(f"[Client] Sending SEQ={seq}, payload={payload}")
    s.sendall(pkt)

    # Receive ACK/echo
    data = s.recv(4096)
    if data:
        # decrypt
        cipher = AES.new(KEY, AES.MODE_CTR, nonce=NONCE, initial_value=IV0)
        resp = cipher.decrypt(data)
        print(f"[Client] Got reply: {resp}")
    s.close()

if __name__ == "__main__":
    main()
