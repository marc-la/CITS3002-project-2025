#!/usr/bin/env python3

"""
server.py

Tier 2.2: Enables multiple games of Battleship to be played without restarting the server.
Uses the two-player game logic defined in battleship.py (run_two_play_game_online).
"""

import socket
import threading
from battlehsip_2p import *

HOST = '127.0.0.1'
PORT = 5000

def handle_client(conn, addr, player_id, rfiles, wfiles, game_over_event):
    """
    Handles a single client connection.
    Adds the client's file-like objects to the shared lists and waits for the game to start.
    """
    print(f"[INFO] Player {player_id + 1} connected from {addr}")
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

    except Exception as e:
        print(f"[ERROR] Exception while handling client {addr}: {e}")
    finally:
        print(f"[INFO] Player {player_id + 1} disconnected.")
        # Ensure the other player is also disconnected
        game_over_event.set()

def main():
    """
    Main server function to accept connections and handle clients using threads.
    Supports multiple games without restarting the server.
    """
    print(f"[INFO] Server listening on {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(2)  # Allow up to 2 connections
        print("[INFO] Waiting for players to connect...")

        while True:
            # Shared lists to store file-like objects for both players
            rfiles = [None, None]
            wfiles = [None, None]

            # Event to signal when the game is over
            game_over_event = threading.Event()

            try:
                # Accept exactly two players
                for player_id in range(2):
                    conn, addr = s.accept()
                    client_thread = threading.Thread(
                        target=handle_client, args=(conn, addr, player_id, rfiles, wfiles, game_over_event), daemon=True
                    )
                    client_thread.start()

                # Wait for the game to finish or a disconnection
                game_over_event.wait()  # Block until the game is over or a client disconnects
                print("[INFO] Game has ended or a client disconnected.")

                # Disconnect both players
                for wfile in wfiles:
                    if wfile:
                        try:
                            wfile.write("The game has ended or a player disconnected. Disconnecting...\n")
                            wfile.flush()
                        except Exception:
                            pass  # Ignore errors during disconnection
                print("[INFO] Returning to waiting for new connections...")

            except KeyboardInterrupt:
                print("\n[INFO] Server shutting down...")
                break
            except Exception as e:
                print(f"[ERROR] Server error: {e}")

if __name__ == "__main__":
    main()