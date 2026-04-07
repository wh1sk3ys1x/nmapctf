#!/usr/bin/env bash
set -euo pipefail

COMPOSE="docker compose"
HEALTH_URL="http://localhost:8080/api/v1/health"
MAX_WAIT=30

echo "=== nmapctf deploy ==="

# Pull latest code
echo "[1/6] Pulling latest code..."
git pull

# Build images
echo "[2/6] Building images..."
$COMPOSE build --quiet

# Bring up the stack
echo "[3/6] Starting containers..."
$COMPOSE up -d

# Wait for health endpoint
echo "[4/6] Waiting for web service..."
elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
  if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
    break
  fi
  sleep 1
  elapsed=$((elapsed + 1))
done

# Backfill AssetAddress rows for existing assets
echo "[5/6] Running address backfill..."
$COMPOSE exec web python -m app.backfill_addresses

# Check result
echo "[6/6] Verifying..."
if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
  echo ""
  echo "  nmapctf is running at http://localhost:8080"
  echo ""
  $COMPOSE ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
else
  echo ""
  echo "  ERROR: health check failed after ${MAX_WAIT}s"
  echo "  Logs:"
  $COMPOSE logs web --tail 20
  exit 1
fi
