"""Service VOIX — Azure → ElevenLabs → import opérateur (data/voice/inbox/script_<id>.mp3).

JAMAIS de piste silencieuse fake : si aucune vraie voix n'est disponible → BLOCKED honnête.
La durée réelle est mesurée via ffmpeg et stockée.
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

    # 1) Azure Speech
    az = providers.get("voice_azure")
    if az.configured():
        r = az.synthesize(text, tmp)
        tried.append({"provider": "azure", "ok": r["ok"], "detail": r.get("detail", "")})
        if r["ok"]:
            return _register(script_id, tmp, "azure", text)

    # 2) ElevenLabs
    el = providers.get("voice_elevenlabs")
    if el.configured():
        r = el.synthesize(text, tmp)
        tried.append({"provider": "elevenlabs", "ok": r["ok"], "detail": r.get("detail", "")})
        if r["ok"]:
            return _register(script_id, tmp, "elevenlabs", text)

    # 3) Import opérateur (voix réelle fournie — data/voice/inbox/script_<id>.mp3)
    vi = providers.get("voice_import")
    found = vi.find_for_script(script_id)
    if found:
        shutil.copy2(found, tmp)
        return _register(script_id, tmp, "voice_import", text)

    db.log_event("voice_blocked", {"script_id": script_id, "tried": tried,
                                   "reason": "aucune vraie voix disponible (configurez Azure/ElevenLabs "
                                             "ou déposez data/voice/inbox/script_%d.mp3)" % script_id})
    return {"ok": False, "blocked": True, "tried": tried,
            "detail": "Aucune voix réelle disponible. Options : configurer AZURE_SPEECH_KEY/REGION ou "
                      "ELEVENLABS_API_KEY dans Réglages, ou déposer le fichier "
                      "data/voice/inbox/script_%d.mp3" % script_id}


def _register(script_id, path, provider, text):
    ok, info = _validate_audio(path)
    if not ok:
        return {"ok": False, "detail": "voix rejetée par validation: %s" % info, "provider": provider}
    dest = os.path.join(config.ASSETS, "voice_script_%d.mp3" % script_id)
    shutil.move(path, dest)
    vid = db.run("INSERT INTO voices(script_id,path,provider,lang,duration_s,chars,created_at) VALUES(?,?,?,?,?,?,?)",
                 (script_id, dest, provider, config.LANG, float(info), len(text), db.now()))
    db.log_event("voice_ready", {"script_id": script_id, "provider": provider, "duration_s": info})
    return {"ok": True, "voice_id": vid, "provider": provider, "duration_s": info, "path": dest}


def get_voice(script_id):
    r = db.q("SELECT * FROM voices WHERE script_id=? ORDER BY id DESC", (script_id,), one=True)
    return dict(r) if r else None
