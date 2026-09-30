"""Wrapper FFmpeg — localisation du binaire + helpers (probe, durée, silence, frames)."""
import json
import os
import re
import subprocess
import sys

_EXE = None


def ffmpeg_exe():
    global _EXE
    if _EXE and os.path.exists(_EXE):
        return _EXE
    candidates = [
        "/home/user/venv-tnp/lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2",
        "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg",
    ]
    # découverte dynamique : (1) python COURANT (solution universelle — venv, conteneur, local),
    # (2) compat ancien chemin venv-tnp hardcodé (déjà couvert par la liste ci-dessus)
    try:
        out = subprocess.run([sys.executable, "-c",
                              "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"],
                             capture_output=True, text=True, timeout=30)
        if out.returncode == 0 and out.stdout.strip():
            candidates.insert(0, out.stdout.strip())
    except Exception:
        pass
    for c in candidates:
        if c and os.path.exists(c) and os.access(c, os.X_OK):
            _EXE = c
            return c
    raise RuntimeError("FFmpeg introuvable — installer imageio-ffmpeg dans le venv")


def run_cmd(args, timeout=300):
    exe = ffmpeg_exe()
    proc = subprocess.run([exe] + args, capture_output=True, text=True, timeout=timeout)
    return proc


def probe(path):
    """Équivalent ffprobe via 'ffmpeg -i' (le bundle n'inclut pas ffprobe)."""
    exe = ffmpeg_exe()
    proc = subprocess.run([exe, "-i", path], capture_output=True, text=True, timeout=60)
    txt = proc.stderr + proc.stdout
    info = {"path": path, "exists": os.path.exists(path)}
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", txt)
    if m:
        info["duration_s"] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    vs = re.search(r"Stream #\S+: Video: (\S+).*?(\d{2,4})x(\d{2,4}).*?([\d.]+) fps", txt)
    if vs:
        info["vcodec"] = vs.group(1)
        info["width"] = int(vs.group(2))
        info["height"] = int(vs.group(3))
        info["fps"] = float(vs.group(4))
    au = re.search(r"Stream #\S+: Audio: (\S+).*?(\d+) Hz", txt)
    if au:
        info["acodec"] = au.group(1)
        info["sample_rate"] = int(au.group(2))
    info["has_video"] = "Video:" in txt
    info["has_audio"] = "Audio:" in txt
    return info


def decodable(path, seconds=3):
    """Decode quelques secondes : échec = fichier corrompu."""
    proc = run_cmd(["-v", "error", "-t", str(seconds), "-i", path, "-f", "null", "-"], timeout=120)
    return proc.returncode == 0 and not proc.stderr.strip()


def audio_stats(path):
    """mean/max volume via volumedetect — détecte les pistes silencieuses."""
    proc = run_cmd(["-i", path, "-af", "volumedetect", "-f", "null", "-"], timeout=180)
    txt = proc.stderr + proc.stdout
    mean = re.search(r"mean_volume: ([-\d.]+) dB", txt)
    mx = re.search(r"max_volume: ([-\d.]+) dB", txt)
    return {"mean_db": float(mean.group(1)) if mean else None,
            "max_db": float(mx.group(1)) if mx else None}


def extract_frames(path, times, out_dir, prefix="f"):
    """Extrait des frames PNG à des instants donnés (pour QA : frames vides, contraste)."""
    os.makedirs(out_dir, exist_ok=True)
    outs = []
    for i, t in enumerate(times):
        out = os.path.join(out_dir, "%s_%d.png" % (prefix, i))
        proc = run_cmd(["-y", "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1", out], timeout=60)
        if proc.returncode == 0 and os.path.exists(out):
            outs.append(out)
    return outs


def version():
    proc = run_cmd(["-version"], timeout=30)
    return proc.stdout.splitlines()[0] if proc.returncode == 0 else "ffmpeg indisponible"
