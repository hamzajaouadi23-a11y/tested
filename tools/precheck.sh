#!/usr/bin/env bash
# Pré-vérification obligatoire avant commit/prod : secrets, tests V2, tests backend.
set -eo pipefail
# pipefail : un FAIL dans une suite pipée à tail fait ÉCHOUER le precheck (régression prod corrigée).
cd "$(dirname "$0")/.."
PY="${VENV:-/home/user/venv-tnp}/bin/python"
[ -x "$PY" ] || { echo "venv manquant → bash tools/setup_env.sh"; bash tools/setup_env.sh; }
echo "—— 1/4 Scan secrets ——"
"$PY" server/secrets_scan.py .
echo "—— 2/4 App V2 (harnais 42 tests) ——"
python3 -c "import re;open('/tmp/app_check.js','w').write(re.search(r'<script>([\s\S]*)</script>', open('teste-et-propre/index.html').read()).group(1))"
node --check /tmp/app_check.js
node tests/harness.js | tail -2
echo "—— 3/4 Backend (tests pipeline) ——"
"$PY" tests/test_server.py | tail -3
echo "—— 4/4 Imports modules backend ——"
"$PY" -c "import server.app, server.db, server.providers, server.services.qa, server.services.render, server.services.pipeline; print('imports OK')"
echo "✅ PRECHECK OK — commit autorisé"
