#!/usr/bin/env python3

import socket
import threading
import select
from battleship_multiplayer import TwoPlayerBattleshipGame
from config import *

# Global Variables
player_connections = [None, None]  # Store (conn, addr) tuples for players
waiting_lobby = []  # Store (conn, addr) tuples for spectators
spectator_threads = {}  # Threads for spectators
game_over_event = threading.Event()
lock = threading.Lock()


def handle_player(conn, addr, player_id):
    """
    Handle a player connection.
    """
    try:
        rfile = conn.makefile('r')
        wfile = conn.makefile('w')
        wfile.write(f"[INFO] Welcome Player {player_id + 1}. Waiting for the game to start...\n")
        wfile.flush()

        with lock:
            player_connections[player_id] = (conn, addr, rfile, wfile)

        # Wait for both players to connect
        if all(player_connections):
            logging.info("Both players connected. Starting the game...")
            start_game()

    except Exception as e:
        logging.error(f"Error with Player {player_id + 1}: {e}")
    finally:
        with lock:
            player_connections[player_id] = None
        conn.close()


def handle_spectator(conn, addr):
    """
    Handle a spectator connection.
    """
    try:
        rfile = conn.makefile('r')
        wfile = conn.makefile('w')
        wfile.write("[INFO] You are now spectating the game. Type 'quit' to leave.\n")
        wfile.flush()

        while True:
            ready, _, _ = select.select([rfile], [], [], 1)
            if ready:
                line = rfile.readline().strip()
                if not line or line.lower() == "quit":
                    logging.info(f"Spectator {addr} disconnected.")
                    break
    except Exception as e:
        logging.error(f"Error with spectator {addr}: {e}")
    finally:
        with lock:
            if conn in waiting_lobby:
                waiting_lobby.remove(conn)
        conn.close()


def start_game():
    """
    Start a new game with the connected players.
    """
    global game_over_event
    game_over_event.clear()

    # Extract player file objects
    rfiles = [player[2] for player in player_connections]
    wfiles = [player[3] for player in player_connections]

    # Run the game in a separate thread
    game_thread = threading.Thread(
        target=TwoPlayerBattleshipGame().run_game,
        args=(rfiles, wfiles, waiting_lobby, game_over_event),
        daemon=True
    )
    game_thread.start()

    # Wait for the game to end
    game_thread.join()

    # Notify players and reset connections
    for player in player_connections:
        if player:
            player[3].write("[INFO] Game over. Waiting for a new game...\n")
            player[3].flush()

    with lock:
        for i in range(2):
            player_connections[i] = None


def accept_connections(server_socket):
    """
    Accept incoming connections and assign them as players or spectators.
    """
    while True:
        conn, addr = server_socket.accept()
        logging.info(f"New connection from {addr}")

        with lock:
            # Assign as a player if slots are available
            if None in player_connections:
                player_id = player_connections.index(None)
                threading.Thread(target=handle_player, args=(conn, addr, player_id), daemon=True).start()
            else:
                # Add to the waiting lobby as a spectator
                waiting_lobby.append(conn)
                spectator_thread = threading.Thread(target=handle_spectator, args=(conn, addr), daemon=True)
                spectator_thread.start()
                spectator_threads[conn] = spectator_thread


def main():
    """
    Main server function to start the server and accept connections.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(MAX_CONNECTIONS)
        logging.info(f"Server started on {HOST}:{PORT}")

        try:
            accept_connections(server_socket)
        except KeyboardInterrupt:
            logging.info("Shutting down server...")
        finally:
            server_socket.close()


if __name__ == "__main__":
    main()