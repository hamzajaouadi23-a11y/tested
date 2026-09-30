# 🚂 DEPLOY-RAILWAY — TESTÉ & PROPRE · Content OS

Objectif : **URL publique stable**, indépendante du sandbox Arena/E2B. Architecture inchangée, 3 vidéos + 3 voix de production préservées.

## Ce qui est déjà prêt dans le repo (rien à coder)
- `Dockerfile` (python:3.11-slim, ffmpeg via imageio-ffmpeg, healthcheck intégré, start unique `python -m server.app`)
- `requirements.txt` (versions épinglées = celles validées en prod)
- `railway.toml` (builder DOCKERFILE, healthcheck `/health`, restart ON_FAILURE ×3)
- `.dockerignore` (jamais `.env`, db runtime, backups — mais seeds inclus)
- `server/app.py` : port = `TNP_PORT` → `PORT` (fourni par Railway) → 8090 ; route **`/health`** légère
- `server/config.py` : **`TNP_DATA_DIR`** — volume Railway `/data` ; au 1er démarrage les seeds du repo (vidéos finales, voix, recherche) y sont **copiés, jamais écrasés** (idempotent)

## ⏱️ LA SEULE ACTION MANUELLE RESTANTE (10 minutes, zéro code)
1. https://railway.app → **Login with GitHub** (compte `hamzajaouadi23-a11y`).
2. **New Project → Deploy from GitHub repo** → sélectionner `hamzajaouadi23-a11y/tested`.
3. Dans le service : **Settings → Source → Branch = `arena/01a0efa9-tested`** (Railway détecte Dockerfile + railway.toml tout seul).
4. **Volumes → New Volume** : Mount Path = **`/data`**, puis **Variables** :
   | Variable | Valeur | Pourquoi |
   |---|---|---|
   | `TNP_DATA_DIR` | `/data` | persistance (déjà dans l'image, le var le rend explicite) |
   | *(optionnel)* `GEMINI_API_KEY` etc. | *tes clés* | providers réels — **jamais** dans Git |
   > **Ne jamais** mettre `PORT` ni `TNP_PORT` — Railway injecte `PORT` automatiquement.
5. **Deploy** → attendre le build (~3-5 min).
6. **Settings → Networking → Generate Domain** → URL `https://xxxx.up.railway.app` = production stable.

## ✅ Vérification après déploiement (copier-coller, remplacer l'URL)
```
curl -i https://xxxx.up.railway.app/health     # {"ok":true,...}
curl -sI https://xxxx.up.railway.app/ | head -1        # 200 (Studio)
curl -sI https://xxxx.up.railway.app/app | head -1     # 200 (App V2)
curl -s  https://xxxx.up.railway.app/api/pipeline/board | head -c 100
curl -sI https://xxxx.up.railway.app/media/ready_to_post/video_01.mp4 | head -1   # 200 (média réel)
```

## 🔁 AUTO-DEPLOY (PHASE 10)
C'est **natif Railway** dès que le projet vient de GitHub : **chaque push sur la branche surveillée → nouveau déploiement automatique**. Aucun fichier supplémentaire requis. (Settings → Service → méthode : GitHub. La branche se change dans le même écran si tu bascules un jour sur `main`.)

Chaîne de publication complète :
```
WORK → TEST (precheck) → SECRET SCAN → COMMIT → PUSH → VERIFY SHA (ls-remote) → RAILWAY DEPLOY AUTO → HTTP CHECK (/health)
```

## Persistance — ce qui se passe réellement
- Premier démarrage : volume `/data` vide → seed-copie des contenus de prod du repo (24 fichiers ≈ 47 Mo) → `data/db` créé frais.
- Redeploys suivants : le volume est conservé → **rien n'est perdu**, la copie seed est no-op.
- Aucune migration DB complexe : SQLite dans `/data/db` (WAL) — comportement local inchangé par défaut.

## Vérifié en local avant ce commit (PHASE 6)
app 200 · /app 200 · /health 200 · API 200 · médias 200 · 3 vidéos + 3 voix présentes · 42/42 · 40/40 · secrets clean · (build Docker validé statiquement — pas de daemon dans le sandbox).
