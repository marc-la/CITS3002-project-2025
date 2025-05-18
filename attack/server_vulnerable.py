# server_vulnerable.py
import socket, struct, time
from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA256
import binascii

KEY = b"Sixteen byte key"
NONCE = b'\x00'*8
IV0    = 0
MAX_DELAY = 5  # seconds

def recv_loop(conn):
    """
    Keep receiving packets on this connection until closed or timeout.
    """
    conn.settimeout( MAX_DELAY + 2 )
    while True:
        try:
            data = conn.recv(4096)
            if not data:
                print("[Server] Client closed connection.")
                break
        except socket.timeout:
            print("[Server] No data for timeout period; closing.")
            break

        handle_packet(data, conn)

def handle_packet(enc_packet, conn):
    """
    Decrypt, verify CRC, HMAC, timestamp, then echo back or drop.
    """
    # 1. Decrypt AES-CTR
    cipher = AES.new(KEY, AES.MODE_CTR, nonce=NONCE, initial_value=IV0)
    plaintext = cipher.decrypt(enc_packet)

    # 2. Split fields
    #    [SEQ(4) || payload || TS(8) || HMAC(32) || CRC16(2)]
    if len(plaintext) < (4 + 8 + 32 + 2):
        print("[Server] Packet too short; dropping.")
        return

    seq = struct.unpack(">I", plaintext[:4])[0]
    crc_recv = struct.unpack(">H", plaintext[-2:])[0]
    mac_recv = plaintext[-(2+32):-2]
    ts_bytes = plaintext[-(2+32+8):-(2+32)]
    payload = plaintext[4: len(plaintext) - (8+32+2)]

    # 3. CRC check
    if binascii.crc_hqx(plaintext[:-2], 0) != crc_recv:
        print(f"[Server] CRC failed; dropping SEQ={seq}")
        return

    # 4. HMAC verify
    h = HMAC.new(KEY, digestmod=SHA256)
    h.update( plaintext[: 4 + len(payload) + 8 ] )  # SEQ||payload||TS
    try:
        h.verify(mac_recv)
    except ValueError:
        print(f"[Server] HMAC mismatch; dropping SEQ={seq}")
        return

    # 5. Timestamp freshness
    ts = struct.unpack(">Q", ts_bytes)[0]
    now = int(time.time())
    if abs(now - ts) > MAX_DELAY:
        print(f"[Server] Timestamp {ts} expired (now={now}); dropping SEQ={seq}")
        return

    # 6. Accept packet
    print(f"[Server] ✅ Accepted SEQ={seq}, payload={payload}, ts={ts}")

    # 7. Echo an ACK back (encrypted in same CTR stream)
    reply_plain = payload   # for demo we echo the payload
    cipher2 = AES.new(KEY, AES.MODE_CTR, nonce=NONCE, initial_value=IV0)
    conn.sendall(cipher2.encrypt(reply_plain))

if __name__ == "__main__":
    HOST, PORT = '0.0.0.0', 5000
    srv = socket.socket()
    srv.bind((HOST, PORT))
    srv.listen(1)
    print(f"[Server] Listening on port {PORT} (fixed protocol)")
    conn, addr = srv.accept()
    print(f"[Server] Connection from {addr}")
    recv_loop(conn)
    conn.close()
    srv.close()
    print("[Server] Shutdown.")