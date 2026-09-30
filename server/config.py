"""Configuration centrale — TESTÉ & PROPRE Content OS (backend pipeline).

Règles :
- Les secrets viennent UNIQUEMENT des variables d'environnement / .env (jamais commités).
- .env est lu ici (format KEY=VALUE), sans aucune dépendance externe.
- Aucune clé n'est jamais renvoyée par l'API (les routes ne renvoient que configured: bool).
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DB_DIR = os.path.join(DATA, "db")
DB_PATH = os.path.join(DB_DIR, "contentos.sqlite")
MEDIA = os.path.join(DATA, "media")
ASSETS = os.path.join(MEDIA, "assets")
READY = os.path.join(MEDIA, "ready_to_post")
DRAFTS = os.path.join(MEDIA, "drafts")
TMP = os.path.join(MEDIA, "tmp")
RESEARCH = os.path.join(DATA, "research")
RESEARCH_INBOX = os.path.join(RESEARCH, "inbox")
MEDIA_INBOX = os.path.join(MEDIA, "inbox")
VOICE_INBOX = os.path.join(DATA, "voice", "inbox")
ENV_PATH = os.path.join(ROOT, ".env")
ENV_EXAMPLE = os.path.join(ROOT, ".env.example")
VENV_PY = "/home/user/venv-tnp/bin/python"

for d in (DATA, DB_DIR, MEDIA, ASSETS, READY, DRAFTS, TMP, RESEARCH, RESEARCH_INBOX, MEDIA_INBOX, VOICE_INBOX):
    os.makedirs(d, exist_ok=True)


def load_env():
    """Charge .env dans os.environ (sans écraser les variables déjà définies)."""
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v


def save_env_key(key, value):
    """Écrit/remplace une clé dans .env (côté serveur uniquement, jamais renvoyée)."""
    load_env()
    lines, found = [], False
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(key + "="):
            lines[i] = key + "=" + value
            found = True
    if not found:
        lines.append(key + "=" + value)
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass
    os.environ[key] = value


def delete_env_key(key):
    load_env()
    if not os.path.exists(ENV_PATH):
        return
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        lines = [l for l in f.read().splitlines() if not l.strip().startswith(key + "=")]
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.environ.pop(key, None)


load_env()

# ---- Drapeaux d'automatisation (jamais AUTO_PUBLISH) ----
def flag(name, default):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")

AUTO_RESEARCH = flag("AUTO_RESEARCH", True)
AUTO_GENERATION = flag("AUTO_GENERATION", True)
AUTO_RENDER = flag("AUTO_RENDER", True)
AUTO_PUBLISH = flag("AUTO_PUBLISH", False)     # TOUJOURS OFF par défaut — publication humaine
AUTO_ANALYTICS = flag("AUTO_ANALYTICS", False)

# ---- Secrets serveur (lues ici, jamais exposées à l'API) ----
SECRET_KEYS = [
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "MISTRAL_API_KEY",
    "OPENROUTER_API_KEY",
    "AZURE_SPEECH_KEY",
    "AZURE_SPEECH_REGION",
    "ELEVENLABS_API_KEY",
    "TIKTOK_ACCESS_TOKEN",
    "TIKTOK_CLIENT_KEY",
    "YOUTUBE_ACCESS_TOKEN",
    "YOUTUBE_CLIENT_ID",
    "INSTAGRAM_ACCESS_TOKEN",
    "INSTAGRAM_BUSINESS_ID",
]

def get_secret(key):
    v = os.environ.get(key, "").strip()
    return v or None

def secret_configured(key):
    return get_secret(key) is not None

LANG = "fr-FR"
NICHE = "household"  # niche stratégique : produits/problèmes maison
