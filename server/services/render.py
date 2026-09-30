"""Service RENDER — FFmpeg : MP4 H.264, 1080x1920 (9:16), 24–30 fps, AAC, +faststart.

Pipeline d'un script : frames compositées PIL (image + captions + chips + disclosure)
→ segments vidéo (Ken Burns zoompan, fondus d'entrée/sortie) → concat → voix off AAC.
Les outputs QA-passés sont déplacés dans data/media/ready_to_post/.
"""
import glob
import json
import os
import re
import shutil
import subprocess

from .. import config, db, ffmpegw
from . import composition, scripts, voice as voice_svc

W, H, FPS = 1080, 1920, 30


def _cover_crop(in_path, out_path):
    from PIL import Image
    img = Image.open(in_path).convert("RGB")
    iw, ih = img.size
    scale = max(W / iw, H / ih)
    nw, nh = int(iw * scale + 0.5), int(ih * scale + 0.5)
    img = img.resize((nw, nh), Image.LANCZOS)
    x0, y0 = (nw - W) // 2, (nh - H) // 2
    img.crop((x0, y0, x0 + W, y0 + H)).save(out_path, "PNG")
    return out_path


def _segments_timing(script, voice_dur):
    onscreen = script["onscreen"] or []
    n = max(len(onscreen), 1)
    total = max(voice_dur + 0.3, 14.0)
    hook_t = min(3.2, total * 0.18)
    rest = total - hook_t
    weights = [max(24, len((o or {}).get("text", ""))) for o in onscreen[1:]] or [1]
    if len(weights) < n - 1:
        weights += [weights[-1]] * (n - 1 - len(weights))
    s = sum(weights)
    times = [hook_t]
    for w_ in weights[: n - 1]:
        times.append(max(2.4, rest * w_ / s))
    # ajuste pour coller à total
    diff = total - sum(times)
    times[-1] = max(2.0, times[-1] + diff)
    return times, total


def _overlay_tag(script, idx):
    struct = {
        "A": ["HOOK", "PROBLÈME", "SOLUTION", "PREUVE", "CTA"],
        "B": ["AVANT", "MÉTHODE", "PENDANT", "APRÈS", "CTA"],
        "C": ["TEST", "MÉTHODE 1", "MÉTHODE 2", "VERDICT", "CTA"],
        "D": ["DUEL", "OPTION 1", "OPTION 2", "VERDICT", "CTA"],
        "E": ["CURIOSITÉ", "EXPLICATION", "DÉMO", "POURQUOI", "CTA"],
    }.get(script["style"], ["1", "2", "3", "4", "5"])
    return struct[min(idx, len(struct) - 1)]


