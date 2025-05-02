#!/usr/bin/env python3

# Imports
from sys import stdin
from select import select
from socket import socket, AF_INET, SOCK_STREAM
from threading import Event, Thread
from config import *
import time

# Global Variables
game_over_event = Event()
input_timer = Event()
is_spectator_event = Event()

def receive_messages(rfile):
    """
    Continuously receive and display messages from the server.
    """
    try:
        while not game_over_event.is_set():
            ready, _, _ = select([rfile], [], [], 1)  # Timeout of 1 second
            if ready:
                line = rfile.readline().strip()
                if not line:
                    logging.info("Server disconnected.")
                    game_over_event.set()
                    break

                line = line.strip()
                if line == "GAME_START":
                    logging.info("The game is starting!")
                    is_spectator_event.clear()  # Clear the spectator event
                elif line == "DISCONNECT":
                    game_over_event.set()
                    break
                elif line == "YOUR_TURN":
                    input_timer.set()  # Set the input timer event
                elif line == "GRID":
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
        logging.error(f"Error receiving messages: {e}")
        game_over_event.set()

def input_loop(wfile):
    """
    Handles user input and sends it to the server.
    """
    try:
        while not game_over_event.is_set():
            time_counter = 0
            while input_timer.is_set():
                if time_counter >= INPUT_TIMEOUT:
                    print("\n[INFO] Input timeout. Exiting...")
                    game_over_event.set()
                    break
                ready, _, _ = select([stdin], [], [], 1)
                time_counter += 1
                if ready:
                    user_input = stdin.readline().strip()
                    if user_input.lower() == 'quit':
                        logging.info("Exiting...")
                        game_over_event.set()
                        break
                    elif user_input == "":
                        continue
                    wfile.write(user_input + '\n')
                    wfile.flush()
    except KeyboardInterrupt:
        logging.info("Client exiting due to keyboard interrupt.")
        game_over_event.set()
    finally:
        wfile.close()

def run_client(host, port):
    """
    Connect to the server and start the client.
    """
    with socket(AF_INET, SOCK_STREAM) as s:
        s.connect((host, port))
        rfile = s.makefile('r')
        wfile = s.makefile('w')

        # Start a background thread for receiving messages
        receiver_thread = Thread(target=receive_messages, args=(rfile,), daemon=True)
        receiver_thread.start()
        time.sleep(0.1)

        # Start the input loop
        input_loop(wfile)

        # Wait for the receiver thread to finish
        receiver_thread.join(timeout=1)

if __name__ == "__main__":
    run_client(host=HOST, port=PORT)