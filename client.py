#!/usr/bin/env python3
from sys import stdin
from select import select
from socket import socket, AF_INET, SOCK_STREAM
from threading import Event, Thread
from config import *

def receive_server_messages(rfile):
    pass

# THIS RUNS ON THE MAIN THREAD aka the send messages thread
def handle_input(wfile):
    pass

def main():
    with socket(AF_INET, SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        rfile = s.makefile('r')
        wfile = s.makefile('w')
        receiver_thread = Thread(target=receive_server_messages, args=(rfile,), daemon=True)
        receiver_thread.start()
        
        while True:
            # Continuously allow input from the user here
            pass