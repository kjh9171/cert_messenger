const express = require('express');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');
const http = require('http');
const { Server } = require('socket.io');
const jwt = require('jsonwebtoken');
const { pool, redis } = require('./db');

const app = express();
app.use(cors());
app.use(express.json());

const server = http.createServer(app);
const io = new Server(server, { cors: { origin: '*' } });

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-change-me';

async function createChannelRow(id, name, ownerId, max_participants, link) {
  await pool.query(
    'INSERT INTO channels(id, name, owner_id, link, max_participants) VALUES($1,$2,$3,$4,$5)',
    [id, name, ownerId, link, max_participants]
  );
}

app.post('/api/channels', async (req, res) => {
  try {
    const auth = req.headers.authorization && req.headers.authorization.split(' ')[1];
    let userId = null;
    if (auth) {
      const payload = jwt.verify(auth, JWT_SECRET);
      userId = payload.sub;
    }
    const { name, limit } = req.body;
    const channelId = uuidv4().split('-')[0];
    const link = `${req.protocol}://${req.get('host')}/join/${channelId}`;
    await createChannelRow(channelId, name || 'untitled', userId, limit || 10, link);
    res.json({ channelId, channelLink: link });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'server error' });
  }
});

app.get('/api/channels/:id', async (req, res) => {
  const id = req.params.id;
  const r = await pool.query('SELECT id,name,owner_id,max_participants,created_at,link FROM channels WHERE id=$1', [id]);
  if (!r.rowCount) return res.status(404).json({ error: 'not found' });
  const row = r.rows[0];
  const members = await pool.query('SELECT user_id FROM channel_members WHERE channel_id=$1', [id]);
  res.json({ id: row.id, name: row.name, limit: row.max_participants, members: members.rowCount, createdAt: row.created_at, link: row.link });
});

// Register contact (phone/email) - send code (mocked)
app.post('/api/register', async (req, res) => {
  const { contact, type } = req.body; // type: 'phone' | 'email'
  if (!contact || !type) return res.status(400).json({ error: 'missing' });
  const code = (Math.floor(Math.random() * 900000) + 100000).toString();
  await redis.set(`verify:${type}:${contact}`, code, 'EX', 300);
  // In production, send SMS or email. Here we return code (for demo).
  res.json({ message: 'code_sent', code });
});

// Verify code and issue JWT
app.post('/api/verify', async (req, res) => {
  const { contact, type, code } = req.body;
  if (!contact || !type || !code) return res.status(400).json({ error: 'missing' });
  const key = `verify:${type}:${contact}`;
  const stored = await redis.get(key);
  if (!stored || stored !== code) return res.status(400).json({ error: 'invalid' });
  await redis.del(key);
  // create or find user
  const userId = uuidv4().split('-')[0];
  const up = await pool.query('SELECT id FROM users WHERE contact=$1', [contact]);
  let id;
  if (up.rowCount) {
    id = up.rows[0].id;
  } else {
    id = userId;
    await pool.query('INSERT INTO users(id, contact, contact_type) VALUES($1,$2,$3)', [id, contact, type]);
  }
  const token = jwt.sign({ sub: id, contact }, JWT_SECRET, { expiresIn: '30d' });
  res.json({ token, userId: id });
});

// Register public key for E2E
app.post('/api/keys', async (req, res) => {
  const auth = req.headers.authorization && req.headers.authorization.split(' ')[1];
  if (!auth) return res.status(401).json({ error: 'unauth' });
  const payload = jwt.verify(auth, JWT_SECRET);
  const userId = payload.sub;
  const { publicKey } = req.body;
  if (!publicKey) return res.status(400).json({ error: 'no key' });
  await pool.query('UPDATE users SET public_key=$1 WHERE id=$2', [publicKey, userId]);
  res.json({ ok: true });
});

app.get('/api/channels/:id/public-keys', async (req, res) => {
  const id = req.params.id;
  const members = await pool.query('SELECT u.id,u.public_key FROM channel_members m JOIN users u ON m.user_id=u.id WHERE m.channel_id=$1', [id]);
  res.json(members.rows.filter(r => r.public_key));
});

// Periodic cleaner for expired notes stored in DB
async function cleanExpiredNotesDb() {
  const now = Date.now();
  const r = await pool.query('DELETE FROM notes WHERE expires_at IS NOT NULL AND expires_at <= $1 RETURNING id,channel_id', [now]);
  for (const row of r.rows) {
    io.to(row.channel_id).emit('noteDeleted', row.id);
  }
}

setInterval(() => { cleanExpiredNotesDb().catch(console.error); }, 10000);

io.on('connection', socket => {
  socket.on('joinChannel', async ({ channelId, userId }) => {
    const ch = await pool.query('SELECT id,max_participants FROM channels WHERE id=$1', [channelId]);
    if (!ch.rowCount) return socket.emit('error', '채널을 찾을 수 없습니다.');
    const max = ch.rows[0].max_participants || 10;
    const members = await pool.query('SELECT user_id FROM channel_members WHERE channel_id=$1', [channelId]);
    if (members.rowCount >= max && !members.rows.some(m=>m.user_id===userId)) {
      return socket.emit('roomFull', { message: '인원이 초과되었습니다.' });
    }
    socket.join(channelId);
    if (userId) {
      const exists = await pool.query('SELECT 1 FROM channel_members WHERE channel_id=$1 AND user_id=$2', [channelId, userId]);
      if (!exists.rowCount) await pool.query('INSERT INTO channel_members(channel_id,user_id) VALUES($1,$2)', [channelId, userId]);
    }
    const notes = await pool.query('SELECT id,content,type,author_id,created_at,expires_at FROM notes WHERE channel_id=$1', [channelId]);
    io.to(channelId).emit('updateMembers', (await pool.query('SELECT user_id FROM channel_members WHERE channel_id=$1', [channelId])).rows.map(r=>r.user_id));
    socket.emit('notesList', notes.rows.map(n => ({ id: n.id, content: n.content, type: n.type, author: n.author_id, createdAt: n.created_at, expiresAt: n.expires_at })));
  });

  socket.on('saveNote', async ({ channelId, content, type, ttlSeconds, author }) => {
    const id = Date.now().toString() + Math.random().toString(36).slice(2,6);
    const expiresAt = ttlSeconds ? Date.now() + ttlSeconds * 1000 : null;
    await pool.query('INSERT INTO notes(id,channel_id,author_id,content,type,expires_at) VALUES($1,$2,$3,$4,$5,$6)', [id, channelId, author || null, content, type || 'memo', expiresAt]);
    const note = { id, content, type: type || 'memo', author, createdAt: Date.now(), expiresAt };
    io.to(channelId).emit('noteAdded', note);
  });

  socket.on('deleteNote', async ({ channelId, noteId }) => {
    await pool.query('DELETE FROM notes WHERE id=$1', [noteId]);
    io.to(channelId).emit('noteDeleted', noteId);
  });
});

const PORT = process.env.PORT || 3100;
server.listen(PORT, () => console.log(`Backend listening on ${PORT}`));
