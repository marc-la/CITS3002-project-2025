#!/usr/bin/env python3

"""
server_v2.py

Tier 2.2: Enables multiple games of Battleship to be played without restarting the server.
Uses the two-player game logic defined in battleship_2p.py (run_two_play_game_online).
"""

import socket
import threading
from battleship_2p import *

HOST = '127.0.0.1'
PORT = 5000

# Global variables
connections = []  # List of all connections (players and spectators)
spectators = []   # List of spectator connections
spectator_threads = {} 
game_lock = threading.Lock()  # Lock to ensure only one game runs at a time


def handle_spectator(conn, addr):
    """Handles a spectator connection."""
    print(f"[INFO] Spectator connected from {addr}")
    try:
        with conn:
            rfile = conn.makefile('r')
            wfile = conn.makefile('w')

            # Notify the spectator
            wfile.write("[INFO] You have joined the waiting lobby. Type 'quit' to leave.\n")
            wfile.flush()

            while True:
                line = rfile.readline().strip()
                if not line or line.lower() == "quit":
                    print(f"[INFO] Spectator {addr} disconnected.")
                    if conn in spectators:
                        spectators.remove(conn)
                    if conn in connections:
                        connections.remove(conn)
                    break
    except Exception as e:
        print(f"[ERROR] Error with spectator {addr}: {e}")
    finally:
        # Clean up the rfile and wfile for the spectator
        try:
            if 'rfile' in locals():
                rfile.close()
            if 'wfile' in locals():
                wfile.close()
        except Exception as cleanup_error:
            print(f"[ERROR] Error during cleanup for spectator {addr}: {cleanup_error}")

def promote_spectators_to_players(rfiles, wfiles):
    """Promotes the first two spectators to players."""
    print("[INFO] Promoting spectators to players...")
    for player_id in range(2):
        if spectators:
            conn = spectators.pop(0)  # Get the first spectator
            spectator_threads[conn].join()  # Wait for their spectator thread to terminate
            del spectator_threads[conn]  # Remove from the thread map

            try:
                rfile = conn.makefile('r')
                wfile = conn.makefile('w')

                # Notify the spectator and wait for confirmation
                wfile.write("[INFO] You are being promoted to a player. Type 'ready' to confirm.\n")
                wfile.flush()

                confirmation = rfile.readline().strip()
                if confirmation.lower() == "ready":
                    print(f"[INFO] Spectator confirmed promotion to player: {conn.getpeername()}")
                    # Update rfiles and wfiles for the new player
                    rfiles[player_id] = rfile
                    wfiles[player_id] = wfile
                    wfile.write("[INFO] You are now a player in the game. Get ready to play!\n")
                    wfile.flush()
                else:
                    print(f"[WARNING] Spectator did not confirm promotion: {conn.getpeername()}")
                    spectators.append(conn)  # Add back to spectators if not confirmed
            except Exception as e:
                print(f"[ERROR] Error promoting spectator to player: {e}")
                spectators.append(conn)  # Add back to spectators if an error occurs
        else:
            print("[WARNING] Not enough spectators to start a new game.")
            return False  # Not enough spectators to start a new game
    return True

def broadcast_to_spectators(message):
    """Broadcasts a message to all spectators."""
    for spectator in spectators:
        try:
            spectator.sendall(message.encode('utf-8'))
        except Exception:
            # Remove disconnected spectators
            spectators.remove(spectator)


def main():
    """Main server function to accept connections and handle clients."""
    global connections  # Declare connections as global to modify the global list
    print(f"[INFO] Server listening on {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(12)  # Allow up to 12 connections in the waiting queue
        print("[INFO] Waiting for players to connect...")

        rfiles = [None, None]
        wfiles = [None, None]
        game_over_event = threading.Event()

        while True:
            try:
                # Accept a new connection
                conn, addr = s.accept()
                print(f"[INFO] Accepted connection from {addr}")
                connections.append(conn)

                # Add the new connection as a spectator
                spectators.append(conn)
                spectator_thread = threading.Thread(target=handle_spectator, args=(conn, addr), daemon=True)
                spectator_thread.start()
                spectator_threads[conn] = spectator_thread

                # Check if we can start a new game
                if len(spectators) >= 2 and not game_over_event.is_set():
                    print("[INFO] Promoting spectators to players...")
                    promote_spectators_to_players(rfiles, wfiles)

                    # Start the game
                    print("[INFO] Starting the game...")
                    broadcast_to_spectators("[INFO] The game is starting (spectate view)...\n")
                    try:
                        run_two_play_game_online(rfiles, wfiles, spectators)
                    except (BrokenPipeError, ConnectionResetError):
                        print("[INFO] A player disconnected during the game.")
                        # Notify the remaining player
                        for i, wfile in enumerate(wfiles):
                            if wfile:
                                wfile.write("[INFO] The other player has disconnected. Returning to the lobby.\n")
                                wfile.flush()
                                wfile.close()
                        # Reset the game state
                        rfiles = [None, None]
                        wfiles = [None, None]
                        game_over_event.clear()
                        continue  # Return to the main loop

                    # Reset the game state for the next game
                    rfiles = [None, None]
                    wfiles = [None, None]
                    game_over_event.clear()

            except KeyboardInterrupt:
                print("\n[INFO] Server shutting down...")
                break
            except Exception as e:
                print(f"[ERROR] Server error: {e}")

            # Clean up disconnected connections
            connections = [conn for conn in connections if conn.fileno() != -1]


if __name__ == "__main__":
    main()