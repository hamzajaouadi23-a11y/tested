"""Service PIPELINE — machine à états :

RESEARCH → SELECT → SCRIPT → ASSETS → VOICE → RENDER → QA → WAITING_APPROVAL
→ (humain) APPROVED → SCHEDULED → (humain) PUBLISHED

JAMAIS de publication automatique : AUTO_PUBLISH est OFF et non contournable ici.
"""
import json

from .. import config, db
from . import assets as assets_svc
from . import qa as qa_svc
from . import render as render_svc
from . import research as research_svc
from . import scripts as scripts_svc
from . import selection as selection_svc
from . import voice as voice_svc

STATES = ["RESEARCH", "SELECT", "SCRIPT", "ASSETS", "VOICE", "RENDER", "QA",
          "WAITING_APPROVAL", "APPROVED", "SCHEDULED", "PUBLISHED", "BLOCKED"]


def set_state(ref_type, ref_id, state, reason=""):
    assert state in STATES
    row = db.q("SELECT * FROM pipeline_items WHERE ref_type=? AND ref_id=?", (ref_type, ref_id), one=True)
    hist = (db.getjson(row, "history_json", []) if row else []) or []
    hist.append({"state": state, "at": db.now(), "reason": reason})
    if row:
        db.run("UPDATE pipeline_items SET state=?, reason=?, history_json=?, updated_at=? WHERE id=?",
               (state, reason, json.dumps(hist, ensure_ascii=False), db.now(), row["id"]))
    else:
        db.run("INSERT INTO pipeline_items(ref_type,ref_id,state,reason,history_json,updated_at) VALUES(?,?,?,?,?,?)",
               (ref_type, ref_id, state, reason, json.dumps(hist, ensure_ascii=False), db.now()))
    db.log_event("pipeline_state", {"ref": "%s/%s" % (ref_type, ref_id), "state": state, "reason": reason})


def get_state(ref_type, ref_id):
    row = db.q("SELECT * FROM pipeline_items WHERE ref_type=? AND ref_id=?", (ref_type, ref_id), one=True)
    if not row:
        return None
    d = dict(row)
    d["history"] = db.getjson(row, "history_json", [])
    return d


def run_research():
    set_state("global", 0, "RESEARCH")
    r = research_svc.run()
    return r


def run_select(n=3):
    set_state("global", 0, "SELECT")
    return selection_svc.select_top(n)


def run_candidate(candidate_id, styles=None):
    """SCRIPT → ASSETS → VOICE → RENDER → QA → WAITING_APPROVAL. S'arrête proprement si bloqué."""
    trace = {"candidate_id": candidate_id, "stages": []}

    def stage(name, ok, detail=""):
        trace["stages"].append({"stage": name, "ok": ok, "detail": detail})
        set_state("candidate", candidate_id, name if ok else "BLOCKED", detail if not ok else "")
        return ok

    if not config.AUTO_GENERATION:
        stage("SCRIPT", False, "AUTO_GENERATION=OFF — génération déclenchée manuellement")
        return trace
    gen = scripts_svc.generate_for_candidate(candidate_id, styles=styles or ["A", "B", "C"])
    if not gen["ok"]:
        stage("SCRIPT", False, gen.get("detail", "échec"))
        return trace
    stage("SCRIPT", True, "%d scripts (%s)" % (len(gen["scripts"]), ", ".join(s["provider"] for s in gen["scripts"])))

    results = []
    for s in gen["scripts"]:
        sid = s["script_id"]
        set_state("script", sid, "ASSETS")
        a = assets_svc.acquire_for_script(sid)
        if not a["ok"]:
            stage("ASSETS", False, a.get("detail", ""))
            continue
        set_state("script", sid, "VOICE")
        v = voice_svc.synthesize_for_script(sid)
        if not v["ok"]:
            stage("VOICE", False, v.get("detail", ""))
            results.append({"script_id": sid, "blocked": "VOICE", "detail": v.get("detail", "")})
            continue
        if not config.AUTO_RENDER:
            stage("RENDER", False, "AUTO_RENDER=OFF")
            continue
        set_state("script", sid, "RENDER")
        r = render_svc.render(sid)
        if not r["ok"]:
            stage("RENDER", False, r.get("detail", ""))
            results.append({"script_id": sid, "blocked": "RENDER", "detail": r.get("detail", "")})
            continue
        video_id = r["video_id"]
        set_state("video", video_id, "QA")
        qres = qa_svc.run(video_id)
        if not qres["pass"]:
            set_state("video", video_id, "BLOCKED", "QA: " + ",".join(qres["blockers"]))
            results.append({"script_id": sid, "video_id": video_id, "qa": "failed", "blockers": qres["blockers"]})
            continue
        fin = qa_svc.finalize_for_post(video_id)
        set_state("video", video_id, "WAITING_APPROVAL", "validation humaine requise avant publication")
        results.append({"script_id": sid, "video_id": video_id, "ready": fin.get("name"), "qa": "passed"})
    trace["results"] = results
    ok_any = any(r.get("qa") == "passed" for r in results)
    trace["stages"].append({"stage": "WAITING_APPROVAL", "ok": ok_any,
                            "detail": "%d vidéo(s) prête(s) à valider" % sum(1 for r in results if r.get("qa") == "passed")})
    if ok_any:
        set_state("candidate", candidate_id, "WAITING_APPROVAL")
    else:
        set_state("candidate", candidate_id, "BLOCKED", "aucune vidéo n'a passé la QA/voix")
    return trace


