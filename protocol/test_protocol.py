import threading
import time
from src.packet import receive_message, send_message  # updated import

def test_protocol():
    import socket

    HOST = '127.0.0.1'
    PORT = 9999

    # Message to send
    test_message = (
        "Hello, this is a test message to check the protocol implementation. "
        "It should be split into multiple packets and sent over the socket. "
        "The server should receive it correctly and reassemble it. "
        "Ligma balls I hate my life. I wanna finish exams and go on holiday."
        "Hello, this is a test message to check the protocol implementation. "
        "It should be split into multiple packets and sent over the socket. "
        "The server should receive it correctly and reassemble it. "
        "Ligma balls I hate my life. I wanna finish exams and go on holiday."
        "Hello, this is a test message to check the protocol implementation. "
        "It should be split into multiple packets and sent over the socket. "
        "The server should receive it correctly and reassemble it. "
        "Ligma balls I hate my life. I wanna finish exams and go on holiday."
        "Hello, this is a test message to check the protocol implementation. "
        "It should be split into multiple packets and sent over the socket. "
        "The server should receive it correctly and reassemble it. "
        "Ligma balls I hate my life. I wanna finish exams and go on holiday."
        "Hello, this is a test message to check the protocol implementation. "
        "It should be split into multiple packets and sent over the socket. "
        "The server should receive it correctly and reassemble it. "
        "Ligma balls I hate my life. I wanna finish exams and go on holiday."
        "Hello, this is a test message to check the protocol implementation. "
        "It should be split into multiple packets and sent over the socket. "
        "The server should receive it correctly and reassemble it. "
        "Ligma balls I hate my life. I wanna finish exams and go on holiday."
        "Hello, this is a test message to check the protocol implementation. "
        "It should be split into multiple packets and sent over the socket. "
        "The server should receive it correctly and reassemble it. "
        "Ligma balls I hate my life. I wanna finish exams and go on holiday."
        "Hello, this is a test message to check the protocol implementation. "
        "It should be split into multiple packets and sent over the socket. "
        "The server should receive it correctly and reassemble it. "
        "Ligma balls I hate my life. I wanna finish exams and go on holiday."
        "Hello, this is a test message to check the protocol implementation. "
        "It should be split into multiple packets and sent over the socket. "
        "The server should receive it correctly and reassemble it. "
        "Ligma balls I hate my life. I wanna finish exams and go on holiday."
        "Hello, this is a test message to check the protocol implementation. "
        "It should be split into multiple packets and sent over the socket. "
        "The server should receive it correctly and reassemble it. "
        "Ligma balls I hate my life. I wanna finish exams and go on holiday."
        "Hello, this is a test message to check the protocol implementation. "
        "It should be split into multiple packets and sent over the socket. "
        "The server should receive it correctly and reassemble it. "
        "Ligma balls I hate my life. I wanna finish exams and go on holiday."
        "Hello, this is a test message to check the protocol implementation. "
        "It should be split into multiple packets and sent over the socket. "
        "The server should receive it correctly and reassemble it. "
        "Ligma balls I hate my life. I wanna finish exams and go on holiday."
    )

    # Server function (runs in a thread)
    def run_server():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen(1)
            print("[Server] Waiting for connection...")
            conn, addr = s.accept()
            with conn:
                print(f"[Server] Connected by {addr}")
                received = receive_message(conn)
                print(f"[Server] Received message:\n{received.decode('utf-8')}\n")  # decode for display

    # Client function
    def run_client():
        time.sleep(1)  # Wait for server to start
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            print("[Client] Sending message...")
            send_message(s, test_message.encode('utf-8'))  # encode to bytes
            print("[Client] Message sent.")
            

    # Run server in a background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Run client
    run_client()

    # Wait for server to finish
    server_thread.join(timeout=5)

# Run the test when script is run directly
if __name__ == "__main__":
    test_protocol()