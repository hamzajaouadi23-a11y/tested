"""Service LEARNING — boucle d'apprentissage honnête.

- Se base UNIQUEMENT sur les métriques réelles saisies (analytics), AUTO_ANALYTICS=OFF.
- Échantillons faibles : le service le dit clairement et NE conclut PAS (pas de sur-apprentissage).
- Génère des VARIATIONS (jamais de clone exact d'une vidéo gagnante).
"""
from .. import db

MIN_SAMPLE = 5


def add_metrics(video_id, platform, views=0, likes=0, comments=0, shares=0, clicks=0, sales=0):
    db.run("INSERT INTO analytics(video_id,platform,views,likes,comments,shares,clicks,sales,captured_at)"
           " VALUES(?,?,?,?,?,?,?,?,?)",
           (video_id, platform, views, likes, comments, shares, clicks, sales, db.now()))
    db.log_event("analytics_added", {"video_id": video_id, "platform": platform, "views": views})
    return {"ok": True}


def analyze():
    rows = db.q("""
      SELECT a.*, v.script_id, s.style, s.hook, s.cta FROM analytics a
      JOIN videos v ON v.id = a.video_id
      LEFT JOIN scripts s ON s.id = v.script_id
      ORDER BY a.captured_at DESC""")
    n_videos = len({r["video_id"] for r in rows})
    if n_videos < MIN_SAMPLE:
        return {"ok": True, "enough_data": False, "videos_with_metrics": n_videos,
                "message": "Données insuffisantes (%d/%d vidéos mesurées). Aucune conclusion automatique "
                           "— accumuler les métriques réelles d'abord." % (n_videos, MIN_SAMPLE)}
    def eng(r):
        v = max(1, r["views"] or 0)
        return (r["likes"] + r["comments"] + r["shares"]) / v * 100
    ranked = sorted(rows, key=eng, reverse=True)
    best = ranked[0]
    by_style = {}
    for r in rows:
        by_style.setdefault(r["style"] or "?", []).append(eng(r))
    winning_styles = sorted(by_style.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))
    summary = {
        "ok": True, "enough_data": True, "videos_with_metrics": n_videos,
        "top_hook": best["hook"], "top_style": best["style"],
        "winning_styles": [{"style": s, "avg_engagement": round(sum(v) / len(v), 2)} for s, v in winning_styles],
        "note": "Tendances descriptives sur %d vidéos — pas une prédiction de ventes." % n_videos,
    }
    db.run("INSERT INTO learning(key,data_json,updated_at) VALUES('last_analysis',?,?) "
           "ON CONFLICT(key) DO UPDATE SET data_json=excluded.data_json, updated_at=excluded.updated_at",
           (__import__("json").dumps(summary, ensure_ascii=False), db.now()))
    return summary


def suggest_variations(video_id):
    """2 variations d'accroches à partir d'une vidéo — jamais le même hook (anti-clone)."""
    v = db.q("SELECT * FROM videos WHERE id=?", (video_id,), one=True)
    if not v:
        return {"ok": False, "detail": "vidéo introuvable"}
    from . import scripts
    script = scripts.get_script(v["script_id"])
    hook = script["hook"]
    variants = [
        "Variante curiosité : " + ("Et si " + hook[:60].rstrip(".") + " ?"),
        "Variante directe : " + ("30 secondes pour comprendre — " + hook[:60].rstrip(".")),
    ]
    return {"ok": True, "original": hook, "variants": variants,
            "rule": "variation créative — ne jamais republier la vidéo identique"}
