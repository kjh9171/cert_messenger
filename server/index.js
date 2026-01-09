const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const path = require('path');
const { Low } = require('lowdb');
const { JSONFile } = require('lowdb/node');
const { v4: uuidv4 } = require('uuid');

const app = express();
app.use(express.json());

const dbFile = path.join(__dirname, 'db.json');
const adapter = new JSONFile(dbFile);
const db = new Low(adapter);

async function initDb(){
  await db.read();
  db.data = db.data || { channels: [], notes: [], channel_members: [] };
  await db.write();
}

initDb().catch(err=>{ console.error('DB init error', err); process.exit(1); });

const server = http.createServer(app);
const io = new Server(server, { cors: { origin: '*' } });

app.get('/health', (req,res)=>res.json({ ok:true }));

app.post('/api/channels', async (req,res)=>{
  await db.read();
  const { name, limit } = req.body;
  const id = uuidv4().split('-')[0];
  const ch = { id, name: name||'untitled', limit: limit||10, createdAt: Date.now() };
  db.data.channels.push(ch);
  await db.write();
  res.json({ channelId: id, channelLink: `/join/${id}` });
});

// Server (admin) broadcast to channel
app.post('/api/channels/:id/broadcast', async (req,res)=>{
  const channelId = req.params.id;
  const { content, type } = req.body;
  const note = { id: Date.now().toString()+Math.random().toString(36).slice(2,6), channelId, content, type: type||'system', author: 'server', createdAt: Date.now(), expiresAt: null, persistent: true };
  await db.read();
  db.data.notes.push(note);
  await db.write();
  io.to(channelId).emit('noteAdded', note);
  res.json({ ok: true });
});

app.get('/api/channels', async (req,res)=>{
  await db.read(); res.json(db.data.channels);
});

io.on('connection', socket=>{
  socket.on('joinChannel', async ({ channelId, userId })=>{
    await db.read();
    const ch = db.data.channels.find(c=>c.id===channelId);
    if(!ch) return socket.emit('error','not found');
    socket.join(channelId);
    // add membership
    const exists = db.data.channel_members.find(m=>m.channelId===channelId && m.userId===userId);
    if(!exists) {
      db.data.channel_members.push({ channelId, userId, joinedAt: Date.now() });
      await db.write();
    }
    const notes = db.data.notes.filter(n=>n.channelId===channelId && (!n.expiresAt || n.expiresAt>Date.now()));
    socket.emit('notesList', notes);
    // notify updated members
    const members = db.data.channel_members.filter(m=>m.channelId===channelId).map(m=>m.userId);
    io.to(channelId).emit('updateMembers', members);
  });

  socket.on('saveNote', async ({ channelId, content, type, ttlSeconds, author, persistent })=>{
    const id = Date.now().toString() + Math.random().toString(36).slice(2,6);
    const expiresAt = ttlSeconds ? Date.now() + ttlSeconds*1000 : null;
    // default persistent false when not provided
    const note = { id, channelId, content, type: type||'memo', author: author||null, createdAt: Date.now(), expiresAt, persistent: !!persistent };
    await db.read();
    db.data.notes.push(note);
    await db.write();
    io.to(channelId).emit('noteAdded', note);
  });

  socket.on('deleteNote', async ({ channelId, noteId })=>{
    await db.read();
    db.data.notes = db.data.notes.filter(n=>n.id!==noteId);
    await db.write();
    io.to(channelId).emit('noteDeleted', noteId);
  });

  socket.on('leaveChannel', async ({ channelId, userId }) => {
    await db.read();
    db.data.channel_members = db.data.channel_members.filter(m=>!(m.channelId===channelId && m.userId===userId));
    // Delete ephemeral notes authored by this user in this channel
    db.data.notes = db.data.notes.filter(n => {
      if (n.channelId !== channelId) return true;
      if (n.persistent) return true;
      if (n.author && n.author === userId) return false; // remove ephemeral authored by leaving user
      return true;
    });
    await db.write();
    // If channel has no members left, remove all non-persistent notes (clean up channel)
    const membersLeft = db.data.channel_members.filter(m=>m.channelId===channelId);
    if (membersLeft.length === 0) {
      db.data.notes = db.data.notes.filter(n => !(n.channelId===channelId && !n.persistent));
      await db.write();
    }
    io.to(channelId).emit('updateMembers', db.data.channel_members.filter(m=>m.channelId===channelId).map(m=>m.userId));
    const notes = db.data.notes.filter(n=>n.channelId===channelId && (!n.expiresAt || n.expiresAt>Date.now()));
    io.to(channelId).emit('notesList', notes);
  });
});

const PORT = process.env.PORT || 4000;
server.listen(PORT, ()=>console.log('Server listening on', PORT));
