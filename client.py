#!/usr/bin/env python3
from sys import stdin
from socket import socket, AF_INET, SOCK_STREAM
from threading import Event, Thread
from config import *
from protocol import send_packets, receive_packets

game_over_event = Event()

def receive_server_messages(conn):
    while not game_over_event.is_set():
        line = receive_packets(conn)
        if not line:
            logging.info("Server disconnected.")
            break
        print(line)

def main():
    with socket(AF_INET, SOCK_STREAM) as conn:
        conn.connect((HOST, PORT))
        print(f"Connected to server at {HOST}:{PORT}")
        receiver_thread = Thread(target=receive_server_messages, args=(conn,), daemon=True)
        receiver_thread.start()
        try:
            while True:
                user_input = stdin.readline()
                send_packets(user_input, conn)
                if user_input.lower() in ['quit', 'exit', 'forfeit']:
                    game_over_event.set()
                    logging.info("Exiting...")
                    break
                elif user_input == "":
                    continue
        except KeyboardInterrupt:
            logging.info("Client exiting due to keyboard interrupt.")
            game_over_event.set()

if __name__ == "__main__":
    main()