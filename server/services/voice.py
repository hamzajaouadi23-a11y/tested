"""Service VOIX — ElevenLabs → Azure → import opérateur (data/voice/inbox/script_<id>.mp3).

JAMAIS de piste silencieuse fake : si aucune vraie voix n'est disponible → BLOCKED honnête.
La durée réelle est mesurée via ffmpeg et stockée.
Le provider utilisé et sa position dans la chaîne (fallback ou non) sont TOUJOURS tracés
(événement voice_ready) : fallback=True dès que la voix ne vient pas de la tête de chaîne.
"""
import os
import shutil

from .. import config, db, ffmpegw, providers


def _validate_audio(path):
    """Une voix production = fichier lisible, ≥ 2 s, non silencieux."""
    info = ffmpegw.probe(path)
    if not info.get("has_audio"):
        return False, "pas de piste audio"
    dur = info.get("duration_s", 0)
    if dur < 2:
        return False, "trop court (%.1fs)" % dur
    stats = ffmpegw.audio_stats(path)
    if stats["mean_db"] is not None and stats["mean_db"] < -50:
        return False, "piste silencieuse (mean %.1f dB)" % stats["mean_db"]
    return True, dur


def synthesize_for_script(script_id):
    from . import scripts
    script = scripts.get_script(script_id)
    if not script:
        return {"ok": False, "detail": "script introuvable"}
    existing = get_voice(script_id)
    if existing and os.path.exists(existing["path"]):
        return {"ok": True, "voice_id": existing["id"], "provider": existing["provider"],
                "duration_s": existing["duration_s"], "path": existing["path"], "reused": True}
    text = script["vo_text"]
    tmp = os.path.join(config.TMP, "voice_%d.mp3" % script_id)
    tried = []

    # 1) ElevenLabs (tête de chaîne)
    el = providers.get("voice_elevenlabs")
    if el.configured():
        r = el.synthesize(text, tmp)
        tried.append({"provider": "elevenlabs", "ok": r["ok"], "detail": r.get("detail", "")})
        if r["ok"]:
            return _register(script_id, tmp, "elevenlabs", text, tried)
    else:
        tried.append({"provider": "elevenlabs", "ok": None, "detail": "non configuré — ignoré"})

    # 2) Azure Speech
    az = providers.get("voice_azure")
    if az.configured():
        r = az.synthesize(text, tmp)
        tried.append({"provider": "azure", "ok": r["ok"], "detail": r.get("detail", "")})
        if r["ok"]:
            return _register(script_id, tmp, "azure", text, tried)
    else:
        tried.append({"provider": "azure", "ok": None, "detail": "non configuré — ignoré"})

    # 3) Import opérateur (voix réelle fournie — data/voice/inbox/script_<id>.mp3)
    vi = providers.get("voice_import")
    found = vi.find_for_script(script_id)
    if found:
        shutil.copy2(found, tmp)
        return _register(script_id, tmp, "voice_import", text, tried)

    db.log_event("voice_blocked", {"script_id": script_id, "tried": tried,
                                   "reason": "aucune vraie voix disponible (configurez Azure/ElevenLabs "
                                             "ou déposez data/voice/inbox/script_%d.mp3)" % script_id})
    return {"ok": False, "blocked": True, "tried": tried,
            "detail": "Aucune voix réelle disponible. Options : configurer AZURE_SPEECH_KEY/REGION ou "
                      "ELEVENLABS_API_KEY dans Réglages, ou déposer le fichier "
                      "data/voice/inbox/script_%d.mp3" % script_id}


def _register(script_id, path, provider, text, tried=None):
    ok, info = _validate_audio(path)
    if not ok:
        return {"ok": False, "detail": "voix rejetée par validation: %s" % info, "provider": provider}
    dest = os.path.join(config.ASSETS, "voice_script_%d.mp3" % script_id)
    shutil.move(path, dest)
    vid = db.run("INSERT INTO voices(script_id,path,provider,lang,duration_s,chars,created_at) VALUES(?,?,?,?,?,?,?)",
                 (script_id, dest, provider, config.LANG, float(info), len(text), db.now()))
    fallback = provider != "elevenlabs"  # tête de chaîne déclarée
    db.log_event("voice_ready", {"script_id": script_id, "provider_used": provider,
                                 "provider_fallback": fallback, "duration_s": info,
                                 "chain_tried": tried or []})
    return {"ok": True, "voice_id": vid, "provider": provider, "provider_fallback": fallback,
            "duration_s": info, "path": dest}


def get_voice(script_id):
    r = db.q("SELECT * FROM voices WHERE script_id=? ORDER BY id DESC", (script_id,), one=True)
    return dict(r) if r else None
