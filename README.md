# CITS3002 Project
This project implements a client-server architecture for a battleship game run on the command line.

## Install Dependencies
The server and client uses `pycryptodome` for encryption and `pytest` for testing. To install:
```bash
pip install pycryptodome
pip install pytest
```

`pycryptodome` and `pytest` are the only python modules required. To be safe however, we have also provided a requirements.txt file. To install:
```bash
python3 install -r requirements.txt
```

## Running The Game

DO THIS IN THE ROOT DIRECTORY!!!!

To run the game, navigate to the project root and first launch the server:
```bash
python3 server.py
```

Next, you can connect an arbitrary number of clients by running the following:
```bash
python3 client.py
```

Only 2 clients at a time will be in a game, the rest are spectators. Spectators will be placed in a waiting queue if a game is ongoing, and whoever joined earliest will be served first. You can connect up to 12 clients to the server at a time.

## Running T4 Protocol

Perform all in root directory `/vuln`.  

### T4.1 Protocol + checksum

Can test with the following:
- Run `server` and `client` as normal and inspect `protocol.log` when finished.
- Run `python3 test_protocol.py` and inspect `protocol.log`
- Run `pytest protocol/tests` and to test the protocol
- Run `python3 -m protocol.stats_demo` to demonstrate statistical analysis of CRC16 applied in protocol.

### T4.3 Encryption layer

Added simple encryption layer from pcryptodome, please pip install pcryptodome. To test:

- Run `server` and `client` and read output in `protocol.log`
- Test using `python3 -m protocol.crypto.aes`

### T4.4 Security analysis + mitigation

#### Vulnerability: Replay attack

In `vuln`, have 4 different terminals open.
1. `python3 server.py` to start the server
2. `python3 attacker.py` to start the attacker
3. `python3 client.py --port {ATTACKER_LISTEN_PORT}` as defined in `config.py` to connect to the attacker (MiTM).
4. `python3 client.py` to connect to the server.

Play the game as normal, and then run `r` in the attacker terminal to replay the attack. The attacker will send the same command to the server as the client. Packets are logged in `protocol.log` and the attacker will replay packets sent to the server as seen in the server output.

#### Patch: Nonce

In the root directory, run the same thing as above.

Try the `r` command in the attacker terminal again. The server will reject the replayed packet and the attacker will not be able to send the same command to the server.