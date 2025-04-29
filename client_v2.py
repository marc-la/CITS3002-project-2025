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

game_start_event = threading.Event()  # Event to signal when the game starts

def receive_messages(rfile):
    """Continuously receive and display messages from the server."""
    try:
        while True:
            line = rfile.readline()
            if not line:
                print("[INFO] Server disconnected.")
                break

            line = line.strip()
            if line == "GAME_START":
                print("[INFO] The game is starting!")
                game_start_event.set()  # Signal that the game has started
            elif line == "GRID":
                # Read and display the board grid
                print("\n[Board]")
                while True:
                    board_line = rfile.readline()
                    if not board_line or board_line.strip() == "":
                        break
                    print(board_line.strip())
            elif "Time's up!" in line:
                print(line)
            else:
                print(line)
    except Exception as e:
        print(f"[ERROR] Error receiving messages: {e}")

def input_loop(wfile):
    """Handles user input and sends it to the server."""
    try:
        while True:
            print(">> ", end="", flush=True)  # Prompt for input
            if not game_start_event.is_set():
                ready, _, _ = select.select([sys.stdin], [], [])  # Wait for input or timeout
            else:
                ready, _, _ = select.select([sys.stdin], [], [], 30)
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
        wfile.close()

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        rfile = s.makefile('r')
        wfile = s.makefile('w')

        # Start a background thread for receiving messages
        receiver_thread = threading.Thread(target=receive_messages, args=(rfile,), daemon=True)
        receiver_thread.start()
        threading.Event().wait(0.1)  # DO NOT REMOVE
        # Start the input loop
        input_loop(wfile)

if __name__ == "__main__":
    main()