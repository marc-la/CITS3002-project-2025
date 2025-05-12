#!/usr/bin/env python3
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from threading import Thread, Event
from config import *
from select import select
from battleship_2p import run_two_player_battleship_game
from queue import Queue
from player import Player
import time

client_files = {} # username as key, (wfile, rfile) as value
client_conns = {} # username as key, (conn, addr) as value
players = [None, None] # Store username of players
waiting_lobby_queue = [] # Store usernames of spectators
game_ongoing_event = Event()
player_inputs = [Queue(), Queue()]  # Queues for player inputs

def handle_disconnect(username):
    pass

def broadcast_message(message):
    pass

def get_username_from_client(wfile, rfile, conn, addr):
    """
    Continuously receive and display messages from the server.
    """
    wfile.write("[INFO] Please enter your username or type 'quit' to leave: \n")
    wfile.flush()
    try:
        while True:
            ready, _, _ = select([rfile], [], [], 1)  
            if ready:
                line = rfile.readline()
                if line.strip().lower() == "quit":
                    logging.info(f"Spectator {addr} disconnected or quit.")
                    break
                elif line == '\n': continue
                elif line == '':
                    logging.info(f"Client {addr} disconnected.")
                    break
                elif line.strip() in client_files:
                    wfile.write(f"[ERROR] Username '{line.strip()}' is already taken. Please choose another one.\n")
                    wfile.flush()
                    continue
                else:
                    waiting_lobby_queue.append(line.strip())
                    client_files[line.strip()] = (wfile, rfile)
                    client_conns[line.strip()] = (conn, addr)
                    wfile.write(f"[INFO] Welcome {line.strip()}! You are now in the waiting lobby.\n")
                    wfile.flush()
                    return line.strip()
    except Exception as e:
        logging.error(f"Error receiving messages: {e}")

# THREAD FUNCTION
def receive_client_messages(conn, addr):
    rfile = conn.makefile('r')
    wfile = conn.makefile('w')
    wfile.write("[INFO] Welcome to Battleship! \n")
    wfile.flush()
    username = get_username_from_client(wfile, rfile, conn, addr)

    # Every second, check for client input check for disconnect
    while True:
        ready, _, _ = select([rfile], [], [], 1)  
        if ready:
            line = rfile.readline()
            if line.strip().lower() == "quit":
                logging.info(f"Spectator {addr} disconnected or quit.")
                break
            elif line == '\n': continue
            elif line == '':
                logging.info(f"Client {addr} disconnected.")
                break
            elif username in waiting_lobby_queue and line.strip().lower()[:4] == "CHAT":
                broadcast_message(f"[{username}] {line[5:]}")
            elif username in players:
                print(f"[{username}] {line.strip()}")
                player_inputs[players.index(username)].put(line.strip())

def check_start_game():
    """
    Check if the game can start.
    """
    global players
    while True: 
        time.sleep(1)  # Check every second
        if len(waiting_lobby_queue) >= 2 and not game_ongoing_event.is_set():
            logging.info("Starting the game...")
            players = [waiting_lobby_queue.pop(0), waiting_lobby_queue.pop(0)]
            player0 = Player(players[0], client_files[players[0]][0], player_inputs[0])
            player1 = Player(players[1], client_files[players[1]][0], player_inputs[1])
            player0.send(f"[INFO] Game starting! You are player 1.\n")
            player1.send(f"[INFO] Game starting! You are player 2.\n")
            run_two_player_battleship_game(player0, player1, client_files)
            game_ongoing_event.clear()
            del client_conns[players[0]]
            del client_conns[players[1]]
            del client_files[players[0]]
            del client_files[players[1]]
            players = [None, None]

            logging.info("Game ended. Waiting for new players...")

def main():
    """
    Start the server and accept connections.
    """
    logging.info(f"Server listening on {HOST}:{PORT}")
    with socket(AF_INET, SOCK_STREAM) as s:
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(MAX_CONNECTIONS)
        logging.info("Waiting for players to connect...")
        check_start_game_thread = Thread(target=check_start_game, daemon=True)
        check_start_game_thread.start()

        while True:
            try:
                conn, addr = s.accept()
                logging.info(f"Accepted connection from {addr}")
                client_thread = Thread(target=receive_client_messages, args=(conn, addr), daemon=True)
                client_thread.start()
            except KeyboardInterrupt:
                logging.info("Server shutting down...")
                break
            except Exception as e:
                logging.error(f"Server error: {e}")

if __name__ == "__main__":
    main()