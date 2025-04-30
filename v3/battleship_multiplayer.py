#!/usr/bin/env python3

# Imports
from queue import Queue, Empty
from threading import Thread
from battleship import *

# Constants
TIMEOUT_SECONDS = 30

class TwoPlayerBattleshipGame:
    """
    A class to manage and execute a two-player Battleship game.

    This class handles the game logic, player interactions, and communication
    between players and spectators. It supports turn-based gameplay, board
    management, and real-time input/output handling for a multiplayer Battleship
    game.

    Attributes:
        rfiles (list): File-like objects for reading input from players.
        wfiles (list): File-like objects for writing output to players.
        spectators (list): File-like objects for broadcasting messages to spectators.
        TIMEOUT_SECONDS (int): The time limit for each player's turn in seconds.
        input_queues (list): Queues for storing player inputs.
        boards (list): The game boards for each player.
        current_player (int): The index of the player whose turn it is.
        other_player (int): The index of the opponent player.
    """

    def __init__(self, rfiles, wfiles, spectators):
        """
        Initialise the game with player input/output files and spectators.
        """
        self.rfiles = rfiles
        self.wfiles = wfiles
        self.spectators = spectators
        self.player_inputs = [Queue(), Queue()]
        self.boards = [Board(BOARD_SIZE), Board(BOARD_SIZE)]
        self.current_player = 0
        self.other_player = 0
        self.listener_threads = []

    def input_listener(self, player):
        """
        Thread function to continuously read inputs from a player.
        Handles disconnections and pushes valid inputs to the player's queue.
        """
        while True:
            try:
                input_line = self.rfiles[player].readline().strip()
                if not input_line:
                    # Handle disconnection
                    print(f"[INFO] Player {player} disconnected.")
                    break
                
                # Push input into the queue
                self.player_inputs[player].put(input_line)  
            except Exception as e:
                print(f"[ERROR] Error receiving input from player {player}: {e}")
                break

    def send(self, player, msg):
        """
        Send a message to a specific player.
        """
        try:
            self.wfiles[player].write(msg + '\n')
            self.wfiles[player].flush()
        except Exception as e:
            print(f"[ERROR] Failed to send message to player {player}: {e}")

    def broadcast_players(self, msg):
        """
        Send a message to both players.
        """
        for wfile in self.wfiles:
            try:
                wfile.write(msg + '\n')
                wfile.flush()
            except Exception as e:
                print(f"[ERROR] Failed to broadcast message to a player: {e}")

    def broadcast_spectators(self, msg):
        """
        Send a message to all spectators.
        """
        for spectator in self.spectators:
            try:
                spectator.write(msg + '\n')
                spectator.flush()
            except Exception as e:
                print(f"[ERROR] Failed to broadcast message to a spectator: {e}")

    def send_board(self, player, player_board, other_board):
        """
        Send the player's board and their guesses to them.
        """
        try:
            # Header
            self.wfiles[player].write("[YOUR GUESSES]".ljust(32) + "[YOUR BOARD]\n")
            col_header = ".  " + "".join(str(i + 1).ljust(2) for i in range(BOARD_SIZE))
            self.wfiles[player].write(col_header.ljust(32) + col_header + '\n')

            # Rows
            for r in range(BOARD_SIZE):
                row_label = chr(ord('A') + r)
                guesses_row = " ".join(other_board.display_grid[r])
                ships_row = " ".join(player_board.hidden_grid[r])
                aligned_row = f"{row_label:2} {guesses_row}".ljust(32) + f"{row_label:2} {ships_row}"
                self.wfiles[player].write(aligned_row + '\n')

            # Flush the output
            self.wfiles[player].write('\n')
            self.wfiles[player].flush()
        except Exception as e:
            print(f"[ERROR] Failed to send board to player {player}: {e}")

    def start_input_listeners(self):
        """
        Start input listener threads for both players.
        """
        for player in range(2):
            thread = Thread(target=self.input_listener, args=(player,), daemon=True)
            thread.start()
            self.listener_threads.append(thread)

    def initialise_boards(self):
        """
        Initialise boards and notify players.
        """
        for player in range(2):
            self.send(player, "Welcome to Battleship! Place your ships.")

            # TODO: Implement manual placements of ships 
            self.boards[player].place_ships_randomly(SHIPS)
            self.send(player, "Your ships have been placed.")

    def start_game(self):
        """
        Main function to start and run the game.
        """
        self.start_input_listeners()
        self.initialise_boards()
        self.broadcast_players("The game begins! Players will alternate turns firing at each other.")
        self.play_game()

    def play_game(self):
        """
        Handle the main gameplay loop.
        """
        while True:
            self.send_board(self.current_player, self.boards[self.current_player], self.boards[self.other_player])
            self.send(self.current_player, f"Your Turn. Enter a coordinate to fire at (e.g., B5). You have {TIMEOUT_SECONDS} seconds:")
            self.send(self.other_player, "Waiting for the other player to take their turn...")

            guess = self.get_player_guess()
            if guess is None:
                return

            if not self.process_guess(guess):
                continue

            if self.check_game_over():
                return

            self.switch_turns()
    
    def get_player_guess(self):
        """
        Get the current player's guess with timeout handling.
        """
        try:
            guess = self.player_inputs[self.current_player].get(timeout=TIMEOUT_SECONDS)
            if guess is None:
                self.handle_disconnection()
                return None
            return guess
        except Empty:
            print(f"[INFO] Player {self.current_player} input queue is empty.")
            self.handle_timeout()
            return None

    def process_guess(self, guess):
        """
        Validate and process the player's guess.
        """
        try:
            row, col = parse_coordinate(guess)
            if row < 0 or row >= BOARD_SIZE or col < 0 or col >= BOARD_SIZE:
                raise ValueError("Coordinates out of bounds.")
        except ValueError as e:
            self.send(self.current_player, f"Invalid input: {e}. Try again.")
            return False

        result, sunk_name = self.boards[self.other_player].fire_at(row, col)
        self.handle_fire_result(result, sunk_name)
        return result != 'already_shot'

    def handle_fire_result(self, result, sunk_name):
        """
        Handle the result of firing at a coordinate.
        """
        if result == 'hit':
            if sunk_name:
                self.send(self.current_player, f"HIT! You sank the {sunk_name}!")
                self.send(self.other_player, f"Your {sunk_name} has been sunk!")
            else:
                self.send(self.current_player, "HIT!")
                self.send(self.other_player, "The opponent hit one of your ships!")
        elif result == 'miss':
            self.send(self.current_player, "MISS!")
            self.send(self.other_player, "The opponent missed!")
        elif result == 'already_shot':
            self.send(self.current_player, "You've already fired at that location. Try again.")

    def check_game_over(self):
        """
        Check if the game is over and handle the end of the game.
        """
        if self.boards[self.other_player].all_ships_sunk():
            self.send(self.current_player, "Congratulations! You sank all the opponent's ships. You win!")
            self.send(self.other_player, "All your ships have been sunk. You lose!")
            self.broadcast_players("Game over.")
            return True
        return False

    def handle_disconnection(self):
        """
        Handle player disconnection.
        """
        self.send(self.current_player, "You disconnected or timed out. You forfeit the game.")
        self.send(self.other_player, "The opponent disconnected or timed out. You win!")
        self.broadcast_players("Game over.")

    def handle_timeout(self):
        """
        Handle player timeout.
        """
        self.send(self.current_player, "Timeout! You took too long. Your turn is skipped.")
        self.send(self.other_player, "The opponent took too long. It's now your turn.")
        self.switch_turns()

    def switch_turns(self):
        """
        Switch turns between players.
        """
        self.current_player, self.other_player = self.other_player, self.current_player


# TEST: __main__ block added to test logic of TwoPlayerBattleshipGame
if __name__ == "__main__":
    import sys
    from io import StringIO

    # Simulate player input/output using StringIO
    player1_input = StringIO("A1\nB2\nC3\n")  # Example inputs for Player 1
    player2_input = StringIO("D4\nE5\nF6\n")  # Example inputs for Player 2
    player1_output = StringIO()
    player2_output = StringIO()

    # Spectator output (optional)
    spectator_output = StringIO()

    # Create file-like objects for players and spectators
    rfiles = [player1_input, player2_input]
    wfiles = [player1_output, player2_output]
    spectators = [spectator_output]

    # Initialize the game
    game = TwoPlayerBattleshipGame(rfiles, wfiles, spectators)

    # Start the game
    try:
        game.start_game()
    except KeyboardInterrupt:
        print("Game interrupted.")

    # Print outputs for debugging
    print("Player 1 Output:")
    print(player1_output.getvalue())
    print("Player 2 Output:")
    print(player2_output.getvalue())
    print("Spectator Output:")
    print(spectator_output.getvalue())
