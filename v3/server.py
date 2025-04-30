#!/usr/bin/env python3

# Imports
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from threading import Thread, Lock, Event, current_thread
from battleship_multiplayer import TwoPlayerBattleshipGame
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Global Variables
HOST = "127.0.0.1"
PORT = 5000

class Server:
    """
    Server Class

    This class implements a multi-threaded server for hosting multiplayer Battleship games. 
    It manages client connections, facilitates communication between players and spectators, 
    and orchestrates the game lifecycle. The server supports multiple concurrent games and 
    ensures thread-safe operations using synchronisation mechanisms.

    Key Responsibilities:
    - Accept and manage client connections (players and spectators).
    - Assign roles (player or spectator) to connected clients.
    - Facilitate communication between players during gameplay.
    - Broadcast game updates to spectators in real-time.
    - Handle disconnections and clean up resources gracefully.
    - Ensure thread-safe access to shared resources.

    Attributes:
        host (str): The IP address the server binds to.
        port (int): The port number the server listens on.
        lock (Lock): A threading lock to ensure thread-safe operations.
        connections (list): A list of all active client connections.
        spectators (list): A list of spectator connections.
        games (list): A list of active game instances.
        threads (list): A list of threads handling client connections.
        running (bool): A flag indicating whether the server is running.

    This server is designed to be scalable, robust, and extensible for future enhancements.
    """

    def __init__(self, host='127.0.0.1', port=5000, max_connections=12):
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.connections = []
        self.spectators = []
        self.spectator_threads = {}
        self.rfiles = [None, None]
        self.wfiles = [None, None]
        self.game_over_event = Event()
        self.lock = Lock()  
        self.running = True
    
    def start(self):
        """
        Start the server and accept connections.
        """
        logging.info(f"Server listening on {self.host}:{self.port}")
        with socket(AF_INET, SOCK_STREAM) as s:
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen(self.max_connections)
            logging.info("Waiting for players to connect...")

            while self.running:
                try:
                    conn, addr = s.accept()
                    logging.info(f"Accepted connection from {addr}")
                    self.connections.append(conn)
                    self.handle_new_connection(conn, addr)
                except KeyboardInterrupt:
                    logging.info("Server shutting down...")
                    self.running = False
                except Exception as e:
                    logging.error(f"Server error: {e}")
    
    def handle_new_connection(self, conn, addr):
        """
        Handle a new connection, assigning it as a player or spectator.
        """
        with self.lock:
            if None in self.rfiles:
                self.assign_player(conn, addr)
            else:
                self.assign_spectator(conn, addr)

    def assign_player(self, conn, addr):
        """
        Assign a connection as a player.
        """
        player_id = self.rfiles.index(None)
        self.rfiles[player_id] = conn.makefile('r')
        self.wfiles[player_id] = conn.makefile('w')
        self.wfiles[player_id].write("[INFO] You are now a player in the game.\n")
        self.wfiles[player_id].flush()

        if None not in self.rfiles:
            logging.info("Both players connected. Starting the game...")
            self.broadcast_to_spectators("[INFO] The game is starting (spectate view)...\n")
            self.start_game()

    def assign_spectator(self, conn, addr):
        """
        Assign a connection as a spectator.
        """
        self.spectators.append(conn)
        spectator_thread = Thread(target=self.handle_spectator, args=(conn, addr), daemon=True)
        spectator_thread.start()
        self.spectator_threads[conn] = spectator_thread
    
    def handle_spectator(self, conn, addr):
        """
        Handle a spectator connection.
        """
        logging.info(f"Spectator connected from {addr}")
        try:
            with conn:
                rfile = conn.makefile('r')
                wfile = conn.makefile('w')
                wfile.write("[INFO] You are now spectating the game. Type 'quit' to leave.\n")
                wfile.flush()

                while True:
                    line = rfile.readline().strip()
                    if not line or line.lower() == "quit":
                        logging.info(f"Spectator {addr} disconnected.")
                        break
        except Exception as e:
            logging.error(f"Error with spectator {addr}: {e}")
        finally:
            with self.lock:
                if conn in self.spectators:
                    self.spectators.remove(conn)
                if conn in self.spectator_threads:
                    del self.spectator_threads[conn]
        
    def broadcast_to_spectators(self, message):
        """
        Broadcast a message to all spectators.
        """
        with self.lock:
            # Iterate over a copy
            for spectator in self.spectators[:]:
                try:
                    spectator.sendall(message.encode('utf-8'))
                except Exception:
                    self.spectators.remove(spectator)
    
    def start_game(self):
        """
        Start a new game.
        """
        try:
            game = TwoPlayerBattleshipGame(self.rfiles, self.wfiles, self.spectators)
            game.start_game()
        except Exception as e:
            logging.error(f"Error during game: {e}")
        finally:
            self.reset_game_state()
            
    def reset_game_state(self):
        """
        Reset the game state for the next game.
        """
        self.rfiles = [None, None]
        self.wfiles = [None, None]
        self.game_over_event.clear()
    
    def shutdown(self):
        """
        Clean up resources and shut down the server.
        """
        self.running = False
        for conn in self.connections:
            try:
                conn.close()
            except Exception as e:
                logging.error(f"Error closing connection: {e}")
        for thread in self.spectator_threads.values():
            thread.join()
        logging.info("Server shutdown complete.")

if __name__ == "__main__":
    server = Server(host=HOST, port=PORT)
    server.start()