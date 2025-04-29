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
            wfile.write("[INFO] You are now spectating the game. Type 'quit' to leave.\n")
            wfile.flush()

            while True:
                line = rfile.readline().strip()
                if not line or line.lower() == "quit":
                    print(f"[INFO] Spectator {addr} disconnected.")
                    break
    except Exception as e:
        print(f"[ERROR] Error with spectator {addr}: {e}")
    finally:
        # Remove the spectator from the list and terminate their thread
        spectators.remove(conn)
        del spectator_threads[conn]
        conn.close()


def promote_spectators_to_players(rfiles, wfiles):
    """Promotes the first two spectators to players."""
    print("[INFO] Promoting spectators to players...")
    for player_id in range(2):
        if spectators:
            conn = spectators.pop(0)  # Get the first spectator
            spectator_threads[conn].join()  # Wait for their thread to terminate
            del spectator_threads[conn]  # Remove from the thread map

            # Update rfiles and wfiles for the new players
            rfiles[player_id] = conn.makefile('r')
            wfiles[player_id] = conn.makefile('w')
            wfiles[player_id].write("[INFO] You are now a player in the game.\n")
            wfiles[player_id].flush()
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
                conn, addr = s.accept()
                print(f"[INFO] Accepted connection from {addr}")
                connections.append(conn)

                # If there are fewer than 2 players, assign them as players
                if None in rfiles:
                    player_id = rfiles.index(None)
                    rfiles[player_id] = conn.makefile('r')
                    wfiles[player_id] = conn.makefile('w')
                    wfiles[player_id].write("[INFO] You are now a player in the game.\n")
                    wfiles[player_id].flush()

                    # Start the game if both players are connected
                    if None not in rfiles:
                        print("[INFO] Both players connected. Starting the game...")
                        broadcast_to_spectators("[INFO] The game is starting (spectate view)...\n")
                        run_two_play_game_online(rfiles, wfiles, spectators)
                        game_over_event.set()

                        # Reset the game state for the next game
                        rfiles = [None, None]
                        wfiles = [None, None]
                        game_over_event.clear()

                        # Promote spectators to players for the next game
                        if not promote_spectators_to_players(rfiles, wfiles):
                            print("[INFO] Waiting for more spectators to start the next game...")
                else:
                    # Otherwise, treat them as a spectator
                    spectators.append(conn)
                    spectator_thread = threading.Thread(target=handle_spectator, args=(conn, addr), daemon=True)
                    spectator_thread.start()
                    spectator_threads[conn] = spectator_thread

            except KeyboardInterrupt:
                print("\n[INFO] Server shutting down...")
                break
            except BrokenPipeError or ConnectionResetError:
                print("[INFO] A client disconnected unexpectedly.")
            except Exception as e:
                print(f"[ERROR] Server error: {e}")


if __name__ == "__main__":
    main()