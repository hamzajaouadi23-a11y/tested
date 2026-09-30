#!/usr/bin/env bash
# Reconstruit l'environnement Python de la pipeline (2-3 min).
# IMPORTANT : ne JAMAIS utiliser un dossier prefixé par un point ou nommé .venv —
# les snapshots de session ne les conservent pas. On utilise $VENV (par défaut /home/user/venv-tnp).
set -e
VENV="${VENV:-/home/user/venv-tnp}"
if [ ! -x "$VENV/bin/python" ]; then
  echo "Création du venv : $VENV"
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet pillow requests imageio imageio-ffmpeg
echo "✅ Env prêt : $VENV"
"$VENV/bin/python" -c "import PIL, requests, imageio_ffmpeg; print('PIL', PIL.__version__, '| ffmpeg:', imageio_ffmpeg.get_ffmpeg_exe())"
