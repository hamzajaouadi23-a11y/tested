"""Service SÉLECTION — score interne de priorité.

⚠️ Le score est un AIDE au choix éditorial. Il NE prédit PAS les ventes, et l'interface
le présente comme tel. Critères (0–5 chacun, pondérés) : visual_demonstrability,
problem_clarity, solution_clarity, price, commission_potential, content_depth,
angles_count, competition (5 = faible), geo_potential, quality_evidence, risk (5 = faible).
"""
import json

from .. import db

WEIGHTS = {
    "visual_demonstrability": 3,
    "problem_clarity": 3,
    "solution_clarity": 2,
    "price": 1,
    "commission_potential": 2,
    "content_depth": 2,
    "angles_count": 2,
    "competition": 1,
    "geo_potential": 1,
    "quality_evidence": 2,
    "risk": 1,
}
CRITERIA = list(WEIGHTS.keys())
MAX_SCORE = sum(WEIGHTS[k] for k in CRITERIA) * 5


def score_candidate(c):
    scores = db.getjson(c, "scores_json", {}) if isinstance(c, dict) is False else (c.get("scores") or {})
    if not isinstance(scores, dict):
        scores = {}
    total, maxhit = 0, 0
    for k, w in WEIGHTS.items():
        v = scores.get(k, 0)
        try:
            v = max(0, min(5, float(v)))
        except Exception:
            v = 0
        total += w * v
        maxhit += w * 5
    return round(100.0 * total / (maxhit or MAX_SCORE), 1)


def rescore_all():
    rows = db.q("SELECT * FROM candidates")
    for r in rows:
        s = db.getjson(r, "scores_json", {}) or {}
        total, maxhit = 0, 0
        for k, w in WEIGHTS.items():
            try:
                v = max(0, min(5, float(s.get(k, 0))))
            except Exception:
                v = 0
            total += w * v
            maxhit += w * 5
        db.run("UPDATE candidates SET priority_score=? WHERE id=?", (round(100.0 * total / maxhit, 1), r["id"]))
    return db.q("SELECT COUNT(*) AS n FROM candidates", one=True)["n"]


def select_top(n=3):
    """Sélectionne les n meilleurs candidats 'proposed' → status 'selected'. Non destructif."""
    rescore_all()
    rows = db.q("SELECT * FROM candidates WHERE status='proposed' ORDER BY priority_score DESC")
    selected = rows[:n]
    for r in selected:
        db.run("UPDATE candidates SET status='selected' WHERE id=?", (r["id"],))
        db.log_event("candidate_selected", {"id": r["id"], "title": r["title"], "score": r["priority_score"]})
    return [dict(r) for r in selected]


def list_candidates(status=None):
    if status:
        rows = db.q("SELECT * FROM candidates WHERE status=? ORDER BY priority_score DESC", (status,))
    else:
        rows = db.q("SELECT * FROM candidates ORDER BY CASE status WHEN 'selected' THEN 0 WHEN 'used' THEN 1 ELSE 2 END, priority_score DESC")
    out = []
    for r in rows:
        d = dict(r)
        d["scores"] = db.getjson(r, "scores_json", {})
        out.append(d)
    return out


def get(cid):
    r = db.q("SELECT * FROM candidates WHERE id=?", (cid,), one=True)
    if not r:
        return None
    d = dict(r)
    d["scores"] = db.getjson(r, "scores_json", {})
    return d
