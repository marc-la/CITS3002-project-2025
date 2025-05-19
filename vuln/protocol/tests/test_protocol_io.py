import socket
import threading
import pytest

from protocol import send_message, receive_message, shutdown_logging

@pytest.fixture
def socket_pair():
    """Provides a pair of connected sockets for client/server simulation."""
    s1, s2 = socket.socketpair()
    yield s1, s2
    s1.close()
    s2.close()
    shutdown_logging()

def test_send_and_receive_message(socket_pair):
    client_sock, server_sock = socket_pair
    message = b"Hello, protocol test message!"

    # Run server receive in background
    def server_thread_fn():
        received = receive_message(server_sock)
        assert received == message

    thread = threading.Thread(target=server_thread_fn)
    thread.start()

    # Client sends
    send_message(client_sock, message)

    thread.join(timeout=2)
