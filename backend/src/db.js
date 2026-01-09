const { Pool } = require('pg');
const Redis = require('ioredis');

const pool = new Pool({
  connectionString: process.env.POSTGRES_URL || 'postgres://postgres:password@db:5432/cert_messenger'
});

const redis = new Redis(process.env.REDIS_URL || 'redis://redis:6379');

module.exports = { pool, redis };
