"""Registre des providers — point d'accès unique.

Toutes les catégories exigées : TEXT, RESEARCH, IMAGE, VOICE, VIDEO, STORAGE, SOCIAL, ANALYTICS, SCHEDULER.
Chaque provider expose : id, label, implemented, mock, requires, costly, test(), health(), gestion d'erreurs.
Aucun provider n'est codé en dur dans la logique métier : les services demandent au registre.
"""
from .base import Provider
from .text_providers import (GeminiProvider, GroqProvider, MistralProvider,
                             OpenRouterProvider, LocalTextProvider, generate_text, TEXT_CHAIN)
from .other_providers import (GeminiGroundingResearch, ResearchImport,
                              GeminiImageProvider, ImageImport, CompositionProvider,
                              AzureVoice, ElevenLabsVoice, VoiceImport,
                              LocalStorage, TikTokSocial, YouTubeSocial, InstagramSocial,
                              LocalAnalytics, LocalScheduler)


class VideoFFmpeg(Provider):
    id = "ffmpeg"
    label = "FFmpeg (rendu MP4 H.264 1080x1920)"
    kind = "VIDEO"
    implemented = True
    mock = False
    requires = []
    costly = False

    def test(self):
        try:
            from .. import ffmpegw
            return {"ok": True, "detail": ffmpegw.version(), "latency_ms": 5}
        except Exception as e:
            return {"ok": False, "detail": str(e)[:200], "latency_ms": 5}


_REGISTRY = [
    # TEXT (chaîne ordonnée : Gemini → Groq → Mistral → OpenRouter → local)
    GeminiProvider(), GroqProvider(), MistralProvider(), OpenRouterProvider(), LocalTextProvider(),
    # RESEARCH
    GeminiGroundingResearch(), ResearchImport(),
    # IMAGE
    ImageImport(), GeminiImageProvider(), CompositionProvider(),
    # VOICE
    AzureVoice(), ElevenLabsVoice(), VoiceImport(),
    # VIDEO
    VideoFFmpeg(),
    # STORAGE
    LocalStorage(),
    # SOCIAL (officiel uniquement)
    TikTokSocial(), YouTubeSocial(), InstagramSocial(),
    # ANALYTICS
    LocalAnalytics(),
    # SCHEDULER
    LocalScheduler(),
]

_BY_ID = {p.id: p for p in _REGISTRY}


def all():
    return list(_REGISTRY)


def get(pid):
    return _BY_ID.get(pid)


def by_kind(kind):
    return [p for p in _REGISTRY if p.kind == kind]


def status_report(deep=False):
    """État de tout le registre. deep=True exécute test() en ligne (peut appeler des APIs)."""
    out = []
    for p in _REGISTRY:
        h = p.health() if deep else {
            "id": p.id, "label": p.label, "kind": p.kind, "implemented": p.implemented,
            "mock": p.mock, "requires": p.requires, "costly": p.costly,
            "configured": p.configured(),
            "status": "not_implemented" if not p.implemented else ("mock" if p.mock else ("ok" if p.configured() else "not_configured" if p.requires else "ready")),
            "quality": p.quality,
        }
        out.append(h)
    return out
