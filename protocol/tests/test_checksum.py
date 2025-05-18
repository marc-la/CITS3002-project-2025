from protocol import compute_checksum, verify_checksum

def test_valid_checksum(sample_payload):
    checksum = compute_checksum(sample_payload)
    assert verify_checksum(sample_payload, checksum) is True

def test_invalid_checksum(sample_payload, bad_payload):
    checksum = compute_checksum(sample_payload)
    # Tampered payload with original checksum should fail
    assert verify_checksum(bad_payload, checksum) is False
