#!/usr/bin/env python3
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from threading import Thread, Event
from config import *
from battleship_2p import run_two_player_battleship_game
from player import Player
import time

players = {} # username as key, Player object as value
currently_playing = [] # Store usernames of players
waiting_lobby_queue = [] # Store usernames of spectators
game_ongoing_event = Event()

def send_player_message(message, source_username):
    print(f"[CHAT ({source_username})] {message.strip()}")
    for username, player in players.items():
        if username in currently_playing or username == source_username or player.is_disconnected.is_set(): continue
        try:
            player.send(f"[CHAT] [{source_username}] {message.strip()}")
        except Exception as e:
            logging.error(f"Error broadcasting message to {username}: {e}")

def send_waiting_lobby_update(message):
    """
    Broadcast a message to all spectators.
    """
    for username, player in players.items():
        if player.is_spectator.is_set() and not player.is_disconnected.is_set():
            try:
                if message == "UPDATE":
                    message = f"[INFO] You are currently in position {waiting_lobby_queue.index(username) + 1} in the waiting lobby."
                player.wfile.write(message + '\n')
                player.wfile.flush()
            except Exception as e:
                logging.error(f"Error broadcasting message to {username}: {e}")

def init_client(conn, addr):
    """
    Continuously receive and display messages from the server.
    """
    rfile = conn.makefile('r')
    wfile = conn.makefile('w')
    wfile.write("[INFO] Please enter your username or type 'quit' to leave: \n")
    wfile.flush()
    try:
        while True:
            line = rfile.readline()
            if line == '\n': continue
            username = line.strip()
            if username.lower() == "quit":
                logging.info(f"Spectator {addr} disconnected or quit.")
                return None
            elif username == '':
                logging.info(f"Client {addr} disconnected.")
                return None
            elif username in players:
                # Check if user has previously disconnected
                if players[username].is_disconnected.is_set():
                    players[username].is_disconnected.clear()
                    players[username].wfile = wfile
                    players[username].rfile = rfile
                    players[username].wfile.write(f"[INFO] Welcome back {username}!\n")
                    players[username].wfile.flush()
                    if username in currently_playing:
                        players[username].wfile.write(f"[INFO] You have been reconnected to the ongoing game!\n")
                        players[username].wfile.flush()
                    else:
                        waiting_lobby_queue.append(username)
                        players[username].is_spectator.set()
                        players[username].wfile.write(f"[INFO] You are now in the waiting lobby.\n")
                        players[username].wfile.flush()
                    return username
                else:
                    wfile.write(f"[ERROR] Username '{username}' is already taken. Please choose another one.\n")
                    wfile.flush()
                    continue
            else:
                waiting_lobby_queue.append(username)
                players[username] = Player(username, wfile, rfile)
                players[username].is_spectator.set()
                wfile.write(f"[INFO] Welcome {username}! You are now in the waiting lobby.\n")
                players[username].send(f"[INFO] You are currently in position {waiting_lobby_queue.index(username) + 1} in the waiting lobby.")
                wfile.flush()
                return username
    except Exception as e:
        logging.error(f"Error receiving messages: {e}")

# THREAD FUNCTION
def receive_client_messages(conn, addr):
    username = init_client(conn, addr)
    if not username: return

    # Pre-process input before sending to battleship game
    try:
        while True:
            line = players[username].rfile.readline()
            if line.strip().lower() in ["quit", "exit", "forfeit"]:
                logging.info(f"Spectator {addr} disconnected or quit.")
                break
            elif line == '\n': continue
            elif line == '':
                logging.info(f"{username} disconnected.")
                players[username].is_disconnected.set()
                if username in waiting_lobby_queue:
                    waiting_lobby_queue.remove(username)
                    send_waiting_lobby_update("UPDATE")
                break
            elif username in waiting_lobby_queue and line.strip().upper()[:4] == "CHAT":
                send_player_message(line[5:], username)
            # only send to the player object if it is their turn
            elif username in players and players[username].is_current_player.is_set():
                players[username].input_queue.put(line.strip())
    except Exception as e:
        logging.error(f"Error receiving messages from {username}: {e}")
        players[username].is_disconnected.set()

def check_start_game():
    """
    Check if the game can start.
    """
    global currently_playing
    while True: 
        time.sleep(1)  # Check every second
        # print(currently_playing, waiting_lobby_queue, players.keys())
        if len(waiting_lobby_queue) >= 2 and not game_ongoing_event.is_set():
            logging.info("Starting the game...")
            game_ongoing_event.set()
            currently_playing = [waiting_lobby_queue.pop(0), waiting_lobby_queue.pop(0)]

            for username in currently_playing:
                players[username].is_spectator.clear()
            send_waiting_lobby_update(f"[INFO] Game is starting in 5 seconds... {players[username].username} vs {players[username].username}")
            send_waiting_lobby_update("UPDATE")
    
            run_two_player_battleship_game(players, currently_playing[0], currently_playing[1])

            for username in currently_playing:
                if not players[username].is_disconnected.is_set():
                    players[username].is_current_player.clear()
                    players[username].is_spectator.set()
                    players[username].wfile.write(f"[INFO] Game over! You are back in the waiting lobby.\n")
                    players[username].wfile.flush()
                    waiting_lobby_queue.append(username)

            currently_playing = []
            game_ongoing_event.clear()
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