# CITS3002 Project
This project implements a client-server architecture for a battleship game run on the command line.

## Install Dependencies
The server and client uses `pycryptodome` for encryption. To install:
```
pip install pycryptodome
```

`pycryptodome` is the only python module required. To be safe however, we have also provided a requirements.txt file. To install:
```
python3 install -r requirements.txt
```

## Running The Game
To run the game, navigate to the project root and first launch the server:
```
python3 server.py
```

Next, you can connect an arbitrary number of clients by running the following:
```
python3 client.py
```

Only 2 clients at a time will be in a game, the rest are spectators. Spectators will be placed in a waiting queue if a game is ongoing, and whoever joined earliest will be served first.
