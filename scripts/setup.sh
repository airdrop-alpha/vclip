#!/usr/bin/env bash
set -euo pipefail

# ===========================================
# VClip — Local Development Setup
# ===========================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}ℹ ${NC} $*"; }
ok()    { echo -e "${GREEN}✅${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠️ ${NC} $*"; }
fail()  { echo -e "${RED}❌${NC} $*"; exit 1; }

echo ""
echo "🎬 VClip — Development Environment Setup"
echo "=========================================="
echo ""

# ---- Check dependencies ----
info "Checking dependencies..."

MISSING=0

check_cmd() {
    if command -v "$1" &>/dev/null; then
        ok "$1 found: $(command -v "$1")"
    else
        warn "$1 not found — $2"
        MISSING=1
    fi
}

check_cmd python3   "Install Python 3.12+: https://python.org"
check_cmd node      "Install Node.js 22+: https://nodejs.org"
check_cmd npm       "Comes with Node.js"
check_cmd ffmpeg    "Install: brew install ffmpeg / apt install ffmpeg"
check_cmd yt-dlp    "Install: pip install yt-dlp / brew install yt-dlp"

echo ""

if [ "$MISSING" -eq 1 ]; then
    fail "Missing dependencies above. Install them and re-run this script."
fi

# ---- Check versions ----
PYTHON_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
NODE_VER=$(node -v | sed 's/v//' | cut -d. -f1)

if (( $(echo "$PYTHON_VER < 3.10" | bc -l 2>/dev/null || echo 0) )); then
    warn "Python $PYTHON_VER detected. Python 3.10+ recommended."
fi
if [ "$NODE_VER" -lt 18 ] 2>/dev/null; then
    warn "Node $NODE_VER detected. Node 18+ recommended."
fi

# ---- Backend setup ----
info "Setting up backend..."

cd "$(dirname "$0")/.."
ROOT_DIR="$(pwd)"

cd backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
    ok "Virtual environment created"
else
    ok "Virtual environment already exists"
fi

source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
ok "Backend dependencies installed"

cd "$ROOT_DIR"

# ---- Frontend setup ----
info "Setting up frontend..."

cd frontend
npm install --silent 2>/dev/null || npm install
ok "Frontend dependencies installed"

cd "$ROOT_DIR"

# ---- Create directories ----
info "Creating directories..."

mkdir -p clips
mkdir -p backend/app/api
mkdir -p backend/app/core
mkdir -p backend/app/models
mkdir -p backend/app/schemas
mkdir -p backend/app/services
mkdir -p backend/tests
mkdir -p frontend/src/app
mkdir -p frontend/src/components
mkdir -p frontend/src/lib
mkdir -p docs

ok "Project directories created"

# ---- Environment file ----
if [ ! -f ".env" ]; then
    cp .env.example .env
    ok "Created .env from .env.example"
else
    ok ".env already exists"
fi

# ---- Done ----
echo ""
echo "=========================================="
echo -e "${GREEN}🎉 VClip setup complete!${NC}"
echo ""
echo "  Start developing:"
echo "    make dev          — Run backend + frontend"
echo "    make docker       — Run with Docker Compose"
echo ""
echo "  URLs:"
echo "    Frontend:  http://localhost:3000"
echo "    Backend:   http://localhost:8000"
echo "    API Docs:  http://localhost:8000/docs"
echo "=========================================="
