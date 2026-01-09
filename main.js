const { app, BrowserWindow } = require('electron');
const path = require('path');
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
// lowdb is ESM-only in recent versions; import dynamically inside initDb
const { v4: uuidv4 } = require('uuid');

// Setup local DB file
const dbFile = path.join(__dirname, 'data', 'db.json');
let db; // will initialize in initDb

async function initDb(){
  const { Low } = await import('lowdb');
  const { JSONFile } = await import('lowdb/node');
  const adapter = new JSONFile(dbFile);
  db = new Low(adapter);
  await db.read();
  db.data = db.data || { users: [], channels: [], notes: [] };
  await db.write();
}

// Start Express + Socket.IO server
async function startServer() {
  await initDb();
  const serverApp = express();
  serverApp.use(express.json());
  const server = http.createServer(serverApp);
  const io = new Server(server, { cors: { origin: '*' } });

  // Create channel
  serverApp.post('/api/channels', async (req, res) => {
    const { name, limit } = req.body;
    const id = uuidv4().split('-')[0];
    const channel = { id, name: name||'untitled', limit: limit||10, createdAt: Date.now() };
    db.data.channels.push(channel);
    await db.write();
    res.json({ channelId: id, channelLink: `local://join/${id}` });
  });

  serverApp.get('/api/channels', async (req, res) => {
    await db.read();
    res.json(db.data.channels);
  });

  // Socket.IO for realtime notes
  io.on('connection', socket => {
    socket.on('joinChannel', async ({ channelId, userId }) => {
      await db.read();
      const ch = db.data.channels.find(c=>c.id===channelId);
      if(!ch) return socket.emit('error','not found');
      socket.join(channelId);
      const notes = db.data.notes.filter(n=>n.channelId===channelId && (!n.expiresAt || n.expiresAt>Date.now()));
      socket.emit('notesList', notes);
    });

    socket.on('saveNote', async ({ channelId, content, type, ttlSeconds, author }) => {
      const id = Date.now().toString() + Math.random().toString(36).slice(2,6);
      const expiresAt = ttlSeconds ? Date.now() + ttlSeconds*1000 : null;
      const note = { id, channelId, content, type: type||'memo', author: author||null, createdAt: Date.now(), expiresAt };
      db.data.notes.push(note);
      await db.write();
      io.to(channelId).emit('noteAdded', note);
    });

    socket.on('deleteNote', async ({ channelId, noteId }) => {
      db.data.notes = db.data.notes.filter(n=>n.id!==noteId);
      await db.write();
      io.to(channelId).emit('noteDeleted', noteId);
    });
  });

  // periodic cleanup
  setInterval(async ()=>{
    await db.read();
    const before = db.data.notes.length;
    db.data.notes = db.data.notes.filter(n=>!n.expiresAt || n.expiresAt>Date.now());
    if (db.data.notes.length!==before) {
      await db.write();
    }
  }, 10000);

  server.listen(3200, () => console.log('Local server listening on 3200'));
  // Note: also start a local-to-server bridge if a remote server URL is configured by user.
}

function createWindow(){
  const w = new BrowserWindow({
    width: 1000,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });
  w.loadFile(path.join(__dirname, 'renderer', 'index.html'));
}

app.whenReady().then(async ()=>{
  await startServer();
  createWindow();
});

app.on('window-all-closed', ()=>{
  if (process.platform !== 'darwin') app.quit();
});
