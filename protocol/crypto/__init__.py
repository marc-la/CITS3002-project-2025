"""
T4.3 Encryption Layer
- Implement a basic symmetric encryption scheme for your protocol, e.g. AES in CTR mode, or a simplified approach with a shared secret key.
- Define how you exchange keys (if at all) or assume an out-of-band channel.
- Show how you incorporate encryption into your custom packet structure from T4.1 (e.g., encrypting the payload, or each packet’s data, ensuring you still can verify checksums or use an integrity-protected encryption scheme).
- Report how you handle replay attacks, partial packet corruption, or IV generation (if using a block cipher).

---

FOR REPORT:
- State symmetric AES-CTR is used.
- Shared key is pre-agreed (out-of-band).
- Payloads are encrypted + IV is sent prepended.
- IV is random and 16 bytes (128-bit).
- Replay attacks mitigated via unique IV per packet (e.g. derived from sequence).
- Corruption handled via checksum + retransmission.
"""