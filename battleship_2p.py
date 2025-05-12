from battleship import *
import logging
import threading
from queue import Queue, Empty
from config import *        # constants

# ----------------------------------------------------------------------------

class Player:
    """
    Class player.

    Represents a player in the Battleship game.

    Attributes:
        name (str): The name of the player.
        rfile (file-like): The input stream for the player.
        wfile (file-like): The output stream for the player.
        board (Board): The player's board.
        is_current_player (bool): Indicates if it's the player's turn.
        is_disconnected (bool): Indicates if the player has disconnected.
    """
    def __init__(self, name, files):
        self.name = name
        self.rfile = files[0]                   # Input stream (file-like)
        self.wfile = files[1]                   # Output stream (file-like)
        self.board = Board(BOARD_SIZE)       # Player's board
        self.is_disconnected = threading.Event()
        self.input_queue = Queue()                  # Queue for incoming messages
        self.listener_thread = threading.Thread(target=self.start_listener, daemon=True)
        self.listener_thread.start()                # Start the listener thread

    # Function to start the listener thread
    def start_listener(self):
        while True:
            try:
                input_line = self.receive()
                self.input_queue.put(input_line)
            except Exception as e:
                self.is_disconnected.set()
                logging.error(f"Error getting input for player {self.name}: {e}")
                break

    def send(self, msg):
        try:
            self.wfile.write(msg + '\n')
            self.wfile.flush()
        except Exception as e:
            self.is_disconnected.set()
            logging.error(f"Error sending message to player {self.name}: {e}")

    def receive(self):
        try:
            return self.rfile.readline().strip()
        except Exception as e:
            self.is_disconnected.set()
            return None

    def get_next_input(self, timeout=TIMEOUT_SECONDS):
        try:
            return self.input_queue.get(timeout)
        except Empty:
            self.is_disconnected.set()
            return None


def display_board(player, opponent):
    """
    Displays the boards of both players.

    @param player (Player): The current player.
    @param opponent (Player): The opponent player.
    """
    try:
        # Header
        player.send("[YOUR GUESSES]".ljust(32) + "[YOUR BOARD]")
        col_header = ".  " + "".join(str(i + 1).ljust(2) for i in range(BOARD_SIZE))
        player.send(col_header.ljust(32) + col_header)

        # Rows
        for r in range(BOARD_SIZE):
            row_label = chr(ord('A') + r)
            guesses_row = " ".join(opponent.board.display_grid[r])
            ships_row = " ".join(player.board.hidden_grid[r])
            aligned_row = f"{row_label:2} {guesses_row}".ljust(32) + f"{row_label:2} {ships_row}"
            player.send(aligned_row)
        
        # Footer
        player.send("")
        player.wfile.flush()
    except Exception as e:
        logging.error(f"Error displaying board to player {player}: {e}")


def send_to_both_players(players: list[Player], msg: str):
    for player in players:
        player.send(msg)

# ----------------------------------------------------------------------------

def run_two_player_battleship_game(players: list, client_files: dict):
    """
    Runs a two-player Battleship game.

    @param players (list): A list of the 2 players in the game.
    @param client_files (dict): A dict in format username:(wfile,rfile).
    """

    # 1. Initialise all players
    current_player = Player(players[0], client_files[players[0]])
    other_player = Player(players[1], client_files[players[1]])
    player_list = [current_player, other_player]

    # 2. Place ships (random or manual)
    for player in player_list:
        player.send("Welcome to Battleship! Place your ships.")
        player.send("Would you like to place ships manually (M) or randomly (R)? [M/R]:")
        choice = player.get_next_input()
        if choice is None:
            player.send("No input received. Defaulting to random placement.")
            choice = 'R'
        if choice == 'M':
            player.send("You chose manual placement.")
            player.board.place_ships_manually(SHIPS)
        else:
            player.board.place_ships_randomly(SHIPS)
        player.send("Your ships have been placed.")


    # 3. Main game loop
    send_to_both_players(player_list, "The game begins! Players will alternate turns firing at each other.")
    should_print_board_to_player = True
    while True:
        # Check for disconnections
        if current_player.is_disconnected.is_set() or other_player.is_disconnected.is_set():
            send_to_both_players(player_list, "A player has disconnected. Game over.")
            break
        
        #    - Prompt for move, receive input
        if should_print_board_to_player:
            display_board(current_player, other_player)
            current_player.send(f"Your Turn. Enter a coordinate to fire at (e.g., B5). You have {TIMEOUT_SECONDS} seconds:")
            other_player.send("Waiting for the other player to take their turn...")

        #    - Validate/process move, update boards
        guess = current_player.get_next_input()
        if not guess:
            current_player.send("No input received. You lose and you will be disconnected. Goodbye.")
            current_player.is_disconnected.set()
            continue

        try:
            row, col = parse_coordinate(guess)
            if row < 0 or row >= BOARD_SIZE or \
                col < 0 or col >= BOARD_SIZE:
                 raise ValueError
        except Exception as e:
                current_player.send(f"Invalid input. Try again.")
                should_print_board_to_player = False
                continue
        
        # Check if the coordinate has already been guessed
        result, was_sunk = other_player.board.fire_at(row, col)
        if result == "hit":
            pass
        else:

        
        #    - Check for win/loss
        if other_player.board.all_ships_sunk():
            current_player.send("You win! All opponent's ships are sunk.")
            other_player.send("You lose! All your ships are sunk.")
            send_to_both_players(player_list, "Game over.")
            break
        


    #    - Notify both players of result
    #    - Check for win/loss
    #    - Handle disconnections/timeouts
    #    - Alternate turns

# ----------------------------------------------------------------------------

def main():
    import io

    # Simulate input for both players (e.g., both choose random placement)
    player1_input = io.StringIO("R\n")
    player2_input = io.StringIO("ss\n")
    player1_output = io.StringIO()
    player2_output = io.StringIO()

    # Map usernames to (rfile, wfile)
    players = ["Alice", "Bob"]
    client_files = {
        "Alice": (player1_input, player1_output),
        "Bob": (player2_input, player2_output)
    }

    # Run the game setup (ship placement)
    run_two_player_battleship_game(players, client_files)

    # Print outputs to verify
    print("Alice's output:")
    print(player1_output.getvalue())
    print("Bob's output:")
    print(player2_output.getvalue())

if __name__ == "__main__":
    main()
