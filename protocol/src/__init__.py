"""
Tier 4: Advanced Features

Implement additional capabilities to address real-world networking concerns or enhancements.
Complete TWO OR MORE of the below tasks, where one of the tasks must be T4.1 Custom Low-Level Protocol with Checksum.
More tasks you complete, better marks you could receive for this tier.
Provide details in your report as indicated.

T4.1 Custom Low-Level Protocol with Checksum
- Move beyond simple send/recv usage of TCP or UDP by crafting your own packet format and verifying data integrity.
- Define a header (e.g., containing sequence number, packet type, game-specific fields, and a checksum).
- Implement a checksum mechanism (e.g. CRC-32 or a simpler sum-based approach) to detect corrupted packets on receipt.
- Decide on your error-handling policy if a packet fails the checksum (discard, request retransmission, etc.).
- In your report, you must include:
    o A clear specification of the packet structure (fields, sizes, arrangement).
    o How you generate and verify checksums.
    o What your protocol does with corrupted or out-of-sequence packets.
    o Statistical demonstration (optional but recommended): E.g., artificially inject errors or scramble bits, measure how many packets get flagged as corrupted.

NOTE: Some of you have asked about whether task 4.1 in the project means to replace TCP with the custom one.
If that is something you think you could do, then you can do so. However, it is sufficient to implement the required features on top of TCP for demonstration purposes (i.e., handling the custom packets and error detection, etc.).

---

T4.3 Encryption Layer
- Implement a basic symmetric encryption scheme for your protocol, e.g. AES in CTR mode, or a simplified approach with a shared secret key.
- Define how you exchange keys (if at all) or assume an out-of-band channel.
- Show how you incorporate encryption into your custom packet structure from T4.1 (e.g., encrypting the payload, or each packet’s data, ensuring you still can verify checksums or use an integrity-protected encryption scheme).
- Report how you handle replay attacks, partial packet corruption, or IV generation (if using a block cipher).
"""
