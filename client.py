#!/usr/bin/env python3

"""
client.py

Connects to a Battleship server which runs the single-player game.
Uses threading to fix message synchronisation issues between server and user input.
"""

import socket
import threading
HOST = '0.0.0.0'
PORT = 5001

def receive_messages(rfile):
    """Continuously receive and display messages from the server"""
    try:
        while True:
            line = rfile.readline()
            if not line:
                print("[INFO] Server disconnected.")
                break

            line = line.strip()
            if line == "GRID":
                # Read and display the board grid
                print("\n[Board]")
                while True:
                    board_line = rfile.readline()
                    if not board_line or board_line.strip() == "":
                        break
                    print(board_line.strip())
            else:
                print(line)
    except Exception as e:
        print(f"[ERROR] Error receiving messages: {e}")

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        rfile = s.makefile('r')
        wfile = s.makefile('w')

        # Start a background thread for receiving messages
        receiver_thread = threading.Thread(target=receive_messages, args=(rfile,), daemon=True)
        receiver_thread.start()

        try:
            while True:
                # Main thread handles sending user input
                user_input = input(">> ")
                if user_input.lower() == 'quit':
                    print("[INFO] Exiting...")
                    break
                wfile.write(user_input + '\n')
                wfile.flush()
        except KeyboardInterrupt:
            print("\n[INFO] Client exiting.")
        finally:
            s.close()
            
# HINT: A better approach would be something like:
#
# def receive_messages(rfile):
#     """Continuously receive and display messages from the server"""
#     while running:
#         line = rfile.readline()
#         if not line:
#             print("[INFO] Server disconnected.")
#             break
#         # Process and display the message
#
# def main():
#     # Set up connection
#     # Start a thread for receiving messages
#     # Main thread handles sending user input

if __name__ == "__main__":
    main()