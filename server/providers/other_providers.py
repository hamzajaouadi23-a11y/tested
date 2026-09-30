"""Providers RESEARCH / IMAGE / VOICE / STORAGE / SOCIAL / ANALYTICS / SCHEDULER.

Principes :
- Jamais de fausse donnée : un provider qui ne peut pas produire du réel renvoie ok=False avec une
  raison claire, et le pipeline se marque BLOCKED (au lieu de fabriquer un mock silencieusement).
- Les providers "drop/inbox" sont RÉELS : ils importent des assets légitimes fournis par
  l'opérateur (priorité n°1 de la stratégie : assets fournis par l'utilisateur).
"""
import glob
import os
import time

from .base import Provider


# ---------------- RESEARCH ----------------
class GeminiGroundingResearch(Provider):
    id = "research_gemini"
    label = "Recherche via Gemini + Google Search grounding"
    kind = "RESEARCH"
    implemented = True
    mock = False
    requires = ["GEMINI_API_KEY"]
    costly = False


class ResearchImport(Provider):
    """Importe des recherches structurées (JSON) déposées dans data/research/inbox/.
    Format : {"topic": str, "sources": [{"url","title"}], "facts": [{"fact","analysis","angle","source_url"}]}
    Chaque fait doit référencer une URL de source. Sans source → fait rejeté (jamais de stats inventées)."""
    id = "research_import"
    label = "Import recherche (data/research/inbox)"
    kind = "RESEARCH"
    implemented = True
    mock = False
    requires = []
    costly = False

    def test(self):
        from .. import config
        files = glob.glob(os.path.join(config.RESEARCH_INBOX, "*.json"))
        return {"ok": True, "latency_ms": 1,
                "detail": "%d fichier(s) de recherche en attente d'import" % len(files)}


# ---------------- IMAGE ----------------
class GeminiImageProvider(Provider):
    """Génération d'images via l'API Gemini (Imagen / native image) — nécessite GEMINI_API_KEY."""
    id = "image_gemini"
    label = "Génération d'images Gemini"
    kind = "IMAGE"
    implemented = True
    mock = False
    requires = ["GEMINI_API_KEY"]
    costly = False

    def generate(self, prompt, out_path, w=1080, h=1920):
        from .. import config
        key = config.get_secret("GEMINI_API_KEY")
        if not key:
            return {"ok": False, "detail": "GEMINI_API_KEY manquante"}
        model = "gemini-2.5-flash-image"
        body = {"contents": [{"parts": [{"text": "Generate a vertical 9:16 image: " + prompt}]}]}
        url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s" % (model, key)
        r = self.safe_http(url, payload=body, timeout=90, retries=2)
        if not r["ok"]:
            return r
        try:
            import base64
            for part in r["json"]["candidates"][0]["content"]["parts"]:
                if part.get("inlineData", {}).get("data"):
                    with open(out_path, "wb") as f:
                        f.write(base64.b64decode(part["inlineData"]["data"]))
                    return {"ok": True, "path": out_path, "provenance": "ai"}
            return {"ok": False, "detail": "aucune image dans la réponse Gemini"}
        except Exception as e:
            return {"ok": False, "detail": str(e)[:200]}

    def test(self):
        return super().test()


class ImageImport(Provider):
    """Assets déposés par l'opérateur dans data/media/inbox/ (assets fournis = priorité 1)."""
    id = "image_import"
    label = "Import assets opérateur (data/media/inbox)"
    kind = "IMAGE"
    implemented = True
    mock = False
    requires = []
    costly = False

    def test(self):
        from .. import config
        files = [f for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.mp4") for f in glob.glob(os.path.join(config.MEDIA_INBOX, ext))]
        return {"ok": True, "latency_ms": 1, "detail": "%d asset(s) opérateur en inbox" % len(files)}


class CompositionProvider(Provider):
    """Compositions graphiques originales 1080x1920 via PIL (fonds, titres, encadrés, pastilles).
    100 % local, réel (provenance=composition)."""
    id = "composition"
    label = "Compositions graphiques (PIL, local)"
    kind = "IMAGE"
    implemented = True
    mock = False
    requires = []
    costly = False

    def test(self):
        try:
            import PIL  # noqa
            return {"ok": True, "detail": "Pillow disponible", "latency_ms": 1}
        except Exception:
            return {"ok": False, "detail": "Pillow manquant", "latency_ms": 1}


# ---------------- VOICE ----------------
class AzureVoice(Provider):
    id = "voice_azure"
    label = "Azure Speech (TTS)"
    kind = "VOICE"
    implemented = True
    mock = False
    requires = ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"]
    costly = False

    def synthesize(self, text, out_path, voicename="fr-FR-DeniseNeural", rate="+8%"):
        from .. import config
        key = config.get_secret("AZURE_SPEECH_KEY")
        region = config.get_secret("AZURE_SPEECH_REGION")
        if not key or not region:
            return {"ok": False, "detail": "Azure Speech non configuré"}
        import html
        ssml = ("<speak version='1.0' xml:lang='fr-FR'><voice xml:lang='fr-FR' name='%s'>"
                "<prosody rate='%s'>%s</prosody></voice></speak>") % (voicename, rate, html.escape(text))
        url = "https://%s.tts.speech.microsoft.com/cognitiveservices/v1" % region
        r = self.safe_http(url, payload=ssml.encode("utf-8"), raw=True, timeout=60, headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
            "User-Agent": "tnp-content-os"})
        if r["ok"] and r.get("raw") and len(r["raw"]) > 200:
            with open(out_path, "wb") as f:
                f.write(r["raw"])
            return {"ok": True, "path": out_path}
        return {"ok": False, "detail": r.get("detail", "synthèse échouée")}