def approve(video_id, note="", decided_by="founder"):
    """Approbation HUMAINE. Refuse si QA non passée."""
    v = db.q("SELECT * FROM videos WHERE id=?", (video_id,), one=True)
    if not v:
        return {"ok": False, "detail": "vidéo introuvable"}
    qa = db.getjson(v, "qa_json", {}) or {}
    if v["status"] != "qa_passed" or not qa.get("pass"):
        return {"ok": False, "detail": "QA non passée — approbation impossible"}
    db.run("INSERT INTO approvals(video_id,decision,note,decided_at) VALUES(?,'approved',?,?)",
           (video_id, note, db.now()))
    db.run("UPDATE videos SET status='approved' WHERE id=?", (video_id,))
    set_state("video", video_id, "APPROVED", note or "approuvée manuellement")
    return {"ok": True}


def reject(video_id, note=""):
    v = db.q("SELECT * FROM videos WHERE id=?", (video_id,), one=True)
    if not v:
        return {"ok": False, "detail": "vidéo introuvable"}
    db.run("INSERT INTO approvals(video_id,decision,note,decided_at) VALUES(?,'rejected',?,?)",
           (video_id, note, db.now()))
    db.run("UPDATE videos SET status='rejected' WHERE id=?", (video_id,))
    set_state("video", video_id, "BLOCKED", "rejetée: " + note)
    return {"ok": True}


def schedule(video_id, platform, planned_at):
    v = db.q("SELECT * FROM videos WHERE id=?", (video_id,), one=True)
    if not v or v["status"] != "approved":
        return {"ok": False, "detail": "seule une vidéo APPROUVÉE peut être planifiée"}
    db.run("INSERT INTO schedule(video_id,platform,planned_at,state,created_at) VALUES(?,?,?,'planned',?)",
           (video_id, platform, planned_at, db.now()))
    set_state("video", video_id, "SCHEDULED", "%s à %s (rappel — publication manuelle)" % (platform, planned_at))
    return {"ok": True}


def mark_published(video_id, platform):
    """Déclaration HUMAINE après publication manuelle sur la plateforme."""
    v = db.q("SELECT * FROM videos WHERE id=?", (video_id,), one=True)
    if not v:
        return {"ok": False, "detail": "vidéo introuvable"}
    db.run("UPDATE schedule SET state='done' WHERE video_id=? AND platform=?", (video_id, platform))
    db.run("UPDATE videos SET status='published' WHERE id=?", (video_id,))
    set_state("video", video_id, "PUBLISHED", "déclarée publiée manuellement sur " + platform)
    db.log_event("published_declared", {"video_id": video_id, "platform": platform})
    return {"ok": True}


def board():
    """Vue globale pour l'UI."""
    return {
        "candidates": [dict(r) for r in db.q("SELECT * FROM pipeline_items WHERE ref_type='candidate' ORDER BY updated_at DESC LIMIT 20")],
        "scripts": [dict(r) for r in db.q("SELECT * FROM pipeline_items WHERE ref_type='script' ORDER BY updated_at DESC LIMIT 20")],
        "videos": [dict(r) for r in db.q("SELECT * FROM pipeline_items WHERE ref_type='video' ORDER BY updated_at DESC LIMIT 20")],
    }
