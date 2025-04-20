#!/usr/bin/env python3

"""
server.py

Tier 1.2: Enables two players to connect and play Battleship against each other.
Uses the two-player game logic defined in battleship.py (run_two_player_game_online).
"""

import socket, threading
from battleship import run_single_player_game_online, run_two_player_game_online

HOST = '127.0.0.1'
PORT = 5000

def handle_client(conn, addr):
    """
    Handles a single client connection.
    Runs the Battleship game logic for the connected client.
    """
    print(f"[INFO] Handling client from {addr}")
    try:
        with conn:
            rfile = conn.makefile('r')
            wfile = conn.makefile('w')
            run_single_player_game_online(rfile, wfile)
    except Exception as e:
        print(f"[ERROR] Exception while handling client {addr}: {e}")
    finally:
        print(f"[INFO] Client {addr} disconnected.")

def main():
    print(f"[INFO] Server listening on {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(2)
        
        # 1. Accept connections in a loop
        conns = []
        while len(conns) < 2:
            conn, addr = s.accept()
            print(f"[INFO] Player {len(conns)+1} connected from {addr}")
            conns.append(conn)

        try: 
            # Makefile wrappers
            rfile1 = conns[0].makefile('r')
            wfile1 = conns[0].makefile('w')
            rfile2 = conns[1].makefile('r')
            wfile2 = conns[1].makefile('w')

            # Start the game between the two players
            run_two_player_game_online(rfiles, wfiles)

        except KeyboardInterrupt:
            print("\n[INFO] Server shutting down...")
        except Exception as e:
            print(f"[ERROR] Server error: {e}")

# HINT: For multiple clients, you'd need to:
# 1. Accept connections in a loop
# 2. Handle each client in a separate thread
# 3. Import threading and create a handle_client function

if __name__ == "__main__":
    main()