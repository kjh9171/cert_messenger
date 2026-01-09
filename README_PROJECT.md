# Cert Messenger — Prototype

This repository contains a minimal prototype for a channel-based messenger with:
- channel link join
- simple notes/todo/schedule entries
- auto-delete (TTL) for notes
- Docker Compose for local deployment

Quick start (macOS / Docker installed):

1. Build & run:

```bash
docker-compose up --build
```

2. Open the frontend:

http://localhost:8080

3. Create a channel (example using curl):

```bash
curl -X POST -H "Content-Type: application/json" -d '{"name":"team1","limit":8}' http://localhost:3100/api/channels
```

4. Create multiple channels (script examples):

```bash
# shell script (requires jq):
./scripts/create_channels.sh 5 myprefix

# node script:
node scripts/create_channels.js http://localhost:3100 5 myprefix
```

Backend URL after change: http://localhost:3100

Files of interest:
- [backend/src/server.js](backend/src/server.js)
- [frontend/index.html](frontend/index.html)
- [frontend/app.js](frontend/app.js)
- [docker-compose.yml](docker-compose.yml)

Next steps:
- Replace in-memory store with PostgreSQL/Redis
- Add authentication and end-to-end encryption
- Add CI and push to GitHub
