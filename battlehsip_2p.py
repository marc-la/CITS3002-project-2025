from battleship import *

def run_two_play_game_online(rfiles, wfiles):
    """
    Runs a two-player Battleship game.
    Expects:
      - rfiles: list of file-like objects to .readline() from players
      - wfiles: list of file-like objects to .write() back to players
    """
    def send(player, msg):
        """Send a message to a specific player."""
        wfiles[player].write(msg + '\n')
        wfiles[player].flush()


    def send_board(player, player_board, other_board):
        """
        Send the player's board to them, showing:
        - Left: opponent's board view (guesses)
        - Right: their own board with ships

        [YOUR GUESSES]                  [YOUR BOARD]
            1 2 3 4 5 6 7 8 9 10            1 2 3 4 5 6 7 8 9 10
        A  . . . . . . . . . .          A  . . . . . . . . . .
        B  . . . . . . . . . .          B  . . . . . . . . . .
        C  . . . . . . . . . .          C  . . . S S S S S S .
        D  . . . . . . . . . .          D  . . . S . . . . . S
        E  . . . . . . . . . .          E  S S S . . . . . . S
        F  . . . . . . . . . .          F  . . . . . . . . . S
        G  . . . . . . . . . .          G  . . . . S S S . . S
        H  . . . . . . . . . .          H  . . . . . . . . . .
        I  . . . . . . . . . .          I  . . . . . . . . . .
        J  . . . . . . . . . .          J  . . . . . . . . . .
    """
        wfiles[player].write("[YOUR GUESSES]".ljust(32) + "[YOUR BOARD]\n")

        # Column headers for both grids
        col_header = ".  " + "".join(str(i + 1).ljust(2) for i in range(player_board.size))
        wfiles[player].write(col_header.ljust(32) + col_header + '\n')

        # Each row: label + guesses on left, ships on right
        for r in range(player_board.size):
            row_label = chr(ord('A') + r)
            guesses_row = " ".join(other_board.display_grid[r])
            ships_row = " ".join(player_board.hidden_grid[r])
            aligned_row = f"{row_label:2} {guesses_row}".ljust(32) + f"{row_label:2} {ships_row}"
            wfiles[player].write(aligned_row + '\n')

        wfiles[player].write('\n')
        wfiles[player].flush()

    def broadcast(msg):
        """Send a message to both players."""
        for wfile in wfiles:
            wfile.write(msg + '\n')
            wfile.flush()

    def recv(player):
        """Receive input from a specific player."""
        return rfiles[player].readline().strip()

    # Initialize board
    boards = [Board(BOARD_SIZE), Board(BOARD_SIZE)]

    # T1.3 Place ship randomly FOR NOW, change to manual later
    for player in range(2):
        send(player, "Welcome to Battleship! Place your ships.")
        boards[player].place_ships_randomly(SHIPS) 
        send(player, "Your ships have been placed.")

    # Start gameplay
    current_player = 0
    other_player = 1
    broadcast("The game begins! Players will alternate turns firing at each other.")

    print_board = True
    while True:
        if print_board:
            send_board(current_player, boards[current_player], boards[other_player])
            send(current_player, "Your Turn. Enter a coordinate to fire at (e.g., B5):")
            send(other_player, "Waiting for the other player to take their turn...")

        # Get the current player's move
        try:
            guess = recv(current_player)
            # FORFEIT LOGIC
            # if guess.lower() == 'quit':
            #     broadcast(f"Player {current_player + 1} has forfeited. Game over.")
            #     return
            try:
                row, col = parse_coordinate(guess)
                print_board = True
            except ValueError as e:
                send(current_player, f"Invalid input: {e}. Try again.")
                print_board = False
                continue  # Retry the turn

            result, sunk_name = boards[other_player].fire_at(row, col)

            # Process the result of the shot
            if result == 'hit':
                if sunk_name:
                    send(current_player, f"HIT! You sank the {sunk_name}!")
                    send(other_player, f"Your {sunk_name} has been sunk!")
                else:
                    send(current_player, "HIT!")
                    send(other_player, "The opponent hit one of your ships!")
                print_board = True
            elif result == 'miss':
                send(current_player, "MISS!")
                send(other_player, "The opponent missed!")
                print_board = True
            elif result == 'already_shot':
                send(current_player, "You've already fired at that location. Try again.")
                print_board = False
                continue  

            # Check if game is over
            if boards[other_player].all_ships_sunk():
                send(current_player, "Congratulations! You sank all the opponent's ships. You win!")
                send(other_player, "All your ships have been sunk. You lose!")
                broadcast("Game over.")
                return

        except ValueError as e:
            send(current_player, f"Invalid input: {e}. Try again.")
            continue 

        current_player, other_player = other_player, current_player

