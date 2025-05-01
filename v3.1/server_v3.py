#!/usr/bin/env python3

"""
server_v2.py

Tier 2.2: Enables multiple games of Battleship to be played without restarting the server.
Uses the two-player game logic defined in battleship_2p.py (run_two_play_game_online).
"""

import socket
import threading
from battleship_2p import *
import select

HOST = '127.0.0.1'
PORT = 5000
game_over_event = threading.Event()  # Event to signal when the game is over

def handle_spectator(conn, addr, rfiles, wfiles, current_players, connections):
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
                # Exit if the game is over and the connection is in the current_players list
                if not game_over_event.is_set() and conn in current_players:
                    print(f"[INFO] Spectator {addr} is now a player. Exiting spectator mode.")
                    wfile.write("[INFO] You are now a player.\n")
                    wfile.flush()
                    rfiles[current_players.index(conn)] = rfile
                    wfiles[current_players.index(conn)] = wfile
                    break

                # Use select to check if input is available
                ready, _, _ = select.select([rfile], [], [], 1)  # Timeout of 1 second
                if ready:
                    line = rfile.readline().strip()
                    if not line or line.lower() == "quit":
                        print(f"[INFO] Spectator {addr} disconnected.")
                        if conn in connections:
                            connections.remove(conn)
                        break
    except Exception as e:
        print(f"[ERROR] Error with spectator {addr}: {e}")

def main():
    """Main server function to accept connections and handle clients."""
    connections = []  # List of all connections (players and spectators)
    spectator_queue = []   # List of spectator connections
    current_players = [None, None]
    rfiles = [None, None]
    wfiles = [None, None]
    spectator_threads = {}

    print(f"[INFO] Server listening on {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(12)  # Allow up to 12 connections in the waiting queue
        print("[INFO] Waiting for players to connect...")

        while True:
            try:
                conn, addr = s.accept()
                connections.append(conn)
                spectator_queue.append(conn)  # Add to the spectator queue
                spectator_thread = threading.Thread(target=handle_spectator, 
                                                    args=(conn, addr, rfiles, wfiles, current_players, connections), 
                                                    daemon=True)
                spectator_thread.start()
                spectator_threads[conn] = spectator_thread

                if not game_over_event.is_set() and len(spectator_queue) >= 2:
                    # Promote the first two spectators to players
                    for player_id in range(2):
                        conn = spectator_queue.pop(0)
                        current_players[player_id] = conn  # Update current players
                        spectator_threads[conn].join()
                        del spectator_threads[conn]
                    try:
                        run_two_play_game_online(rfiles, wfiles, spectator_queue, game_over_event)
                    except (BrokenPipeError, ConnectionResetError):
                        print("[INFO] A player disconnected during the game.")
                        # Notify the remaining player and reset the game state
                        for wfile in wfiles:
                            if wfile:
                                try:
                                    wfile.write("[INFO] The other player has disconnected. You are being returned to the lobby.\n")
                                    wfile.write("DISCONNECT")
                                    wfile.flush()
                                except Exception:
                                    pass  # Ignore errors when notifying the remaining player
                                finally:
                                    wfile.close()

                        for conn in current_players:
                            if conn and conn.fileno() == -1:  # Check if the connection is closed
                                connections.remove(conn)
                                conn.close()

                        # Reset the game state
                        rfiles = wfiles = current_players = [None, None]
                        game_over_event.clear()
                        continue  # Return to the main loop
            except KeyboardInterrupt:
                print("\n[INFO] Server shutting down...")
                break
            except (BrokenPipeError, ConnectionResetError):
                continue
            except Exception as e:
                print(f"[ERROR] Server error: {e}")

            connections = [conn for conn in connections if conn.fileno() != -1]
        

if __name__ == "__main__":
    main()