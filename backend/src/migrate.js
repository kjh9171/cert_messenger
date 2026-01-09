const fs = require('fs');
const path = require('path');
const { pool } = require('./db');

function wait(ms){ return new Promise(res => setTimeout(res, ms)); }

async function waitForDb(retries = 12, delay = 2000) {
  for (let i = 0; i < retries; i++) {
    try {
      await pool.query('SELECT 1');
      return;
    } catch (e) {
      console.log(`Postgres not ready, retrying in ${delay}ms... (${i+1}/${retries})`);
      await wait(delay);
    }
  }
  throw new Error('Postgres did not become available');
}

async function runMigrations() {
  await waitForDb();
  const dir = path.join(__dirname, '..', 'migrations');
  const files = fs.readdirSync(dir).filter(f => f.endsWith('.sql')).sort();
  for (const f of files) {
    const sql = fs.readFileSync(path.join(dir, f), 'utf8');
    console.log('Running', f);
    await pool.query(sql);
  }
  console.log('Migrations complete');
}

runMigrations().then(() => process.exit(0)).catch(e => { console.error('Migration failed', e); process.exit(1); });
