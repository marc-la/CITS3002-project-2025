from battleship import *
import logging
import time
from config import *        # constants
from player import Player

# ----------------------------------------------------------------------------

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

    except Exception as e:
        logging.error(f"Error displaying board to player {player}: {e}")


def send_to_both_players(players: list[Player], msg: str):
    for player in players:
        player.send(msg)

def broadcast_spectators(message, players, player0, player1, outcome=None, guess=None):
    for username, player in players.items():
        if player.is_spectator.is_set() and not player.is_disconnected.is_set():
            try:
                if message == "GRID":
                    # Header
                    player.send(f"[{player0.username}]".ljust(32) + f"[{player1.username}]")
                    col_header = ".  " + "".join(str(i + 1).ljust(2) for i in range(BOARD_SIZE))
                    player.send(col_header.ljust(32) + col_header)

                    # Rows
                    for r in range(BOARD_SIZE):
                        row_label = chr(ord('A') + r)
                        guesses_row = " ".join(player0.board.hidden_grid[r])
                        ships_row = " ".join(player1.board.hidden_grid[r])
                        aligned_row = f"{row_label:2} {guesses_row}".ljust(32) + f"{row_label:2} {ships_row}"
                        player.send(aligned_row)
                    
                    # Footer
                    if outcome and guess:
                        player.send(f"[INFO] {player0.username} fired at {guess} and {outcome}.")
                else:
                    player.send(f"[INFO] {message}")
            except Exception as e:
                logging.error(f"Error broadcasting message to {username}: {e}")

def check_disconnected(current_player, other_player):
    """possible thread implementation of checking for disconnections"""
    pass
# ----------------------------------------------------------------------------

def run_two_player_battleship_game(players, player0, player1):
    """
    Runs a two-player Battleship game.

    @param players (dict): A dict of players in the game, where the key is the username and the value is a Player object.
    @param player0 (str): The username of the first player.
    @param player1 (str): The username of the second player.
    """

    # 1. Initialise all players
    current_player, other_player = players[player0], players[player1]
    player_list = [current_player, other_player]
    strikes = {player0: 0, player1: 0}

    # 2. Place ships (random or manual)
    current_player.send(f"Welcome to Battleship! You will be playing against {other_player.username}")
    other_player.send(f"Welcome to Battleship! You will be playing against {current_player.username}")
    other_player.send("Waiting for the other player to place ships...")

    broadcast_spectators("Players are placing ships...", players, players[player0], players[player1])
    for i, player in enumerate(player_list):
        if i == 0:
            player_list[0].is_current_player.set()
            player_list[1].is_current_player.clear()
        else:
            player_list[0].is_current_player.clear()
            player_list[1].is_current_player.set()

        player.send("Would you like to place ships manually (M) or randomly (R)? [M/R]:")
        choice = player.get_next_input()
        if not choice or choice.strip().upper() not in ("M", "R"):
            player.send("No valid input received. Defaulting to random placement.")
            choice = 'R'
        else:
            choice = choice.strip().upper()

        if choice == 'M':
            player.send("You chose manual placement.")
            player.board.place_ships_manually(SHIPS)
        else:
            player.send("You chose random placement.")
            player.board.place_ships_randomly(SHIPS)
        player.send("Your ships have been placed.")

    current_player.is_current_player.set()
    other_player.is_current_player.clear()

    # 3. Main game loop
    send_to_both_players(player_list, "The game begins! Players will alternate turns firing at each other.")
    broadcast_spectators("The game begins! Players will alternate turns firing at each other.", players, players[player0], players[player1])
    display_board(other_player, current_player)
    broadcast_spectators("GRID", players, players[player0], players[player1])
    should_print_board_to_player = True
    while True:
        #    - Handle disconnections/timeouts
        for player, opponent in [(current_player, other_player), (other_player, current_player)]:
            if player.is_disconnected.is_set():
                opponent.send("[INFO] Your opponent has disconnected. They will forfeit if they do not reconnect within 30 seconds.")
                for _ in range(RECONNECT_TIMEOUT):
                    time.sleep(1)
                    if not player.is_disconnected.is_set():
                        opponent.send("[INFO] Your opponent has reconnected. The game will resume.")
                        break
                if player.is_disconnected.is_set():
                    opponent.send("Your opponent has failed to reconnect. You win by default.")
                    return
                    
        if current_player.is_disconnected.is_set() and other_player.is_disconnected.is_set():
            broadcast_spectators("Both players have disconnected. The game will end.", players, players[player0], players[player1])
            return
        
        #    - Prompt for move, receive input
        if should_print_board_to_player:
            display_board(current_player, other_player)
            current_player.send(f"Your Turn. Enter a coordinate to fire at (e.g., B5). You have {TIMEOUT_SECONDS} seconds:")
            other_player.send("Waiting for your opponent to take their turn...")

        #    - Validate/process move, update boards
        guess = current_player.get_next_input()
        if not guess:
            strikes[current_player.username] += 1
            if strikes[current_player.username] >= 3:
                current_player.send("You have timed out too many times. You lose by default.")
                other_player.send("Your opponent has timed out too many times. You win by default.")
                current_player.is_disconnected.set()
                return
            current_player.send(f"Timeout! Your turn is skipped. You have {3 - strikes[current_player.username]} timeouts left.")
            current_player, other_player = other_player, current_player
            should_print_board_to_player = True
            current_player.is_current_player.set()
            other_player.is_current_player.clear()
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
        
        #    - Notify both players of result
        result, ship_was_sunk = other_player.board.fire_at(row, col)
        if result == "hit":
            if ship_was_sunk:
                current_player.send(f"Hit! You sunk a ship at {ship_was_sunk}.")
                other_player.send(f"Your ship was sunk at {ship_was_sunk}.")
            else:
                current_player.send(f"Hit! You hit a ship at {guess}.")
                other_player.send(f"Your ship was hit at {guess}.")
        elif result == "miss":
            current_player.send(f"Miss! You missed at {guess}.")
            other_player.send(f"The opponent missed!")
        elif result == "already_shot":
            current_player.send(f"You already shot at {guess}. Try again.")
            should_print_board_to_player = False
            continue

        #    - Check for win/loss
        if other_player.board.all_ships_sunk():
            current_player.send("You win! All opponent's ships are sunk.")
            other_player.send("You lose! All your ships are sunk.")
            send_to_both_players(player_list, "Game over.")
            break
        
        #    - Alternate turns
        broadcast_spectators("GRID", players, players[player0], players[player1], result, guess)
        current_player, other_player = other_player, current_player
        should_print_board_to_player = True
        current_player.is_current_player.set()
        other_player.is_current_player.clear()

# ----------------------------------------------------------------------------

def main():
    import io

    # Simulate input for both players:
    player1_moves = "R\nB2\nC3\nD4\n"
    player2_moves = "R\nA1\nB1\nC1\n"

    player1_input = io.StringIO(player1_moves)
    player2_input = io.StringIO(player2_moves)
    player1_output = io.StringIO()
    player2_output = io.StringIO()

    client_files = {
        "Alice": (player1_input, player1_output),
        "Bob": (player2_input, player2_output)
    }

    # Create Player objects
    player1 = Player("Alice", client_files["Alice"])
    player2 = Player("Bob", client_files["Bob"])

    run_two_player_battleship_game(player1, player2, client_files)

    print("Alice's output:")
    print(player1_output.getvalue())
    print("Bob's output:")
    print(player2_output.getvalue())

if __name__ == "__main__":
    main()