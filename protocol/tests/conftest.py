import pytest

@pytest.fixture
def sample_payload():
    return b"sample data for checksum"

@pytest.fixture
def bad_payload():
    return b"tampered data"