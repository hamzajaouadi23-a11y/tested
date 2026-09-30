"""Providers TEXT — chaîne de repli : Gemini → Groq → Mistral → OpenRouter → local (toujours disponible).

Gemini : gemini-2.5-flash (recherche, analyse produit, sélection, scripts, raisonnement)
         gemini-2.5-flash-lite (hooks, captions, hashtags, classification, transformations)
         + grounding Google Search quand disponible.
"""
from .base import Provider


class GeminiProvider(Provider):
    id = "gemini"
    label = "Google Gemini (2.5 Flash / Flash-Lite)"
    kind = "TEXT"
    implemented = True
    mock = False
    requires = ["GEMINI_API_KEY"]
    costly = False

    MODEL_FLASH = "gemini-2.5-flash"
    MODEL_LITE = "gemini-2.5-flash-lite"

    def generate(self, prompt, model=None, grounding=False, temperature=0.7):
        from .. import config
        key = config.get_secret("GEMINI_API_KEY")
        if not key:
            return {"ok": False, "detail": "GEMINI_API_KEY manquante"}
        model = model or self.MODEL_FLASH
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature, "maxOutputTokens": 4096}}
        if grounding:
            body["tools"] = [{"google_search": {}}]
        url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s" % (model, key)
        r = self.safe_http(url, payload=body, timeout=45)
        if not r["ok"]:
            return r
        try:
            parts = r["json"]["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts)
            meta = {}
            gm = r["json"]["candidates"][0].get("groundingMetadata")
            if gm:
                meta["grounding"] = [
                    {"url": c.get("web", {}).get("uri", ""), "title": c.get("web", {}).get("title", "")}
                    for c in gm.get("groundingChunks", [])]
            return {"ok": True, "text": text, "model": model, "citations": meta.get("grounding", [])}
        except Exception as e:
            return {"ok": False, "detail": "réponse Gemini inattendue: %s" % e}

    def test(self):
        base = super().test()
        if not base["ok"]:
            return base
        r = self.generate("Réponds uniquement : OK", model=self.MODEL_LITE, temperature=0)
        return {"ok": r["ok"], "detail": "gemini-2.5-flash-lite répond" if r["ok"] else r.get("detail", "échec"),
                "latency_ms": r.get("latency_ms", 0)}


class GroqProvider(Provider):
    id = "groq"
    label = "Groq (Llama + Whisper)"
    kind = "TEXT"
    implemented = True
    mock = False
    requires = ["GROQ_API_KEY"]
    costly = False

    MODEL = "llama-3.3-70b-versatile"

    def generate(self, prompt, temperature=0.6):
        from .. import config
        key = config.get_secret("GROQ_API_KEY")
        if not key:
            return {"ok": False, "detail": "GROQ_API_KEY manquante"}
        body = {"model": self.MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": temperature}
        r = self.safe_http("https://api.groq.com/openai/v1/chat/completions", payload=body,
                           headers={"Authorization": "Bearer " + key}, timeout=40)
        if not r["ok"]:
            return r
        try:
            return {"ok": True, "text": r["json"]["choices"][0]["message"]["content"], "model": self.MODEL}
        except Exception as e:
            return {"ok": False, "detail": "réponse Groq inattendue: %s" % e}

    def transcribe(self, audio_path):
        """Transcription Whisper (multipart)."""
        from .. import config
        key = config.get_secret("GROQ_API_KEY")
        if not key:
            return {"ok": False, "detail": "GROQ_API_KEY manquante"}
        boundary = "----tnpboundary"
        with open(audio_path, "rb") as f:
            audio = f.read()
        parts = []
        parts.append(("--" + boundary + '\r\nContent-Disposition: form-data; name="model"\r\n\r\nwhisper-large-v3-turbo\r\n').encode())
        parts.append(('--' + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="audio.mp3"\r\n'
                      'Content-Type: audio/mpeg\r\n\r\n').encode() + audio + b"\r\n")
        parts.append(("--" + boundary + "--\r\n").encode())
        body = b"".join(parts)
        r = self.safe_http("https://api.groq.com/openai/v1/audio/transcriptions", payload=body,
                           headers={"Authorization": "Bearer " + key,
                                    "Content-Type": "multipart/form-data; boundary=" + boundary}, timeout=90)
        if r["ok"]:
            try:
                r["text"] = r["json"].get("text", "")
            except Exception:
                pass
        return r

    def test(self):
        base = super().test()
        if not base["ok"]:
            return base
        r = self.generate("Réponds uniquement : OK", temperature=0)
        return {"ok": r["ok"], "detail": "%s répond" % self.MODEL if r["ok"] else r.get("detail", "échec"),
                "latency_ms": r.get("latency_ms", 0)}


class MistralProvider(Provider):
    id = "mistral"
    label = "Mistral (small)"
    kind = "TEXT"
    implemented = True
    mock = False
    requires = ["MISTRAL_API_KEY"]
    costly = False
    MODEL = "mistral-small-latest"

    def generate(self, prompt, temperature=0.6):
        from .. import config
        key = config.get_secret("MISTRAL_API_KEY")
        if not key:
            return {"ok": False, "detail": "MISTRAL_API_KEY manquante"}
        body = {"model": self.MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": temperature}
        r = self.safe_http("https://api.mistral.ai/v1/chat/completions", payload=body,
                           headers={"Authorization": "Bearer " + key}, timeout=40)
        if not r["ok"]:
            return r
        try:
            return {"ok": True, "text": r["json"]["choices"][0]["message"]["content"], "model": self.MODEL}
        except Exception as e:
            return {"ok": False, "detail": "réponse Mistral inattendue: %s" % e}

    def test(self):
        base = super().test()
        if not base["ok"]:
            return base
        r = self.generate("Réponds uniquement : OK", temperature=0)
        return {"ok": r["ok"], "detail": "%s répond" % self.MODEL if r["ok"] else r.get("detail", "échec"),
                "latency_ms": r.get("latency_ms", 0)}


class OpenRouterProvider(Provider):
    id = "openrouter"
    label = "OpenRouter (routage gratuit)"
    kind = "TEXT"
    implemented = True
    mock = False
    requires = ["OPENROUTER_API_KEY"]
    costly = False
    MODEL = "openrouter/auto"

    def generate(self, prompt, temperature=0.6):
        from .. import config
        key = config.get_secret("OPENROUTER_API_KEY")
        if not key:
            return {"ok": False, "detail": "OPENROUTER_API_KEY manquante"}
        body = {"model": self.MODEL, "models": ["meta-llama/llama-3.3-70b-instruct:free", "google/gemma-3-27b-it:free"],
                "messages": [{"role": "user", "content": prompt}], "temperature": temperature}
        r = self.safe_http("https://openrouter.ai/api/v1/chat/completions", payload=body,
                           headers={"Authorization": "Bearer " + key}, timeout=45)
        if not r["ok"]:
            return r
        try:
            return {"ok": True, "text": r["json"]["choices"][0]["message"]["content"], "model": r["json"].get("model", self.MODEL)}
        except Exception as e:
            return {"ok": False, "detail": "réponse OpenRouter inattendue: %s" % e}

    def test(self):
        base = super().test()
        if not base["ok"]:
            return base
        r = self.generate("Réponds uniquement : OK", temperature=0)
        return {"ok": r["ok"], "detail": "routage OK" if r["ok"] else r.get("detail", "échec"),
                "latency_ms": r.get("latency_ms", 0)}


class LocalTextProvider(Provider):
    """Secours local déterministe — génère du texte RÉEL (banques FR), hors ligne, sans clé.
    Jamais de faux chiffres ni de promesses. Indiqué quality=fallback (à remplacer dès qu'une clé existe)."""
    id = "local_text"
    label = "Local (secours hors ligne)"
    kind = "TEXT"
    implemented = True
    mock = False
    requires = []
    costly = False
    quality = "fallback"

    def generate(self, prompt, **kw):
        return {"ok": False, "detail": "le provider local ne répond pas aux prompts libres — passer par services.scripts"}

    def test(self):
        return {"ok": True, "detail": "moteur de templates FR opérationnel (hors ligne)", "latency_ms": 1}


TEXT_CHAIN = [GeminiProvider, GroqProvider, MistralProvider, OpenRouterProvider, LocalTextProvider]


def generate_text(prompt, purpose="script", lite=False):
    """Essaie la chaîne dans l'ordre. Retourne {ok, text, provider, model} ou {ok:False, tried:[...]}."""
    order = [GeminiProvider, GroqProvider, MistralProvider, OpenRouterProvider]
    tried = []
    for cls in order:
        p = cls()
        if not p.configured():
            continue
        kw = {}
        if isinstance(p, GeminiProvider):
            kw = {"model": GeminiProvider.MODEL_LITE if lite else GeminiProvider.MODEL_FLASH,
                  "grounding": purpose == "research"}
        r = p.generate(prompt, **kw)
        if r["ok"]:
            return {"ok": True, "text": r["text"], "provider": p.id, "model": r.get("model"),
                    "citations": r.get("citations", [])}
        tried.append({"provider": p.id, "detail": r.get("detail", "")[:200]})
    return {"ok": False, "tried": tried, "detail": "aucun provider cloud configuré/disponible"}
