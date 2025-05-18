#!/usr/bin/env python3
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from threading import Thread, Event
from config import *
from battleship_2p import run_two_player_battleship_game
from player import Player
from protocol import send_message, receive_message
import time
import logging

logger = logging.getLogger("server")
logger.setLevel(logging.INFO)
logger.propagate = False

# Add a handler with formatting only if not already present
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


players = {}                    # username as key, Player object as value
currently_playing = []          # Store usernames of players
waiting_lobby_queue = []        # Store usernames of spectators
game_ongoing_event = Event()    # Event to indicate if a game is ongoing

def send_chat_message(message, source_username):
    """
    Broadcast a chat message to all players except the source.
    """
    logger.info(f"{source_username} IM: {message.strip()}")
    for username, player in players.items():
        if username != source_username and not player.is_disconnected.is_set():
            try:
                player.send(f"[CHAT] [{source_username}] {message.strip()}")
            except Exception as e:
                logger.error(f"Error broadcasting message to {username}: {e}")

def send_waiting_lobby_update(message):
    """
    Broadcast a message to all spectators.
    """
    for username, player in players.items():
        if player.is_spectator.is_set() and not player.is_disconnected.is_set():
            try:
                if message == "UPDATE":
                    message = f"[INFO] You are currently in position {waiting_lobby_queue.index(username) + 1} in the waiting lobby."
                player.send(message)
            except Exception as e:
                logger.error(f"Error broadcasting message to {username}: {e}")

def handle_reconnect(username, conn):
    """
    Handle reconnection of a player.
    """
    players[username].is_disconnected.clear()
    players[username].conn = conn
    players[username].send(f"[INFO] Welcome back {username}!")
    if username in currently_playing:
        players[username].send(f"[INFO] You have been reconnected to the ongoing game!")
    else:
        waiting_lobby_queue.append(username)
        players[username].is_spectator.set()
        players[username].send(f"[INFO] You are now in the waiting lobby.")
    logger.info(f"Player {username} reconnected to current game.")

def init_client(conn, addr):
    """
    initialize a client connection, either create a new Player object or reconnect to an existing one.
    Either returns the username or None if the user disconnected.
    """
    send_message(conn, "[INFO] Welcome to the Battleship game!".encode('utf-8'))
    send_message(conn, "[INFO] Please enter your username or type 'quit' to leave:".encode('utf-8'))

    try:
        while True:
            line = receive_message(conn).decode('utf-8')
            # Check for enter key
            if line == '\n': continue
            username = line.strip()

            # Check if user wants to quit
            if username.lower() == "quit":
                logger.info(f"Spectator {addr} disconnected or quit.")
                return None
            # Check if user has disconnected
            elif username == '':
                logger.info(f"Client {addr} disconnected.")
                return None
            # Check if username is already taken
            elif username in players:
                if players[username].is_disconnected.is_set():
                    handle_reconnect(username, conn)
                    return username
                else:
                    send_message(conn, f"[ERROR] Username '{username}' is already taken. Please choose another one.".encode('utf-8'))
                    continue
            # Finally, if username is not taken, initialize the new player
            else:
                waiting_lobby_queue.append(username)
                players[username] = Player(username, conn)
                players[username].is_spectator.set()
                players[username].send(f"[INFO] Welcome {username}! You are now in the waiting lobby.")
                players[username].send(f"[INFO] You are currently in position {waiting_lobby_queue.index(username) + 1} in the waiting lobby.")
                return username
            
    except Exception as e:
        logger.error(f"Error receiving messages: {e}")

def receive_client_messages(conn, addr):
    """
    Thread function to receive messages from a client.
    """
    username = init_client(conn, addr)
    if not username: return

    # Pre-process input before sending to battleship game
    try:
        while True:
            line = receive_message(conn).decode('utf-8')
            logger.info(f"Received message from {username}: {line.strip()}")

            # Check if user wants to quit
            if line.strip().lower() in ["quit", "exit", "forfeit"]:
                logger.info(f"Spectator {addr} disconnected or quit.")
                break
            # Check for enter key
            elif line == '\n': continue
            # Check for CHAT command
            elif username in waiting_lobby_queue and line.strip().upper()[:4] == "CHAT":
                send_chat_message(line[5:], username)
            # Check if user has diconnected
            elif line == '':
                logger.info(f"{username} disconnected.")
                players[username].is_disconnected.set()
                if username in waiting_lobby_queue:
                    waiting_lobby_queue.remove(username)
                    send_waiting_lobby_update("UPDATE")
                break
            # Finally, if user is in the game, add input to their queue
            elif username in players and players[username].is_current_player.is_set():
                players[username].input_queue.put(line.strip())
    except Exception as e:
        logger.error(f"Error receiving messages from {username}: {e}")
        players[username].is_disconnected.set()

def check_start_game():
    """
    Check if the game can start, and if so, start the game, then handle the game end.
    This function runs in a separate thread and checks the waiting lobby queue every second.
    """
    global currently_playing
    while True: 
        time.sleep(1)
        # Start the game if there are at least 2 players in the waiting lobby
        if len(waiting_lobby_queue) >= 2 and not game_ongoing_event.is_set():
            logger.info("Starting the game...")
            game_ongoing_event.set()
            currently_playing = [waiting_lobby_queue.pop(0), waiting_lobby_queue.pop(0)]

            # Clear spectator status of players in the game
            for username in currently_playing:
                players[username].is_spectator.clear()

            # Game starting messages
            send_waiting_lobby_update("UPDATE")
            send_waiting_lobby_update(f"[INFO] Game is starting: {players[username].username} vs {players[username].username}.")
            for username in currently_playing:
                players[username].send(f"[INFO] You are now a player in the game, game is starting in...")
            send_waiting_lobby_update(f"[INFO] Game starting in...")
            for i in range(3, 0, -1):
                send_waiting_lobby_update(f"[INFO] {i}...")
                for username in currently_playing:
                    players[username].send(f"[INFO] {i}...")
                time.sleep(1)

            run_two_player_battleship_game(players, currently_playing[0], currently_playing[1])

            # Handle game end, add back to waiting lobby if they are still connected
            for username in currently_playing:
                if not players[username].is_disconnected.is_set():
                    players[username].is_current_player.clear()
                    players[username].is_spectator.set()
                    players[username].send(f"[INFO] Game over! You are back in the waiting lobby.\n")
                    waiting_lobby_queue.append(username)
            currently_playing = []
            game_ongoing_event.clear()
            logger.info("Game ended. Waiting for new players...")

def main():
    """
    Start the server and accept connections.
    """
    logger.info(f"Server listening on {HOST}:{PORT}")
    with socket(AF_INET, SOCK_STREAM) as s:
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(MAX_CONNECTIONS)
        logger.info("Waiting for players to connect...")
        
        # Start a thread to check for game start conditions
        check_start_game_thread = Thread(target=check_start_game, daemon=True)
        check_start_game_thread.start()

        # Continuously accept new connections and start a new thread for each client
        while True:
            try:
                conn, addr = s.accept()
                logger.info(f"Accepted connection from {addr}")
                client_thread = Thread(target=receive_client_messages, args=(conn, addr), daemon=True)
                client_thread.start()
            except KeyboardInterrupt:
                logger.info("Server shutting down...")
                break
            except Exception as e:
                logger.error(f"Server error: {e}")

if __name__ == "__main__":
    main()