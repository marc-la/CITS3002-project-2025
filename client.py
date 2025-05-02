#!/usr/bin/env python3

# Imports
from sys import stdin
from select import select
from socket import socket, AF_INET, SOCK_STREAM
from threading import Event, Thread
from config import *

# Global Variables
game_over_event = Event()
input_timer = Event()
is_spectator_event = Event()

def handle_server_message(line, rfile):
    """
    Process a single message from the server.
    """
    if line == "GAME_START":
        logging.info("The game is starting!")
        is_spectator_event.clear()
    elif line == "DISCONNECT":
        logging.info("Server requested disconnection.")
        game_over_event.set()
    elif line == "YOUR_TURN":
        input_timer.set()
    elif line == "GRID":
        logging.info("Receiving board grid:")
        while True:
            board_line = rfile.readline().strip()
            if not board_line:
                break
            print(board_line)
    else:
        print(line)

def receive_messages(rfile):
    """
    Continuously receive and display messages from the server.
    """
    try:
        while not game_over_event.is_set():
            ready, _, _ = select([rfile], [], [], 1)
            if ready:
                line = rfile.readline().strip()
                if line == "":
                    # logging.info("Server disconnected.")
                    # game_over_event.set()
                    break
                handle_server_message(line, rfile)
    except Exception as e:
        logging.error(f"Error receiving messages: {e}")
        game_over_event.set()

def input_loop(wfile):
    """
    Handles user input and sends it to the server.
    """
    try:
        while not game_over_event.is_set():
            if input_timer.is_set():
                ready, _, _ = select([stdin], [], [], INPUT_TIMEOUT)
                if ready:
                    user_input = stdin.readline().strip()
                    if user_input.lower() == 'quit':
                        logging.info("Exiting...")
                        game_over_event.set()
                        break
                    wfile.write(user_input + '\n')
                    wfile.flush()
                else:
                    logging.info("Input timeout. Exiting...")
                    game_over_event.set()
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

        # Start the input loop
        input_loop(wfile)

        # Wait for the receiver thread to finish
        receiver_thread.join()

if __name__ == "__main__":
    run_client(host=HOST, port=PORT)