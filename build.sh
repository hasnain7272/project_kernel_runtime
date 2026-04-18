#!/bin/bash
# Antigravity Runtime — Build Script
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VITE_DIR="$SCRIPT_DIR/ui/vite-app"

echo "[1/2] Building Vite React Dashboard..."
cd "$VITE_DIR"
npm run build

echo "[2/2] Build complete!"
echo "  Local dev:  cd $VITE_DIR && npm run dev"
echo "  Backend:    cd $SCRIPT_DIR && python -m uvicorn src.api.fastapi_gateway:app --port 8089 --reload"
echo "  Production: cd $SCRIPT_DIR && docker compose up -d"
