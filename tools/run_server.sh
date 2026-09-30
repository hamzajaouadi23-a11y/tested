#!/usr/bin/env bash
# Lance le backend production (Studio + API + app V2) sur 0.0.0.0:8090
cd "$(dirname "$0")/.."
PY="${VENV:-/home/user/venv-tnp}/bin/python"
[ -x "$PY" ] || bash tools/setup_env.sh
exec "$PY" -m server.app