class ElevenLabsVoice(Provider):
    id = "voice_elevenlabs"
    label = "ElevenLabs (TTS)"
    kind = "VOICE"
    implemented = True
    mock = False
    requires = ["ELEVENLABS_API_KEY"]
    costly = False

    def synthesize(self, text, out_path, voice_id="21m00Tcm4TlvDq8ikWAM"):
        from .. import config
        key = config.get_secret("ELEVENLABS_API_KEY")
        if not key:
            return {"ok": False, "detail": "ELEVENLABS_API_KEY manquante"}
        body = {"text": text, "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.7, "speed": 1.06}}
        r = self.safe_http("https://api.elevenlabs.io/v1/text-to-speech/" + voice_id, payload=body,
                           raw=True, timeout=90, headers={"xi-api-key": key, "Accept": "audio/mpeg"})
        if r["ok"] and r.get("raw") and len(r["raw"]) > 200:
            with open(out_path, "wb") as f:
                f.write(r["raw"])
            return {"ok": True, "path": out_path}
        return {"ok": False, "detail": r.get("detail", "synthèse échouée")}


class VoiceImport(Provider):
    """Voix off déposées par l'opérateur dans data/voice/inbox/ — RÉEL (voix fournies).
    Nom de fichier : script_<id>.mp3|wav|m4a — la durée réelle est mesurée via ffmpeg."""
    id = "voice_import"
    label = "Import voix opérateur (data/voice/inbox)"
    kind = "VOICE"
    implemented = True
    mock = False
    requires = []
    costly = False

    def find_for_script(self, script_id):
        from .. import config
        for ext in ("mp3", "wav", "m4a", "ogg", "opus", "aac"):
            p = os.path.join(config.VOICE_INBOX, "script_%d.%s" % (script_id, ext))
            if os.path.exists(p):
                return p
        return None

    def test(self):
        from .. import config
        files = [f for ext in ("*.mp3", "*.wav", "*.m4a", "*.ogg") for f in glob.glob(os.path.join(config.VOICE_INBOX, ext))]
        return {"ok": True, "latency_ms": 1, "detail": "%d voix en inbox" % len(files)}


# ---------------- STORAGE ----------------
class LocalStorage(Provider):
    id = "storage_local"
    label = "Stockage local (SQLite + fichiers)"
    kind = "STORAGE"
    implemented = True
    mock = False
    requires = []
    costly = False

    def test(self):
        from .. import config, db
        try:
            probe = os.path.join(config.TMP, ".probe")
            with open(probe, "w") as f:
                f.write("ok")
            ok = open(probe).read() == "ok"
            os.remove(probe)
            db.q("SELECT 1")
            return {"ok": ok, "detail": "fichiers + SQLite OK", "latency_ms": 2}
        except Exception as e:
            return {"ok": False, "detail": str(e)[:200], "latency_ms": 2}


# ---------------- SOCIAL (APIs officielles uniquement, OAuth jamais contourné) ----------------
class _SocialBase(Provider):
    kind = "SOCIAL"
    implemented = True
    mock = False
    costly = False
    docs = ""

    def publish(self, video_path, caption):
        return {"ok": False, "detail": "non connecté — OAuth requis. La publication reste manuelle."}

    def test(self):
        if not self.configured():
            return {"ok": False, "latency_ms": 0,
                    "detail": "non configuré (OAuth requis) — voir %s" % self.docs}
        return {"ok": True, "latency_ms": 0, "detail": "token présent — test d'envoi non exécuté (publication humaine uniquement)"}


class TikTokSocial(_SocialBase):
    id = "tiktok"
    label = "TikTok Content Posting API (officielle)"
    requires = ["TIKTOK_ACCESS_TOKEN"]
    docs = "developers.tiktok.com — Content Posting API"


class YouTubeSocial(_SocialBase):
    id = "youtube"
    label = "YouTube Data API v3 (officielle)"
    requires = ["YOUTUBE_ACCESS_TOKEN"]
    docs = "console.cloud.google.com — YouTube Data API"


class InstagramSocial(_SocialBase):
    id = "instagram"
    label = "Instagram Graph API (Meta, officielle)"
    requires = ["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_BUSINESS_ID"]
    docs = "developers.facebook.com — Instagram Content Publishing"


# ---------------- ANALYTICS ----------------
class LocalAnalytics(Provider):
    """Saisie/import des métriques réelles postées. AUTO_ANALYTICS=OFF : jamais de scraping,
    jamais de simulation d'engagement."""
    id = "analytics_local"
    label = "Analytics locaux (saisie réelle)"
    kind = "ANALYTICS"
    implemented = True
    mock = False
    requires = []
    costly = False

    def test(self):
        return {"ok": True, "latency_ms": 1, "detail": "saisie manuelle/import JSON — aucune simulation"}


# ---------------- SCHEDULER ----------------
class LocalScheduler(Provider):
    """Planification rappel humain : marque les vidéos 'à publier' à l'heure prévue.
    Ne publie JAMAIS automatiquement (AUTO_PUBLISH=OFF, non contournable)."""
    id = "scheduler_local"
    label = "Planificateur local (rappels)"
    kind = "SCHEDULER"
    implemented = True
    mock = False
    requires = []
    costly = False

    def due(self):
        from .. import db
        rows = db.q("SELECT * FROM schedule WHERE state='planned' AND planned_at <= ?", (db.now(),))
        for r in rows:
            db.run("UPDATE schedule SET state='due_reminder' WHERE id=?", (r["id"],))
        return rows

    def test(self):
        return {"ok": True, "latency_ms": 1, "detail": "rappels locaux — aucune publication auto"}
