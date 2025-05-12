#!/usr/bin/env python3
from sys import stdin
from select import select
from socket import socket, AF_INET, SOCK_STREAM
from threading import Event, Thread
from config import *
game_ongoing_event = Event()
your_turn_event = Event()

def receive_server_messages(rfile):
    while True:
        line = rfile.readline().strip()
        if not line:
            logging.info("Server disconnected.")
            game_ongoing_event.set()
            break

        line = line.strip()
        if line == "GAME_START":
            logging.info("The game is starting!")
            game_ongoing_event.set()
        elif line == "YOUR_TURN":
            your_turn_event.set()
        elif line == "OPPONENT_TURN":
            your_turn_event.clear()
        else:
            print(line)

def main():
    with socket(AF_INET, SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"Connected to server at {HOST}:{PORT}")
        rfile = s.makefile('r')
        wfile = s.makefile('w')
        receiver_thread = Thread(target=receive_server_messages, args=(rfile,), daemon=True)
        receiver_thread.start()
        try:
            while True:
                ready, _, _ = select([stdin], [], [], 1)
                if ready:
                    user_input = stdin.readline()
                    wfile.write(user_input)
                    wfile.flush()
                    if user_input.lower() == 'quit':
                        logging.info("Exiting...")
                        game_ongoing_event.clear()
                        break
                    elif user_input == "":
                        continue
        except KeyboardInterrupt:
            logging.info("Client exiting due to keyboard interrupt.")
            game_ongoing_event.clear()
        finally:
            wfile.close()

if __name__ == "__main__":
    main()