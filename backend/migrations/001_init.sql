-- users table
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  contact TEXT,
  contact_type TEXT,
  created_at TIMESTAMP DEFAULT now(),
  public_key TEXT
);

-- channels
CREATE TABLE IF NOT EXISTS channels (
  id TEXT PRIMARY KEY,
  name TEXT,
  owner_id TEXT,
  link TEXT,
  max_participants INTEGER DEFAULT 10,
  created_at TIMESTAMP DEFAULT now()
);

-- channel members
CREATE TABLE IF NOT EXISTS channel_members (
  id SERIAL PRIMARY KEY,
  channel_id TEXT REFERENCES channels(id) ON DELETE CASCADE,
  user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
  joined_at TIMESTAMP DEFAULT now()
);

-- notes
CREATE TABLE IF NOT EXISTS notes (
  id TEXT PRIMARY KEY,
  channel_id TEXT REFERENCES channels(id) ON DELETE CASCADE,
  author_id TEXT,
  content TEXT,
  type TEXT,
  created_at TIMESTAMP DEFAULT now(),
  expires_at BIGINT
);
