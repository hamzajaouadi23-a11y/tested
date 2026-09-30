"""Serveur HTTP — Backend Production Pipeline (stdlib uniquement).
Écoute 0.0.0.0:8090. Sert : Studio UI (/), app de vente V2 (/app), API JSON (/api/*), médias (/media/*).

Aucun secret n'est jamais renvoyé : /api/secrets ne renvoie que {nom, configured}.
Lancement : cd <repo> && /home/user/venv-tnp/bin/python -m server.app
"""
import json
import os
import signal
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config, db, providers
from .services import assets as assets_svc
from .services import learning as learning_svc
from .services import pipeline as pipeline_svc
from .services import qa as qa_svc
from .services import render as render_svc
from .services import research as research_svc
from .services import scripts as scripts_svc
from .services import selection as selection_svc
from .services import voice as voice_svc

HOST = os.environ.get("TNP_HOST", "0.0.0.0")
# Chaîne de port (hébergements cloud) : TNP_PORT (override implicite) → PORT (Railway/Render…) → 8090 local
PORT = int(os.environ.get("TNP_PORT") or os.environ.get("PORT") or "8090")
ROOT = config.ROOT
STARTED = time.time()

MIME = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "application/javascript",
        ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".mp4": "video/mp4", ".mp3": "audio/mpeg", ".txt": "text/plain; charset=utf-8",
        ".md": "text/markdown; charset=utf-8", ".svg": "image/svg+xml"}


def _safe_path(base, rel):
    rel = urllib.parse.unquote(rel).lstrip("/")
    full = os.path.normpath(os.path.join(base, rel))
    if not full.startswith(os.path.abspath(base)):
        return None
    return full


def _scheduler_loop(stop):
    while not stop.is_set():
        try:
            due = providers.get("scheduler_local").due()
            for r in due:
                db.log_event("schedule_due", {"video_id": r["video_id"], "platform": r["platform"]})
        except Exception as e:
            db.log_event("scheduler_error", {"error": str(e)[:150]})
        stop.wait(45)


