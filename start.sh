#!/bin/bash
# Start the NCAA Bracket Predictor
# Usage: ./start.sh [--prod]
#
# Dev mode (default): FastAPI on :8000, React dev server on :5173
# Prod mode (--prod):  Build React, serve everything from FastAPI on :8000

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv/bin"

if [[ "$1" == "--prod" ]]; then
  echo "Building frontend for production..."
  cd "$ROOT/web/frontend" && npm run build
  echo ""
  echo "Starting server at http://localhost:8000"
  cd "$ROOT" && "$VENV/python" -m uvicorn web.backend.app:app --host 0.0.0.0 --port 8000
else
  # Kill anything already on ports 8000 / 5173
  lsof -ti:8000 | xargs kill -9 2>/dev/null; true
  lsof -ti:5173 | xargs kill -9 2>/dev/null; true
  echo "Starting API server on :8000 ..."
  cd "$ROOT" && "$VENV/python" -m uvicorn web.backend.app:app --host 0.0.0.0 --port 8000 --reload &
  API_PID=$!

  echo "Starting React dev server on :5173 ..."
  cd "$ROOT/web/frontend" && npm run dev &
  VITE_PID=$!

  echo ""
  echo "✓ API:      http://localhost:8000/api/bracket"
  echo "✓ App:      http://localhost:5173"
  echo ""
  echo "Press Ctrl+C to stop both servers."
  trap "kill $API_PID $VITE_PID 2>/dev/null" EXIT
  wait
fi
