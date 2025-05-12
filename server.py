#!/usr/bin/env python3
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from threading import Thread, Event, Lock
from config import *
from select import select
from battleship import run_two_player_battleship_game

client_files = {} # username as key, (wfile, rfile) as value
client_conns = {} # username as key, (conn, addr) as value
players = [None, None] # Store username of players
waiting_lobby_queue = [] # Store usernames of spectators
game_ongoing_event = Event()

def handle_disconnect(username):
    """
    Handle client disconnection.
    """
    pass

# THREAD FUNCTION
def receive_client_messages(conn, addr):
    rfile = conn.makefile('r')
    wfile = conn.makefile('w')
    wfile.write("[INFO] Welcome to Battleship!")
    wfile.flush()
    username = get_username_from_client(rfile)
    client_files[username] = (wfile, rfile)
    client_conns[username] = (conn, addr)

    # Every second, check for client input check for disconnect
    while True:
        ready, _, _ = select([rfile], [], [], 1)  
        if ready:
            line = rfile.readline().strip()
            if line.lower() == "quit":
                logging.info(f"Spectator {addr} disconnected or quit.")
                break
            elif not line:
                continue
        if conn.fileno() == -1:
            logging.info(f"Client {addr} disconnected.")
            handle_disconnect(username)
            break

def get_username_from_client(rfile):
    """
    Continuously receive and display messages from the server.
    """
    pass
    # wfile.write("[INFO] Please enter your username or type 'quit' to leave: ")
    # wfile.flush()
    # try:
    #     while True:
    #         ready, _, _ = select([rfile], [], [], 1)  # Timeout of 1 second
    #         if ready:
    #             line = rfile.readline().strip()
    #             if not line:
    #                 break
    #             print(line)
    # except Exception as e:
    #     logging.error(f"Error receiving messages: {e}")

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

        while True:
            try:
                conn, addr = s.accept()
                logging.info(f"Accepted connection {conn} from {addr}")
                client_thread = Thread(target=receive_client_messages, args=(conn, addr), daemon=True)
                client_thread.start()
                if len(waiting_lobby_queue) >= 2 and not game_ongoing_event.is_set:
                    logging.info("Starting the game...")
                    players = [waiting_lobby_queue.pop(0), waiting_lobby_queue.pop(0)]
                    run_two_player_battleship_game(players, client_files)
                    game_ongoing_event.clear()
                    players = [None, None]
                    
            except KeyboardInterrupt:
                logging.info("Server shutting down...")
                break
            except Exception as e:
                logging.error(f"Server error: {e}")