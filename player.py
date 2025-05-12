from battleship import *
import logging
from queue import Empty
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
    def __init__(self, username, wfile, input_queue):
        self.username = username
        self.wfile = wfile                   # Output stream (file-like)
        self.board = Board(BOARD_SIZE)       # Player's board
        self.input_queue = input_queue       # Queue for incoming messages
        self.is_disconnected = Event()

    def send(self, msg):
        try:
            self.wfile.write(msg + '\n')
            self.wfile.flush()
        except Exception as e:
            self.is_disconnected.set()
            logging.error(f"Error sending message to player {self.username}: {e}")

    def get_next_input(self, timeout=TIMEOUT_SECONDS):
        try:
            return self.input_queue.get(timeout)
        except Empty:
            self.is_disconnected.set()
            return None