#!/usr/bin/env python3

"""
client.py

Connects to a Battleship server which runs the single-player game.
Uses threading to fix message synchronisation issues between server and user input.
"""

import sys
import select
import socket
import threading

HOST = '127.0.0.1'
PORT = 5000

# Shared event to signal the main thread
stop_input_event = threading.Event()

def receive_messages(rfile):
    """Continuously receive and display messages from the server."""
    try:
        while True:
            line = rfile.readline()
            if not line:
                print("[INFO] Server disconnected.")
                stop_input_event.set()  # Signal the main thread to stop
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
            elif "Time's up!" in line:
                print(line)
                stop_input_event.set()  # Signal the main thread to stop accepting input
            else:
                print(line)
    except Exception as e:
        print(f"[ERROR] Error receiving messages: {e}")
        stop_input_event.set()  # Signal the main thread to stop

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        rfile = s.makefile('r')
        wfile = s.makefile('w')

        # Start a background thread for receiving messages
        receiver_thread = threading.Thread(target=receive_messages, args=(rfile,), daemon=True)
        receiver_thread.start()

        try:
            while not stop_input_event.is_set():  # Check if the stop signal is set
                print(">> ", end="", flush=True)  # Prompt for input
                ready, _, _ = select.select([sys.stdin], [], [], 1)  # Wait for input or timeout
                if stop_input_event.is_set():  # Check if the stop signal is set
                    break
                if ready:  # If input is ready
                    user_input = sys.stdin.readline().strip()
                    if user_input.lower() == 'quit':
                        print("[INFO] Exiting...")
                        break
                    wfile.write(user_input + '\n')
                    wfile.flush()
        except KeyboardInterrupt:
            print("\n[INFO] Client exiting.")
        finally:
            s.close()

if __name__ == "__main__":
    main()