from battleship import *
import logging
from queue import Empty, Queue
from threading import Event
from config import *
from protocol import send_message

logger = logging.getLogger("player")
logger.setLevel(logging.INFO)
logger.propagate = False

class Player:
    """
    Class player.

    Represents a player in the Battleship game.

    Attributes:
        username (str): The username of the player.
        conn (socket.socket): The socket connection for the player.
        input_queue (Queue): Queue for ouput stream for the player.
        board (Board): The player's board.
        is_current_player (Event): Indicates if it's the player's turn.
        is_disconnected (Event): Indicates if the player has disconnected.
        is_spectator (Event): Indicates if the player is a spectator.
    """
    def __init__(self, username, conn):
        self.username = username              # The username of the player
        self.conn = conn                      # The socket connection for the player
        self.board = Board(BOARD_SIZE)        # The player's game board
        self.input_queue = Queue()            # Queue for incoming input from the player
        self.is_disconnected = Event()        # Event flag for player disconnection
        self.is_current_player = Event()      # Event flag for tracking player's turn
        self.is_spectator = Event()           # Event flag for spectator status

    def send(self, msg):
        try:
            if self.is_disconnected.is_set():
                return
            send_message(self.conn, msg.encode('utf-8'), key=KEY, use_timestamp=False)
        except Exception as e:
            self.is_disconnected.set()
            logger.error(f"Error sending message to player {self.username}: {e}")

    def get_next_input(self):
        try:
            input = self.input_queue.get(timeout=TIMEOUT_SECONDS)
            logger.info(f"Received input from {self.username}: {input}")
            return input
        except Empty:
            logger.info(f"{self.username} timed out waiting for input.")
            return None