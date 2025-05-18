# Terminal 1
$ python3 server_vulnerable.py
# ... server processes twice ...

# Terminal 2
$ python3 attacker_vulnerable.py 4000 localhost 5000

# Terminal 3
$ python3 client_vulnerable.py

# Result: Server logs two Received SEQ=1, payload=b'FIRE 3 4' entries.
# WHY BAD: Replay attack = undermine integrity of the protocol.
# E.g. a bank transfer of $1000 could be replayed to transfer $1000 again.

# MITM: At its core, a “port‑redirect” MitM works by tricking the victim’s TCP/IP stack into sending traffic for some service through your machine, where you can inspect, modify, and then forward it on to the real server.