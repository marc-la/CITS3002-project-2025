#!/usr/bin/env python3

"""
server.py

Tier 2.2: Enables multiple games of Battleship to be played without restarting the server.
Uses the two-player game logic defined in battleship.py (run_two_play_game_online).
"""

import socket
import threading
from battleship_2p import *

HOST = '127.0.0.1'
PORT = 5000

# Global lock to ensure only one game runs at a time
game_lock = threading.Lock()

def handle_client(conn, addr, player_id, rfiles, wfiles, game_over_event):
    """Handles a single client connection."""
    print(f"[INFO] Player {player_id} from {addr} is now playing.")
    try:
        with conn:
            rfile = conn.makefile('r')
            wfile = conn.makefile('w')

            # Add the player's file-like objects to the shared lists
            rfiles[player_id] = rfile
            wfiles[player_id] = wfile

            # Notify the player to wait for the game to start
            wfile.write("Waiting for the other player to connect...\n")
            wfile.flush()

            # Wait until both players are connected
            while None in rfiles or None in wfiles:
                pass  # Busy wait until both players are ready

            # Start the game once both players are connected
            if player_id == 0:  # Only the first thread starts the game
                print("[INFO] Both players connected. Starting the game...")
                run_two_play_game_online(rfiles, wfiles)

                # Signal that the game is over
                game_over_event.set()

    except (ConnectionResetError, BrokenPipeError):
        print(f"[INFO] Player {player_id} from {addr} disconnected.")
        game_over_event.set()  # Signal that the game is over if a player disconnects
        # Clean up resources for the disconnected player
        rfiles[player_id] = None
        wfiles[player_id] = None
        print(f"[INFO] Player {player_id} from {addr} has been cleaned up.")
    except Exception as e:
        print(f"[ERROR] Exception while handling client {addr}: {e}")

def start_game(connections, rfiles, wfiles, game_over_event):
    """Starts a new game in a separate thread."""
    print("[INFO] Starting a new game with the first two players in the queue.")

    # Acquire the lock to ensure only one game runs at a time
    with game_lock:
        for player_id in range(2):
            conn, addr = connections.pop(0)
            client_thread = threading.Thread(target=handle_client, args=(conn, addr, player_id, rfiles, wfiles, game_over_event), daemon=True)
            client_thread.start()
            print_running_threads()

        game_over_event.wait()  # Block until the game is over or a client disconnects
        game_over_event.clear()  # Reset the event for the next game

        # Close any remaining connections for the game
        for conn in rfiles + wfiles:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        print("[INFO] Game has ended or a client disconnected.")
        print("[INFO] Returning to waiting for new connections...")

def print_running_threads():
    threads = threading.enumerate()
    print(f"Number of running threads: {len(threads)}")
    for thread in threads:
        print(f"[INFO] Thread Name: {thread.name}, Is Daemon: {thread.daemon}, Is Alive: {thread.is_alive()}")

def main():
    """Main server function to accept connections and handle clients using threads."""
    print(f"[INFO] Server listening on {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(12)  # Allow up to 12 connections in the waiting queue
        print("[INFO] Waiting for players to connect...")

        connections = []

        while True:
            # Shared lists to store file-like objects for both players
            rfiles = [None, None]
            wfiles = [None, None]

            # Event to signal when the game is over
            game_over_event = threading.Event()

            try:
                conn, addr = s.accept()
                print(f"[INFO] Accepted connection from {addr} into waiting lobby. Current waiting lobby size: {len(connections) + 1}")
                connections.append((conn, addr))

                conn.sendall(b"[INFO] You have joined the battleship game waiting room\n")
                # Remove disconnected clients from the waiting room
                connections = [(c, a) for c, a in connections if c.fileno() != -1]

                # Start a game if there are at least two players
                if len(connections) >= 2:
                    game_thread = threading.Thread(target=start_game, args=(connections, rfiles, wfiles, game_over_event), daemon=True)
                    game_thread.start()
                    print_running_threads()

            except KeyboardInterrupt:
                print("\n[INFO] Server shutting down...")
                break
            except Exception as e:
                print(f"[ERROR] Server error: {e}")

if __name__ == "__main__":
    main()