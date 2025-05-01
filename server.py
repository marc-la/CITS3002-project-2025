#!/usr/bin/env python3

# Imports
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from threading import Thread, Event
from battleship_multiplayer import TwoPlayerBattleshipGame
import logging
import time
import select

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Global Variables
HOST = "127.0.0.1"
PORT = 5000
MAX_CONNECTIONS = 12
player_connections = [None, None] # Store (conn, addr) tuples for players
waiting_lobby_queue = [] # Store (conn, addr) tuples for spectators
spectator_threads = {} # Spectator threads
rfiles = {} # Read file objects for all connections
wfiles = {} # Write file objects for all connections
game_over_event = Event()

def start_server():
    """
    Start the server and accept connections.
    """
    logging.info(f"Server listening on {HOST}:{PORT}")
    with socket(AF_INET, SOCK_STREAM) as s:
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(MAX_CONNECTIONS)
        logging.info("Waiting for players to connect...")

        while True:
            try:
                conn, addr = s.accept()
                logging.info(f"Accepted connection from {addr}")
                handle_new_connection(conn, addr)
                if len(waiting_lobby_queue) >= 2:  # Check if there is space for a player
                    logging.info("Both players connected. Starting the game...")
                    start_game()
            except KeyboardInterrupt:
                logging.info("Server shutting down...")
                break
            except Exception as e:
                logging.error(f"Server error: {e}")

def handle_new_connection(conn, addr):
    """
    Handle a new connection, assigning it as a player or spectator.
    """
    waiting_lobby_queue.append((conn, addr))
    rfiles[conn] = conn.makefile('r')
    wfiles[conn] = conn.makefile('w')
    wfiles[conn].write("[INFO] You are connected to the server and in the waiting lobby. Type 'quit' to leave.\n")
    wfiles[conn].flush()

    spectator_thread = Thread(target=handle_spectator, args=(conn, addr), daemon=True)
    spectator_thread.start()
    spectator_threads[conn] = spectator_thread

def handle_spectator(conn, addr):
    """
    Handle a spectator connection.
    """
    logging.info(f"Spectator connected from {addr}")
    try:
        with conn:
            rfile = conn.makefile('r')
            wfile = conn.makefile('w')
            wfile.write("[INFO] You are now spectating the game. Type 'quit' to leave.\n")
            wfile.flush()

            while True:
                # Check if the spectator has been promoted to a player
                if (conn, addr) in player_connections:
                    logging.info(f"Spectator {addr} promoted to player. Exiting spectator mode.")
                    break

                # Use select to check for input without blocking
                ready, _, _ = select.select([rfile], [], [], 1)  # Timeout of 1 second
                if ready:
                    line = rfile.readline().strip()
                    if not line or line.lower() == "quit":
                        logging.info(f"Spectator {addr} disconnected.")
                        break
    except Exception as e:
        logging.error(f"Error with spectator {addr}: {e}")
    finally:
        if (conn, addr) in waiting_lobby_queue:
            del spectator_threads[(conn, addr)]

def broadcast_to_spectators(message):
    """
    Broadcast a message to all spectators.
    """
    # Iterate over a copy
    for spectator in waiting_lobby_queue:
        conn, addr = spectator
        try:
            conn.sendall(message.encode('utf-8'))
        except Exception:
            waiting_lobby_queue.remove(spectator)

def start_game():
    """
    Start a new game.
    """
    try:
        # Extract the first two players from the waiting lobby
        global player_connections
        player_connections = [waiting_lobby_queue.pop(0), waiting_lobby_queue.pop(0)]

        # Wait for their spectator threads to terminate
        spectator_threads[player_connections[0][0]].join()  # Use conn as the key
        spectator_threads[player_connections[1][0]].join()  # Use conn as the key

        # Extract rfiles and wfiles using conn as the key
        player_rfiles = [rfiles[player_connections[0][0]], rfiles[player_connections[1][0]]]
        player_wfiles = [wfiles[player_connections[0][0]], wfiles[player_connections[1][0]]]
        logging.info(f"Starting game with players: {player_connections[0][1]} and {player_connections[1][1]}")
        # Start the game

        broadcast_to_spectators("[INFO] The game is starting (spectate view)...\n")
        game = TwoPlayerBattleshipGame(player_rfiles, player_wfiles, waiting_lobby_queue)
        game.start_game()
    except KeyError as e:
        logging.error(f"KeyError during game setup: {e}")
    except Exception as e:
        logging.error(f"Error during game: {e}")
    finally:
        game_over_event.clear()

def shutdown_server():
    """
    Clean up resources and shut down the server.
    """
    for conn, addr in waiting_lobby_queue + player_connections:
        try:
            conn.close()
        except Exception as e:
            logging.error(f"Error closing connection: {e}")
    for thread in spectator_threads.values():
        thread.join()
    logging.info("Server shutdown complete.")

if __name__ == "__main__":
    try:
        start_server()
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        shutdown_server()