def _encode_image_segment(frame_png, dur, out_mp4, fade_out=True):
    # zoompan d=1 : 1 frame de sortie par frame d'entrée (loop) — 'on' compte les frames de sortie,
    # le zoom progresse image par image (Ken Burns). -t borne la durée exacte.
    vf = ("scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
          "zoompan=z='min(1.0+on*0.0006,1.10)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=%dx%d:fps=%d,"
          "format=yuv420p,fade=t=in:st=0:d=0.25%s"
          % (W, H, FPS, ",fade=t=out:st=%.2f:d=0.25" % max(0, dur - 0.25) if fade_out else ""))
    proc = ffmpegw.run_cmd(["-y", "-v", "error", "-framerate", str(FPS), "-loop", "1",
                            "-t", "%.2f" % dur, "-i", frame_png,
                            "-vf", vf, "-t", "%.2f" % dur,
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", out_mp4],
                           timeout=300)
    return proc.returncode == 0 and os.path.exists(out_mp4)


def _encode_video_segment(clip_path, overlay_png, dur, out_mp4):
    vf = ("[0:v]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,setsar=1,fps=%d[base];"
          "[base][1:v]overlay=0:0,format=yuv420p,fade=t=in:st=0:d=0.25[v]"
          % (W, H, W, H, FPS))
    proc = ffmpegw.run_cmd(["-y", "-v", "error", "-stream_loop", "-1", "-t", "%.2f" % dur, "-i", clip_path,
                            "-i", overlay_png, "-filter_complex", vf, "-map", "[v]",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", out_mp4],
                           timeout=300)
    return proc.returncode == 0 and os.path.exists(out_mp4)


def render(script_id):
    script = scripts.get_script(script_id)
    if not script:
        return {"ok": False, "detail": "script introuvable"}
    voice = voice_svc.get_voice(script_id)
    if not voice:
        return {"ok": False, "blocked": True, "detail": "voix off manquante — étape VOICE d'abord"}
    assets = db.q("SELECT * FROM assets WHERE script_id=? ORDER BY id", (script_id,))
    if not assets:
        return {"ok": False, "blocked": True, "detail": "aucun asset — étape ASSETS d'abord"}

    tmp = os.path.join(config.TMP, "render_%d" % script_id)
    os.makedirs(tmp, exist_ok=True)
    for f in glob.glob(os.path.join(tmp, "*")):
        os.remove(f)

    has_ai = any(a["realness"] == "ai" for a in assets)
    onscreen = script["onscreen"] or []
    n = max(len(onscreen), len(assets))
    times, total = _segments_timing(script, voice["duration_s"])

    # 1) frames compositées
    frames, overlays_meta = [], []
    ordered = list(assets)
    for i in range(n):
        asset = ordered[i % len(ordered)]
        base = os.path.join(tmp, "base_%02d.png" % i)
        frame = os.path.join(tmp, "frame_%02d.png" % i)
        overlay = os.path.join(tmp, "overlay_%02d.png" % i)
        text = (onscreen[i]["text"] if i < len(onscreen) else script["hook"])[:90]
        tag = _overlay_tag(script, i)
        composition.caption_overlay(overlay, text, tag=tag, disclosure=has_ai)
        if asset["path"].lower().endswith(".png") or asset["path"].lower().endswith((".jpg", ".jpeg", ".webp")):
            _cover_crop(asset["path"], base)
            from PIL import Image
            b = Image.open(base).convert("RGBA")
            o = Image.open(overlay).convert("RGBA")
            Image.alpha_composite(b, o).convert("RGB").save(frame, "PNG")
            frames.append({"kind": "image", "frame": frame, "dur": times[min(i, len(times) - 1)]})
        else:  # clip vidéo importé
            frames.append({"kind": "video", "clip": asset["path"], "overlay": overlay,
                           "dur": times[min(i, len(times) - 1)]})
        overlays_meta.append(composition.measure_overlay(text, tag))

    # 2) segments encodés
    segs = []
    for i, fr in enumerate(frames):
        seg = os.path.join(tmp, "seg_%02d.mp4" % i)
        if fr["kind"] == "image":
            okc = _encode_image_segment(fr["frame"], fr["dur"], seg, fade_out=(i < len(frames) - 1))
        else:
            okc = _encode_video_segment(fr["clip"], fr["overlay"], fr["dur"], seg)
        if not okc:
            return {"ok": False, "detail": "échec encodage segment %d" % i}
        segs.append(seg)

    # 3) concat + voix
    lst = os.path.join(tmp, "concat.txt")
    with open(lst, "w") as f:
        for s in segs:
            f.write("file '%s'\n" % s)
    silent_v = os.path.join(tmp, "video_silent.mp4")
    proc = ffmpegw.run_cmd(["-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
                            "-c", "copy", silent_v], timeout=240)
    if proc.returncode != 0:
        proc = ffmpegw.run_cmd(["-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
                                "-c:v", "libx264", "-preset", "medium", "-crf", "22",
                                "-pix_fmt", "yuv420p", silent_v], timeout=300)
    if proc.returncode != 0:
        return {"ok": False, "detail": "concat échoué: " + proc.stderr[-200:]}

    out = os.path.join(config.DRAFTS, "script_%d.mp4" % script_id)
    proc = ffmpegw.run_cmd(["-y", "-v", "error", "-i", silent_v, "-i", voice["path"],
                            "-map", "0:v", "-map", "1:a",
                            "-c:v", "copy",
                            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                            "-c:a", "aac", "-b:a", "128k", "-shortest",
                            "-movflags", "+faststart", out], timeout=300)
    if proc.returncode != 0 or not os.path.exists(out):
        return {"ok": False, "detail": "mux final échoué: " + proc.stderr[-200:]}

    info = ffmpegw.probe(out)
    vid = db.run("INSERT INTO videos(script_id,path,filename,duration_s,width,height,fps,size_bytes,status,disclosure_json,created_at)"
                 " VALUES(?,?,?,?,?,?,?,?,'rendered',?,?)",
                 (script_id, out, os.path.basename(out), info.get("duration_s", total),
                  info.get("width", W), info.get("height", H), info.get("fps", FPS),
                  os.path.getsize(out),
                  json.dumps({"ai_assets": has_ai, "disclosure_required": has_ai,
                              "disclosure_shown_on_video": has_ai}, ensure_ascii=False),
                 db.now()))
    meta = {"video_id": vid, "overlays": overlays_meta, "segments": len(segs),
            "voice_provider": voice["provider"], "target_total_s": round(total, 2)}
    with open(os.path.join(tmp, "render_meta.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    db.log_event("video_rendered", {"video_id": vid, "script_id": script_id, "duration": info.get("duration_s")})
    return {"ok": True, "video_id": vid, "path": out, "duration_s": info.get("duration_s"),
            "size_bytes": os.path.getsize(out)}
