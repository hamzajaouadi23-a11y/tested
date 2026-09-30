# 🤝 PROJECT_HANDOFF — TESTÉ & PROPRE · Content OS (2026-09-30)

## État en une ligne
Application stable, 3 vidéos réelles QA-pass préservées, tests 42/42 (app) + 40/40 (backend), tout est sur GitHub (SHA vérifié), preview live Arena en cours.

## Où est la vérité
- **GitHub** `hamzajaouadi23-a11y/tested` — branche session `arena/01a0efa9-tested` @ `516816be`.
- Tags : `stable-live-2026-09-30` (plus récent), `checkpoint-session-start`, `recovery-current-work`, `RECOVERED-LIVE-V1`, `stable-2026-09-30`, `v5.2-real-media`, `v5.3-production-pipeline`.

## Contenu production (préservé, jamais regénéré)
- `data/media/ready_to_post/video_0{1,2,3}.mp4` + `_caption.txt` + `_metadata.json` (claims sourcés, disclosure IA).
- `data/voice/inbox/script_{1,2,3}.mp3` (voix off réelles — restaurées après incident tests, maintenant protégées par herméticité des tests).
- `data/research/processed/20260930-105258-nightshift_2026-09-30.json` (10 faits SOURCÉS).

## Architecture (ne pas réécrire)
- `server/app.py` : serveur stdlib 0.0.0.0:8090 → Studio `/`, App V2 `/app`, API `/api/*`, médias `/media/*`. SIGTERM propre. `TNP_HOST/TNP_PORT` env. Aucun secret renvoyé.
- `server/services/` : research → selection → scripts → assets → voice → render → qa (+ finalize ready_to_post) ; `pipeline` (states), `learning` (INSUFFICIENT tant que <5 mesures), `honesty` (lint anti-fakes).
- `teste-et-propre/index.html` : app V2 single-file, offline, localStorage `tnp_`, [data-action]→ACTIONS, backend optionnel.
- `tools/` : `run_server.sh` (auto-recrée le venv), `setup_env.sh`, `precheck.sh` (secrets+42+40+imports), nightshift_*.py (rebuild/polish/produce idempotents).
- `tests/test_server.py` : 40 tests dont e2e réelle ; **HERMÉTIQUE** (chemins prod jamais touchés).

## Règles inviolables
AUTO_PUBLISH=OFF · jamais de secret dans le repo/frontend/backups · jamais de fausses preuves/stats/témoignages · disclosure IA dans chaque caption · backups jamais écrasés · après chaque étape : test → scan secrets → commit → push → vérif SHA.

## Créances utilisateur
Voir `QUESTIONS-FOR-USER.md` (clés providers, publication, branche, lien pérenne, saisie métriques).
