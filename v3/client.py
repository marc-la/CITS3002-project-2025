#!/usr/bin/env python3

# Imports
from sys import stdin
from select import select
from socket import socket, AF_INET, SOCK_STREAM
from threading import Event, Thread
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='[CLIENT][%(levelname)s] %(message)s')

# Global variables (edit here to change)
HOST = '127.0.0.1'
PORT = 5000
INPUT_TIMEOUT = 30

class Client:
    """
    Client Class

    A class-based implementation of the Battleship client.
    Connects to a Battleship server for multiplayer gameplay.
    Uses threading to handle message synchronization between server and user input.

    Attributes:
        host (str): The server's IP address.
        port (int): The server's port number.
        game_start_event (threading.Event): Event to signal when the game starts.
        stop_input_event (threading.Event): Event to signal when input should stop.
    """

    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self.game_start_event = Event()
        self.stop_input_event = Event()

    def receive_messages(self, rfile):
        """
        Continuously receive and display messages from the server.
        """
        try:
            while not self.stop_input_event.is_set():
                line = rfile.readline()
                if not line:
                    logging.info("Server disconnected.")
                    self.stop_input_event.set()
                    break

                line = line.strip()
                if line == "GAME_START":
                    logging.info("The game is starting!")
                    self.game_start_event.set()
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
                    self.stop_input_event.set()
                else:
                    print(line)
        except Exception as e:
            logging.error(f"Error receiving messages: {e}")
            self.stop_input_event.set()
            raise

    def input_loop(self, wfile):
        """
        Handles user input and sends it to the server.
        """
        try:
            while not self.stop_input_event.is_set():
                print(">> ", end="", flush=True)
                timeout = None if not self.game_start_event.is_set() else INPUT_TIMEOUT
                ready, _, _ = select([stdin], [], [], timeout)
                if self.stop_input_event.is_set():
                    break
                if ready:
                    user_input = stdin.readline().strip()
                    if user_input.lower() == 'quit':
                        logging.info("Exiting...")
                        self.stop_input_event.set()
                        break
                    wfile.write(user_input + '\n')
                    wfile.flush()
        except KeyboardInterrupt:
            logging.info("Client exiting due to keyboard interrupt.")
            self.stop_input_event.set()
        finally:
            wfile.close()

    def run(self):
        """
        Connect to the server and start the client.
        """
        with socket(AF_INET, SOCK_STREAM) as s:
            try:
                s.connect((self.host, self.port))
                rfile = s.makefile('r')
                wfile = s.makefile('w')

                # Start a background thread for receiving messages
                receiver_thread = Thread(target=self.receive_messages, args=(rfile,), daemon=True)
                receiver_thread.start()

                # Start the input loop
                self.input_loop(wfile)

                # Wait for the receiver thread to finish
                receiver_thread.join()
            except Exception as e:
                logging.error(f"An error occurred: {e}")
                self.stop_input_event.set()


if __name__ == "__main__":
    client = Client(host=HOST, port=PORT)
    client.run()