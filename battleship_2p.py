from battleship import *
import logging
import threading
from queue import Queue, Empty

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
        self.is_current_player = False
        self.is_disconnected = False
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
                self.is_disconnected = True
                logging.error(f"Error getting input for player {self.name}: {e}")
                break

    def send(self, msg):
        try:
            self.wfile.write(msg + '\n')
            self.wfile.flush()
        except Exception as e:
            self.is_disconnected = True
            logging.error(f"Error sending message to player {self.name}: {e}")

    def receive(self):
        try:
            return self.rfile.readline().strip()
        except Exception as e:
            self.is_disconnected = True
            return None       

    def get_next_input(self, timeout=None):
        try:
            return self.input_queue.get(timeout=timeout)
        except Empty:
            self.is_disconnected = True
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
    current_player.is_current_player = True

    player_list = [current_player, other_player]

    # 2. Place ships (random or manual)
    for player in player_list:
        player.send("Welcome to Battleship! Place your ships.")
        player.send("Would you like to place ships manually (M) or randomly (R)? [M/R]:")
        choice = player.get_next_input(timeout=60)
        if choice is None:
            player.send("No input received. Defaulting to random placement.")
            choice = 'R'
        if choice == 'M':
            player.send("You chose manual placement.")
            player.board.place_ships_manually(SHIPS)
        else:
            player.send("You chose random placement.")
            player.board.place_ships_randomly(SHIPS)


    # 3. Main game loop
    #    - Alternate turns
    #    - Prompt for move, receive input
    #    - Validate/process move, update boards
    #    - Notify both players of result
    #    - Check for win/loss
    #    - Handle disconnections/timeouts
    display_board(current_player, other_player) 
    display_board(other_player, current_player) 
    return



# ----------------------------------------------------------------------------

def main():
    import io

    # Simulate input for both players (e.g., both choose random placement)
    player1_input = io.StringIO("R\n")
    player2_input = io.StringIO("M\n")
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
