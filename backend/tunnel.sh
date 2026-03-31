#!/usr/bin/env bash
set -uo pipefail
exec cloudflared tunnel --url http://localhost:8000 --metrics localhost:0 2>&1 | grep -E "Tunnel|error|registered"
