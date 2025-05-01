from battleship import Board, parse_coordinate, BOARD_SIZE, SHIPS
import select, sys, queue, threading

def run_two_play_game_online(rfiles, wfiles, spectators, game_over_event):
    """
    Runs a two-player Battleship game.
    Expects:
      - rfiles: list of file-like objects to .readline() from players
      - wfiles: list of file-like objects to .write() back to players
    """
    TIMEOUT_SECONDS = 30  # Set timeout period

    # Shared queues for player inputs
    input_queues = [queue.Queue(), queue.Queue()]

    def input_listener(player, input_queue):
        """Thread function to continuously read inputs from a player."""
        while True: 
            ready, _, _ = select.select([rfiles[player]], [], [], 30)
            if ready:  # If input is ready
                input_line = rfiles[player].readline().strip()
            if not input_line:
                # Handle disconnection
                print(f"[INFO] Player {player} disconnected.")
                game_over_event.set()  # Signal that the game is over
                input_queue.put(None)  # Signal disconnection
                break
            input_queue.put(input_line)  # Push input into the queue

    def send(player, msg):
        """Send a message to a specific player."""
        wfiles[player].write(msg + '\n')
        wfiles[player].flush()

    def send_board(player, player_board, other_board):
        """Send the player's board to them."""
        wfiles[player].write("[YOUR GUESSES]".ljust(32) + "[YOUR BOARD]\n")
        col_header = ".  " + "".join(str(i + 1).ljust(2) for i in range(player_board.size))
        wfiles[player].write(col_header.ljust(32) + col_header + '\n')
        for r in range(player_board.size):
            row_label = chr(ord('A') + r)
            guesses_row = " ".join(other_board.display_grid[r])
            ships_row = " ".join(player_board.hidden_grid[r])
            aligned_row = f"{row_label:2} {guesses_row}".ljust(32) + f"{row_label:2} {ships_row}"
            wfiles[player].write(aligned_row + '\n')
        wfiles[player].write('\n')
        wfiles[player].flush()

    def broadcast_players(msg):
        """Send a message to both players."""
        for wfile in wfiles:
            wfile.write(msg + '\n')
            wfile.flush()

    # Start input listener threads for both players
    listener_threads = []
    for player in range(2):
        thread = threading.Thread(target=input_listener, args=(player, input_queues[player]), daemon=True)
        thread.start()
        listener_threads.append(thread)

    # Initialize boards
    boards = [Board(BOARD_SIZE), Board(BOARD_SIZE)]
    for player in range(2):
        send(player, "Welcome to Battleship! Place your ships.")
        boards[player].place_ships_randomly(SHIPS)
        send(player, "Your ships have been placed.")

    # Start gameplay
    current_player = 0
    other_player = 1
    broadcast_players("The game begins! Players will alternate turns firing at each other.")
    send_board(other_player, boards[other_player], boards[current_player])

    while True:
        if game_over_event.is_set():
            break
        send_board(current_player, boards[current_player], boards[other_player])
        send(current_player, f"Your Turn. Enter a coordinate to fire at (e.g., B5). You have {TIMEOUT_SECONDS} seconds:")
        send(other_player, "Waiting for the other player to take their turn...")

        # Get the current player's move
        try:
            guess = input_queues[current_player].get(timeout=TIMEOUT_SECONDS)
            if guess is None:
                send(current_player, "You disconnected or timed out. You forfeit the game.")
                return
        except queue.Empty:
            send(current_player, "Timeout! You took too long. Your turn is skipped.")
            send(other_player, "The opponent took too long. It's now your turn.")
            current_player, other_player = other_player, current_player
            continue

        # Validate and process the guess
        try:
            row, col = parse_coordinate(guess)
            if row < 0 or row >= BOARD_SIZE or col < 0 or col >= BOARD_SIZE:
                raise ValueError("Coordinates out of bounds.")
        except ValueError as e:
            send(current_player, f"Invalid input: {e}. Try again.")
            continue

        result, sunk_name = boards[other_player].fire_at(row, col)
        if result == 'hit':
            if sunk_name:
                send(current_player, f"HIT! You sank the {sunk_name}!")
                send(other_player, f"Your {sunk_name} has been sunk!")
            else:
                send(current_player, "HIT!")
                send(other_player, "The opponent hit one of your ships!")
        elif result == 'miss':
            send(current_player, "MISS!")
            send(other_player, "The opponent missed!")
        elif result == 'already_shot':
            send(current_player, "You've already fired at that location. Try again.")
            continue

        # Check if the game is over
        if boards[other_player].all_ships_sunk():
            send(current_player, "Congratulations! You sank all the opponent's ships. You win!")
            send(other_player, "All your ships have been sunk. You lose!")
            broadcast_players("Game over.")
            return

        # Switch turns
        current_player, other_player = other_player, current_player