# 🚂 DEPLOY-RAILWAY — TESTÉ & PROPRE · Content OS

Objectif : **URL publique stable**, indépendante du sandbox Arena/E2B. Architecture inchangée, 3 vidéos + 3 voix de production préservées.

> ## 🚨 ERREUR « Railpack failed to prepare the build » avec `./ └── workspace-XXXX.zip` — CAUSE ET CORRECTIF
> **Diagnostic prouvé (30/09/2026)** : le service Railway construit la branche **`main`**, qui ne contient
> historiquement qu'**un seul fichier** (l'upload `workspace-*.zip`). Railpack ne voit donc **ni Dockerfile,
> ni requirements.txt, ni railway.toml** → échec immédiat à l'étape *prepare*, avant tout build.
> Le projet complet, lui, est sur **`arena/01a0efa9-tested`** (racine : `Dockerfile`, `railway.toml`,
> `requirements.txt`, `server/`, `teste-et-propre/index.html`…).
> **CORRECTIF — UN SEUL CLIC** dans Railway : **Service → Settings → Source → Branch → `arena/01a0efa9-tested`** → **Deploy**.
> Dès ce moment, Railpack lit `Dockerfile` à la racine et build sans erreur *prepare*.
> (Preuve locale : `git ls-tree origin/main --name-only` → 1 zip seul ; `git ls-tree origin/arena/01a0efa9-tested` → projet complet.)

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
3. Dans le service : **Settings → Source → Branch = `arena/01a0efa9-tested`** — **ÉTAPE CRITIQUE** :
   la branche par défaut `main` ne contient qu'un zip (cause exacte de l'erreur
   « Railpack failed to prepare the build »). Railway détecte ensuite Dockerfile + railway.toml tout seul.
4. **Volumes → New Volume** : Mount Path = **`/data`**, puis **Variables** :
   | Variable | Valeur | Pourquoi |
   |---|---|---|
   | `TNP_DATA_DIR` | `/data` | persistance (déjà dans l'image, le var le rend explicite) |
   | `GEMINI_API_KEY` | *ta clé* | TEXT/RESEARCH/IMAGE cloud (optionnels mais recommandés) |
   | `GROQ_API_KEY` | *ta clé* | TEXT alternatif (fallback chaîne Gemini→Groq→Mistral) |
   | `MISTRAL_API_KEY` | *ta clé* | TEXT alternatif |
   | `OPENROUTER_API_KEY` | *ta clé* | TEXT alternatif (dernier recours cloud) |
   | `ELEVENLABS_API_KEY` | *ta clé* | VOIX chaîne 1 (options ELEVENLABS_VOICE_ID/MODEL_ID) |
   | `AZURE_SPEECH_KEY` + `AZURE_SPEECH_REGION` | *clé + francecentral* | VOIX chaîne 2 (options AZURE_SPEECH_VOICE/RATE) |
   > Chaînes déclarées : TEXT gemini→groq→mistral→openrouter→local · VOICE elevenlabs→azure→import · IMAGE cloud→opérateur→composition. Tout fallback est visible (événements + metadata vidéo).
   > Statuts honnêtes garantis : tant qu'une variable manque, Studio → Providers affiche **NOT CONFIGURED** (aucun READY sans appel réel — le bouton *TEST CONNECTION* tire un vrai appel minimal : TTS 5 caractères / 1 réponse lite / 1 image jetable). Aucune variable CI/CD ne recevra JAMAIS de clé ; Railway Variables chiffrées seulement.
   > `/api/status` expose `commit` (RAILWAY_GIT_COMMIT_SHA, injecté par Railway au build) pour vérifier que le déploiement courant = dernier push.
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

<!-- deploy trigger 2026-09-30T18:58:27Z : cette ligne force un commit pour déclencher le build Railway si la branche source a été rectifiée (arena/01a0efa9-tested). -->
