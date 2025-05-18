# pytest fixtures (e.g. sample byte buffers)

import pytest

@pytest.fixture
def sample_payload():
    return b"""Hello, this is a test message to check the protocol implementation.
                It should be split into multiple packets and sent over the socket.
                The server should receive it correctly and reassemble it.
                Ligma balls I hate my life. I wanna finish exams and go on holiday."""