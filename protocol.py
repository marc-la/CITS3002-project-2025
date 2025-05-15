import struct
import socket

MAX_PAYLOAD = 32
PACKET_FORMAT = "!H B H"  # SEQ (2 bytes), TYPE (1 byte), CHECKSUM (2 bytes)
PACKET_TYPE_DATA = 0x01
PACKET_TYPE_ACK = 0x02
PACKET_TYPE_NACK = 0x03
PACKET_TYPE_END = 0x04

def checksum(data: bytes) -> int:
    return sum(data) % 65536

def build_packet(seq: int, pkt_type: int, payload: bytes) -> bytes:
    header = struct.pack('!H B', seq, pkt_type)
    cs = checksum(header + payload)
    full_packet = struct.pack(PACKET_FORMAT, seq, pkt_type, cs) + payload
    return full_packet

def send(message: str, conn: socket.socket):
    message_bytes = message.encode('utf-8')
    packets = []
    seq = 0
    
    # Split message into multiple packets
    for i in range(0, len(message_bytes), MAX_PAYLOAD):
        chunk = message_bytes[i:i+MAX_PAYLOAD]
        packet = build_packet(seq, PACKET_TYPE_DATA, chunk)
        packets.append(packet)
        seq += 1

    # Add END packet to mark end of message
    end_packet = build_packet(seq, PACKET_TYPE_END, b'')
    packets.append(end_packet)

    # Send all packets, wait for acks, retransmit if needed
    acks = set()
    while len(acks) < len(packets):
        for i, pkt in enumerate(packets):
            if i not in acks:
                conn.send(pkt)
                print(f"[send] Sent packet {i}")

        try:
            conn.settimeout(1.0)
            ack_data = conn.recv(1024)
            ack_seq, ack_type, _, = struct.unpack('!H B H', ack_data[:5])

            if ack_type == PACKET_TYPE_ACK:
                acks.add(ack_seq)
                print(f"[send] Received ACK for packet {ack_seq}")
            elif ack_type == PACKET_TYPE_NACK:
                print(f"Retransmit requested for packet {ack_seq}")
        except socket.timeout:
            print("Timeout, resending unacknowledged packets...")
            
    # Send final acknowledgment to indicate all packets were received
    final_ack = build_packet(seq + 1, PACKET_TYPE_ACK, b'')
    conn.send(final_ack)
    print("[send] Sent final acknowledgment to server.")

def receive(conn: socket.socket) -> str:
    received_packets = {}
    expected_seq = 0

    while True:
        try:
            packet = conn.recv(1024)
            seq, pkt_type, cs = struct.unpack(PACKET_FORMAT, packet[:5])
            payload = packet[5:]

            # Verify checksum
            header = struct.pack('!H B', seq, pkt_type)
            if checksum(header + payload) != cs:
                print(f"Checksum failed for packet {seq}")
                nack = build_packet(seq, PACKET_TYPE_NACK, b'')
                conn.send(nack)
                print(f"[receive] Sent NACK for packet {seq}")
                continue

            if pkt_type == PACKET_TYPE_DATA:
                received_packets[seq] = payload
                ack = build_packet(seq, PACKET_TYPE_ACK, b'')
                conn.send(ack)
                print(f"[receive] Sent ACK for packet {seq}")

            elif pkt_type == PACKET_TYPE_END:
                conn.send(build_packet(seq, PACKET_TYPE_ACK, b''))
                conn.send(ack)
                print(f"[receive] Sent ACK for END packet {seq}")

            elif pkt_type == PACKET_TYPE_ACK:
                print("[receive] Final acknowledgment received. Closing connection.")
                break
        except socket.timeout:
            continue

    # Reorder packets by sequence number
    ordered = [received_packets[i] for i in sorted(received_packets.keys())]
    full_data = b''.join(ordered)
    return full_data.decode('utf-8')

import threading
import time

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
                received = receive(conn)
                print(f"[Server] Received message:\n{received}\n")

    # Client function
    def run_client():
        time.sleep(1)  # Wait for server to start
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            print("[Client] Sending message...")
            send(test_message, s)
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