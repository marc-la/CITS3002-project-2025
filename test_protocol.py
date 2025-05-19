import threading
import time
import socket
from protocol import send_message, receive_message, shutdown_logging

HOST = '127.0.0.1'
PORT = 9999

# The shared secret key for HMAC (must be agreed by both sides)
KEY = b'supersecretkey123'

test_message = (
    "Hello, this is a test message to check the protocol implementation. "
    "It should be split into multiple packets and sent over the socket. "
    "The server should receive it correctly and reassemble it. "
    "This is a longer message to ensure fragmentation and reassembly works. "
    "Good luck with your exams!"
    "Hello, this is a test message to check the protocol implementation. "
    "It should be split into multiple packets and sent over the socket. "
    "The server should receive it correctly and reassemble it. "
    "This is a longer message to ensure fragmentation and reassembly works. "
    "Good luck with your exams!"
    "Hello, this is a test message to check the protocol implementation. "
    "It should be split into multiple packets and sent over the socket. "
    "The server should receive it correctly and reassemble it. "
    "This is a longer message to ensure fragmentation and reassembly works. "
    "Good luck with your exams!"
    "Hello, this is a test message to check the protocol implementation. "
    "It should be split into multiple packets and sent over the socket. "
    "The server should receive it correctly and reassemble it. "
    "This is a longer message to ensure fragmentation and reassembly works. "
    "Good luck with your exams!"
    "Hello, this is a test message to check the protocol implementation. "
    "It should be split into multiple packets and sent over the socket. "
    "The server should receive it correctly and reassemble it. "
    "This is a longer message to ensure fragmentation and reassembly works. "
    "Good luck with your exams!"
    "Hello, this is a test message to check the protocol implementation. "
    "It should be split into multiple packets and sent over the socket. "
    "The server should receive it correctly and reassemble it. "
    "This is a longer message to ensure fragmentation and reassembly works. "
    "Good luck with your exams!"
)

def run_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        print("[Server] Waiting for connection...")
        conn, addr = s.accept()
        with conn:
            print(f"[Server] Connected by {addr}")
            try:
                received = receive_message(conn, key=KEY, max_skew=300, seen_nonces=None)
            except TypeError:
                # old version of receive_message just takes the socket
                received = receive_message(conn)
            print(f"[Server] Received message:\n{received.decode('utf-8')}\n")


def run_client():
    time.sleep(0.5)  # ensure server is ready
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print("[Client] Sending message...")
        try:
            send_message(s, test_message.encode('utf-8'), key=KEY, use_timestamp=True)
        except TypeError:
            # old version of send_message doesn’t accept key/use_timestamp
            send_message(s, test_message.encode('utf-8'))
        print("[Client] Message sent.")


def main():
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    try:
        run_client()
        server_thread.join(timeout=5)  # Wait for server to finish processing
    finally:
        shutdown_logging()  # Shutdown logging after all threads are done

if __name__ == '__main__':
    main()
