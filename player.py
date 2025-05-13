from battleship import *
import logging
from queue import Empty, Queue
from threading import Event
from config import * 

class Player:
    """
    Class player.

    Represents a player in the Battleship game.

    Attributes:
        username (str): The username of the player.
        rfile (file-like): The input stream for the player.
        wfile (file-like): The output stream for the player.
        board (Board): The player's board.
        is_current_player (bool): Indicates if it's the player's turn.
        is_disconnected (bool): Indicates if the player has disconnected.
    """
    def __init__(self, username, wfile):
        self.username = username
        self.wfile = wfile                   # Output stream (file-like)
        self.board = Board(BOARD_SIZE)       # Player's board
        self.input_queue = Queue()       # Queue for incoming messages
        self.is_disconnected = Event()
        self.is_current_player = Event()
        self.is_spectator = Event()

    def send(self, msg):
        try:
            # print(msg, "HERE")
            self.wfile.write(msg + '\n')
            self.wfile.flush()
        except Exception as e:
            self.is_disconnected.set()
            logging.error(f"Error sending message to player {self.username}: {e}")

    def get_next_input(self):
        try:
            x = self.input_queue.get(timeout=TIMEOUT_SECONDS)
            print(f"[INFO] Received input from {self.username}: {x}")
            return x
        except Empty:
            print(f"[INFO] {self.username} timed out waiting for input.")
            self.is_disconnected.set()
            return None