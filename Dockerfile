# TESTÉ & PROPRE — Content OS · image de production (unique commande de start)
# python:3.11-slim + binaire ffmpeg fourni par imageio-ffmpeg (statique, aucun apt nécessaire).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
# Railway fournit $PORT ; app.py lit TNP_PORT→PORT→8090. TNP_DATA_DIR=/data vise le Volume monté.
ENV TNP_DATA_DIR=/data

WORKDIR /srv/app

# 1) dépendances d'abord (cache build)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 2) code + contenus seed (vidéos finales + voix + recherche + docs + app)
COPY . .

# 3) dossier volume (peut être monté par Railway sur /data)
RUN mkdir -p /data

EXPOSE 8090

# Healthcheck interne (Railway utilise aussi healthcheckPath=/health de railway.toml)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:%s/health'%os.environ.get('PORT','8090'),timeout=4)" || exit 1

# Commande unique de démarrage
CMD ["python", "-m", "server.app"]
