#!/usr/bin/env python3
from sys import stdin
from socket import socket, AF_INET, SOCK_STREAM
from threading import Event, Thread
from config import *
from protocol import send_message, receive_message
import logging
import argparse

logger = logging.getLogger("client")
logger.setLevel(logging.INFO)
logger.propagate = False

# Add a handler with formatting only if not already present
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

exit_condition = Event()

def receive_server_messages(conn):
    try:
        while not exit_condition.is_set():
            line = receive_message(conn, key=KEY).decode('utf-8')
            if not line:
                logger.info("Server disconnected.")
                exit_condition.set()
                break 
            print(line)
    except Exception as e:
        logger.error(f"Server disconnected: {e}")
        exit_condition.set()

def main():
    parser = argparse.ArgumentParser(description="Client for the game server.")
    parser.add_argument('-p', '--port', type=int, default=PORT, help='Port to connect to (default from config.py)')
    args = parser.parse_args()

    with socket(AF_INET, SOCK_STREAM) as conn:
        conn.connect((HOST, args.port))
        print(f"Connected to server at {HOST}:{args.port}")
        receiver_thread = Thread(target=receive_server_messages, args=(conn,), daemon=True)
        receiver_thread.start()
        try:
            while not exit_condition.is_set():
                user_input = stdin.readline()
                send_message(conn, user_input.encode('utf-8'), key=KEY, use_timestamp=False)
                if user_input.strip().lower() in ['quit', 'exit', 'forfeit']:
                    exit_condition.set()
                    print("Exiting client...")
                    return
        except KeyboardInterrupt:
            logger.info("Client exiting due to keyboard interrupt.")
            exit_condition.set()
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            exit_condition.set()

if __name__ == "__main__":
    main()