class Handler(BaseHTTPRequestHandler):
    server_version = "TNP-ContentOS/5.0"

    def log_message(self, fmt, *args):
        pass  # journal HTTP silencieux (les vrais événements métier vont dans `events`)

    # ---------- helpers ----------
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path, download_name=None):
        if not path or not os.path.isfile(path):
            return self._json({"ok": False, "detail": "fichier introuvable"}, 404)
        ext = os.path.splitext(path)[1].lower()
        size = os.path.getsize(path)
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(size))
        self.send_header("Accept-Ranges", "bytes")
        if download_name:
            self.send_header("Content-Disposition", 'attachment; filename="%s"' % download_name)
        self.end_headers()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if not n:
            return {}
        raw = self.rfile.read(n)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    # ---------- routing ----------
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path, qs = url.path, urllib.parse.parse_qs(url.query)
        try:
            if path in ("/", "/studio", "/index.html"):
                return self._file(os.path.join(ROOT, "studio", "index.html"))
            if path.startswith("/studio/"):
                return self._file(_safe_path(os.path.join(ROOT, "studio"), path[8:]))
            if path in ("/app", "/app/", "/vente"):
                return self._file(os.path.join(ROOT, "teste-et-propre", "index.html"))
            if path.startswith("/media/"):
                return self._file(_safe_path(config.MEDIA, path[7:]))
            if path == "/health":
                # Healthcheck plateforme (Railway/Render/uptime) : léger, sans toucher la DB —
                # un 200 prouve que le processus sert du HTTP.
                return self._json({"ok": True, "service": "tnp-contentos", "uptime_s": int(time.time() - STARTED)})
            if path == "/api/status":
                return self.get_status()
            if path == "/api/providers":
                deep = qs.get("deep", ["0"])[0] == "1"
                return self._json({"ok": True, "providers": providers.status_report(deep=deep)})
            if path == "/api/providers/test":
                # Miroir GET du POST canonique (test RÉEL d'un seul provider, borné) —
                # permet à l'opérateur/gardien de sonder sans outillage POST.
                p = providers.get(qs.get("id", [""])[0])
                if not p:
                    return self._json({"ok": False, "detail": "provider inconnu"}, 404)
                return self._json({"ok": True, "id": p.id, "test": p.test(), "health": p.health()})
            if path == "/api/run/research":
                # Déclencheur opérateur GET (autant autorisé que le POST) : import inbox
                # puis recherche Gemini grounding si configurée. Traité en tâche de fond.
                def jobr():
                    research_svc.run()
                threading.Thread(target=jobr, daemon=True).start()
                db.log_event("run_trigger", {"route": "GET /api/run/research"})
                return self._json({"ok": True, "started": True, "note": "résultats via /api/research/runs & /api/events"})
            if path == "/api/run/candidate":
                c = {"title": qs.get("title", [""])[0], "problem": qs.get("problem", [""])[0],
                     "solution": qs.get("solution", [""])[0],
                     "product_name": qs.get("product_name", [""])[0],
                     "product_url": qs.get("product_url", [""])[0], "price": qs.get("price", [""])[0]}
                cid = research_svc.add_candidate(c)
                if not cid:
                    return self._json({"ok": False, "detail": "title, problem et solution sont requis"}, 400)
                db.run("UPDATE candidates SET status='selected' WHERE id=?", (cid,))
                db.log_event("run_trigger", {"route": "GET /api/run/candidate", "candidate_id": cid})
                return self._json({"ok": True, "candidate_id": cid, "status": "selected"})
            if path == "/api/pipeline/run":
                cid = int(qs.get("candidate_id", ["0"])[0] or 0)
                styles = ([s.strip() for s in qs.get("styles", [""])[0].split(",") if s.strip()] or None)
                if not cid:
                    return self._json({"ok": False, "detail": "candidate_id requis"}, 400)
                def jobg():
                    pipeline_svc.run_candidate(cid, styles=styles)
                threading.Thread(target=jobg, daemon=True).start()
                db.log_event("run_trigger", {"route": "GET /api/pipeline/run", "candidate_id": cid,
                                             "styles": styles or "A,B,C"})
                return self._json({"ok": True, "started": True, "candidate_id": cid,
                                   "styles": styles or ["A", "B", "C"],
                                   "note": "suivi via /api/pipeline/board, /api/events, /api/videos"})
            if path == "/api/flags":
                return self._json({"ok": True, "flags": {
                    "AUTO_RESEARCH": config.AUTO_RESEARCH, "AUTO_GENERATION": config.AUTO_GENERATION,
                    "AUTO_RENDER": config.AUTO_RENDER, "AUTO_PUBLISH": False, "AUTO_ANALYTICS": config.AUTO_ANALYTICS}})
            if path == "/api/secrets":
                return self._json({"ok": True, "secrets": [
                    {"key": k, "configured": config.secret_configured(k)} for k in config.SECRET_KEYS]})
            if path == "/api/research/findings":
                return self._json({"ok": True, "findings": research_svc.findings()})
            if path == "/api/research/runs":
                return self._json({"ok": True, "runs": research_svc.runs()})
            if path == "/api/candidates":
                return self._json({"ok": True, "candidates": selection_svc.list_candidates(),
                                   "criteria": selection_svc.CRITERIA, "weights": selection_svc.WEIGHTS})
            if path == "/api/scripts":
                cid = qs.get("candidate_id", [None])[0]
                return self._json({"ok": True, "scripts": scripts_svc.list_scripts(int(cid) if cid else None)})
            if path == "/api/videos":
                return self._json({"ok": True, "videos": self._videos()})
            if path == "/api/pipeline/board":
                return self._json({"ok": True, "board": pipeline_svc.board()})
            if path == "/api/schedule":
                return self._json({"ok": True, "schedule": [dict(r) for r in db.q(
                    "SELECT s.*, v.filename FROM schedule s LEFT JOIN videos v ON v.id=s.video_id ORDER BY planned_at")]})
            if path == "/api/learning":
                return self._json(learning_svc.analyze())
            if path == "/api/events":
                return self._json({"ok": True, "events": [
                    {"id": r["id"], "kind": r["kind"], "payload": db.getjson(r, "payload_json", {}), "at": r["created_at"]}
                    for r in db.q("SELECT * FROM events ORDER BY id DESC LIMIT 60")]})
            if path.startswith("/api/qa/"):
                vid = int(path.split("/")[-1])
                v = db.q("SELECT qa_json FROM videos WHERE id=?", (vid,), one=True)
                return self._json({"ok": bool(v), "qa": db.getjson(v, "qa_json", None) if v else None})
            return self._json({"ok": False, "detail": "route inconnue: " + path}, 404)
        except Exception as e:
            db.log_event("api_error", {"path": path, "error": str(e)[:300]})
            return self._json({"ok": False, "detail": "erreur serveur: %s" % str(e)[:200]}, 500)

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path
        body = self._body()
        try:
            if path == "/api/flags":
                name, value = body.get("name", ""), bool(body.get("value"))
                allowed = {"AUTO_RESEARCH", "AUTO_GENERATION", "AUTO_RENDER", "AUTO_ANALYTICS"}
                if name == "AUTO_PUBLISH" and value:
                    return self._json({"ok": False, "detail": "AUTO_PUBLISH est verrouillé OFF — publication humaine uniquement."}, 403)
                if name not in allowed:
                    return self._json({"ok": False, "detail": "flag inconnu"}, 400)
                config.save_env_key(name, "true" if value else "false")
                setattr(config, name, value)
                return self._json({"ok": True, "flags": {name: value}})
            if path == "/api/secrets":
                key, value = body.get("key", "").strip(), body.get("value", "").strip()
                if key not in config.SECRET_KEYS:
                    return self._json({"ok": False, "detail": "clé inconnue"}, 400)
                if not value:
                    config.delete_env_key(key)
                    return self._json({"ok": True, "key": key, "configured": False})
                config.save_env_key(key, value)
                db.log_event("secret_updated", {"key": key})
                return self._json({"ok": True, "key": key, "configured": True})
            if path == "/api/providers/test":
                p = providers.get(body.get("id", ""))
                if not p:
                    return self._json({"ok": False, "detail": "provider inconnu"}, 404)
                return self._json({"ok": True, "id": p.id, "test": p.test(), "health": p.health()})
            if path == "/api/research/run":
                return self._json(research_svc.run())
            if path == "/api/research/import":
                return self._json(research_svc.import_inbox())
            if path == "/api/candidates":
                cid = research_svc.add_candidate(body)
                return self._json({"ok": bool(cid), "candidate_id": cid},
                                  201 if cid else 400)
            if path == "/api/select/run":
                return self._json({"ok": True, "selected": selection_svc.select_top(int(body.get("n", 3)))})
            if path == "/api/pipeline/run":
                cid = int(body.get("candidate_id", 0))
                styles = body.get("styles")
                def job():
                    pipeline_svc.run_candidate(cid, styles=styles)
                threading.Thread(target=job, daemon=True).start()
                return self._json({"ok": True, "started": True, "candidate_id": cid})
            if path == "/api/pipeline/research":
                def job2():
                    pipeline_svc.run_research()
                threading.Thread(target=job2, daemon=True).start()
                return self._json({"ok": True, "started": True})
            if path == "/api/videos/approve":
                return self._json(pipeline_svc.approve(int(body.get("video_id", 0)), body.get("note", "")))
            if path == "/api/videos/reject":
                return self._json(pipeline_svc.reject(int(body.get("video_id", 0)), body.get("note", "")))
            if path == "/api/videos/qa":
                return self._json(qa_svc.run(int(body.get("video_id", 0))))
            if path == "/api/schedule":
                return self._json(pipeline_svc.schedule(int(body.get("video_id", 0)),
                                                        body.get("platform", "TikTok"), body.get("planned_at", "")))
            if path == "/api/published":
                return self._json(pipeline_svc.mark_published(int(body.get("video_id", 0)), body.get("platform", "TikTok")))
            if path == "/api/analytics":
                return self._json(learning_svc.add_metrics(int(body.get("video_id", 0)), body.get("platform", "TikTok"),
                                                           int(body.get("views", 0)), int(body.get("likes", 0)),
                                                           int(body.get("comments", 0)), int(body.get("shares", 0)),
                                                           int(body.get("clicks", 0)), int(body.get("sales", 0))))
            if path == "/api/learning/variations":
                return self._json(learning_svc.suggest_variations(int(body.get("video_id", 0))))
            return self._json({"ok": False, "detail": "route inconnue: " + path}, 404)
        except Exception as e:
            db.log_event("api_error", {"path": path, "error": str(e)[:300]})
            return self._json({"ok": False, "detail": "erreur serveur: %s" % str(e)[:200]}, 500)

    # ---------- vues ----------
    def get_status(self):
        vids = db.q("SELECT status, COUNT(*) AS n FROM videos GROUP BY status")
        return self._json({
            "ok": True, "app": "TESTÉ & PROPRE — Content OS", "version": "v6-cloud",
            "commit": os.environ.get("RAILWAY_GIT_COMMIT_SHA", "local")[:12],
            "data_dir": config.DATA,
            "persistence": "volume persistant" if os.environ.get("TNP_DATA_DIR") else "locale (repo)",
            "uptime_s": int(time.time() - STARTED),
            "flags": {"AUTO_RESEARCH": config.AUTO_RESEARCH, "AUTO_GENERATION": config.AUTO_GENERATION,
                      "AUTO_RENDER": config.AUTO_RENDER, "AUTO_PUBLISH": False, "AUTO_ANALYTICS": config.AUTO_ANALYTICS},
            "counts": {
                "facts": db.q("SELECT COUNT(*) AS n FROM facts", one=True)["n"],
                "sources": db.q("SELECT COUNT(*) AS n FROM sources", one=True)["n"],
                "candidates": db.q("SELECT COUNT(*) AS n FROM candidates", one=True)["n"],
                "selected": db.q("SELECT COUNT(*) AS n FROM candidates WHERE status IN ('selected','used')", one=True)["n"],
                "scripts": db.q("SELECT COUNT(*) AS n FROM scripts", one=True)["n"],
                "voices": db.q("SELECT COUNT(*) AS n FROM voices", one=True)["n"],
                "videos_by_status": {r["status"]: r["n"] for r in vids},
            },
            "providers_real": sum(1 for p in providers.all() if p.implemented and not p.mock),
            "publish_mode": "humain uniquement (AUTO_PUBLISH=OFF)",
        })

    def _videos(self):
        rows = db.q("""SELECT v.*, s.hook, s.style FROM videos v
                       LEFT JOIN scripts s ON s.id = v.script_id ORDER BY v.id DESC LIMIT 30""")
        out = []
        for r in rows:
            d = dict(r)
            d["qa"] = db.getjson(r, "qa_json", None)
            d["disclosure"] = db.getjson(r, "disclosure_json", {})
            if d.get("path", "").startswith(config.MEDIA):
                d["url"] = "/media/" + os.path.relpath(d["path"], config.MEDIA).replace(os.sep, "/")
            out.append(d)
        return out


def main():
    db.init()
    stop = threading.Event()
    t = threading.Thread(target=_scheduler_loop, args=(stop,), daemon=True)
    t.start()
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print("TESTÉ & PROPRE — Content OS · pipeline prêt sur http://%s:%d" % (HOST, PORT))
    print("  Studio UI : /     App de vente V2 : /app     API : /api/status")

    def _sigterm(_s=None, _f=None):
        # SIGTERM (arrêt sandbox Arena/e2b) → shutdown() propre depuis un thread
        # (le handler ne doit pas bloquer le thread principal).
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _sigterm)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()


if __name__ == "__main__":
    main()
