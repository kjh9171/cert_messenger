#!/usr/bin/env bash
# Simple script to create multiple channels via POST /api/channels
API=${API:-http://localhost:3100}
TOKEN=${TOKEN:-}

if [ -z "$1" ]; then
  echo "Usage: $0 <number> [prefix]"
  exit 1
fi
NUM=$1
PREFIX=${2:-channel}

for i in $(seq 1 $NUM); do
  name="$PREFIX-$i"
  if [ -n "$TOKEN" ]; then
    curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"name":"'"$name"'"}' $API/api/channels | jq -r '.channelLink'
  else
    curl -s -X POST -H "Content-Type: application/json" -d '{"name":"'"$name"'"}' $API/api/channels | jq -r '.channelLink'
  fi
done
