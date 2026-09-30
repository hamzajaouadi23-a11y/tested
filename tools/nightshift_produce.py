#!/usr/bin/env python3
"""Batch Night Shift — exécute ASSETS → VOICE → RENDER → QA → finalize pour des scripts donnés.
Usage : /home/user/venv-tnp/bin/python tools/nightshift_produce.py 5 6 7
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import db  # noqa: E402
from server.services import assets as assets_svc  # noqa: E402
from server.services import pipeline as pl  # noqa: E402
from server.services import qa as qa_svc  # noqa: E402
from server.services import render as render_svc  # noqa: E402
from server.services import voice as voice_svc  # noqa: E402


def produce(sid):
    line = {"script_id": sid}
    pl.set_state("script", sid, "ASSETS")
    a = assets_svc.acquire_for_script(sid)
    line["assets"] = {"total": a.get("total"), "realness": a.get("realness")}
    if not a.get("total"):
        line["blocked"] = "ASSETS"
        pl.set_state("script", sid, "BLOCKED", "aucun asset")
        return line

    pl.set_state("script", sid, "VOICE")
    v = voice_svc.synthesize_for_script(sid)
    line["voice"] = {"ok": v.get("ok"), "provider": v.get("provider"), "duration_s": v.get("duration_s")}
    if not v["ok"]:
        line["blocked"] = "VOICE"
        line["detail"] = v.get("detail")
        pl.set_state("script", sid, "BLOCKED", v.get("detail", "voix indisponible"))
        return line

    pl.set_state("script", sid, "RENDER")
    r = render_svc.render(sid)
    line["render"] = {"ok": r.get("ok"), "video_id": r.get("video_id"), "duration_s": r.get("duration_s")}
    if not r["ok"]:
        line["blocked"] = "RENDER"
        line["detail"] = r.get("detail")
        pl.set_state("script", sid, "BLOCKED", r.get("detail", "rendu échoué"))
        return line

    vid = r["video_id"]
    pl.set_state("video", vid, "QA")
    q = qa_svc.run(vid)
    line["qa"] = {"pass": q["pass"], "blockers": q["blockers"], "warnings": q["warnings"]}
    if not q["pass"]:
        pl.set_state("video", vid, "BLOCKED", "QA: " + ",".join(q["blockers"]))
        return line

    fin = qa_svc.finalize_for_post(vid)
    line["final"] = fin
    pl.set_state("script", sid, "WAITING_APPROVAL", "vidéo prête — validation humaine")
    pl.set_state("video", vid, "WAITING_APPROVAL", "vidéo prête — validation humaine")
    return line


def main():
    sids = [int(x) for x in sys.argv[1:]] or [5, 6, 7]
    out = []
    for sid in sids:
        print("▶ production script %d…" % sid, flush=True)
        res = produce(sid)
        out.append(res)
        print(json.dumps(res, ensure_ascii=False))
    ok = sum(1 for r in out if r.get("final", {}).get("ok"))
    print("=== %d/%d vidéo(s) en WAITING_APPROVAL ===" % (ok, len(out)))
    sys.exit(0 if ok == len(out) else 2)


if __name__ == "__main__":
    main()
