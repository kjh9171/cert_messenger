Multi-user setup (remote server)

1) Start the standalone server (can be hosted on any machine reachable by clients):

```bash
cd server
npm install
node index.js
```

Server listens on port 4000 by default. Ensure firewall allows incoming connections.

2) Start desktop clients (Electron) and point them to the server URL (e.g. http://your-server:4000) in the Server field, then click Connect.

3) Multiple clients can connect to the same channel and share notes in real time.

Security: this prototype does not include auth or TLS. For production, add HTTPS, authentication, and rate-limiting.
