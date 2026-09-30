#!/usr/bin/env python3
"""Night Shift — reconstruction complète de l'état du batch après perte de la base.

Séquence : recherche (inbox) → sélection top 3 → scripts (styles A/B/C) → passe éditoriale
→ re-mapping des assets inbox vers les nouveaux ids → production (voix/rendu/QA/finalize).
Idempotent au niveau fichiers ; conçu pour être rejoué sans risque.
"""
import glob
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import config, db  # noqa: E402
from server.services import research, scripts, selection  # noqa: E402
from tools.nightshift_polish import EDITS  # noqa: E402
from tools.nightshift_produce import produce  # noqa: E402

STYLE_FOR = {"brosse": "A", "rouleau": "B", "tiroirs": "C"}


def style_of(title):
    t = (title or "").lower()
    for k, s in STYLE_FOR.items():
        if k in t:
            return s
    return "A"


def main():
    print("1/6 import recherche…")
    imp = research.import_inbox()
    print("   ", json.dumps(imp, ensure_ascii=False))

    print("2/6 sélection top 3…")
    selected = selection.select_top(3)
    plan = []
    for c in selected:
        st = style_of(c["title"])
        plan.append({"candidate_id": c["id"], "style": st, "title": c["title"]})
        print("   → #%d style %s : %s (score %s)" % (c["id"], st, c["title"][:60], c["priority_score"]))

    print("3/6 génération scripts…")
    old_for_style = {"A": 5, "B": 6, "C": 7}   # ids des voix/images déjà en inbox
    mapping = {}
    for p in plan:
        r = scripts.generate_for_candidate(p["candidate_id"], styles=[p["style"]])
        sid = r["scripts"][0]["script_id"]
        p["script_id"] = sid
        mapping[old_for_style[p["style"]]] = sid
        print("   → script %d (style %s)" % (sid, p["style"]))

    print("4/6 passe éditoriale (polish)…")
    from tools.nightshift_polish import apply_edit
    for p in plan:
        sid = p["script_id"]
        e = EDITS[old_for_style[p["style"]]]
        apply_edit(sid, e)
        print("   ✔ script %d édité (%d claims sourcés)" % (sid, len(e["claims"])))

    print("5/6 re-mapping inbox (assets + voix) vers les nouveaux ids…")
    for old, new in mapping.items():
        if old == new:
            print("   = id stable %d — rien à faire" % old)
            continue
        for f in glob.glob(os.path.join(config.MEDIA_INBOX, "script_%d_shot_*" % old)):
            nf = f.replace("script_%d_shot_" % old, "script_%d_shot_" % new)
            os.rename(f, nf)
            print("   ↳ %s → %s" % (os.path.basename(f), os.path.basename(nf)))
        v = os.path.join(config.VOICE_INBOX, "script_%d.mp3" % old)
        if os.path.exists(v):
            nv = os.path.join(config.VOICE_INBOX, "script_%d.mp3" % new)
            os.rename(v, nv)
            print("   ↳ voix %s → %s" % (os.path.basename(v), os.path.basename(nv)))
    # manifest des provenances
    man_path = os.path.join(config.MEDIA_INBOX, "assets_manifest.json")
    if os.path.exists(man_path):
        man = json.load(open(man_path))
        newman = {}
        for k, v in man.items():
            nk = k
            for old, new in mapping.items():
                nk = nk.replace("script_%d_" % old, "script_%d_" % new)
            newman[nk] = v
        json.dump(newman, open(man_path, "w"), ensure_ascii=False, indent=2)

    print("6/6 production (ASSETS→VOICE→RENDER→QA→finalize)…")
    finals = []
    for p in plan:
        print("   ▶ script %d…" % p["script_id"], flush=True)
        res = produce(p["script_id"])
        print("     " + json.dumps(res, ensure_ascii=False)[:400])
        if res.get("final", {}).get("ok"):
            finals.append(res["final"]["name"])
    print("\n=== RÉSULTAT : %s ===" % (", ".join(finals) if finals else "aucune vidéo finalisée"))
    print(json.dumps({"videos": finals}, ensure_ascii=False))
    sys.exit(0 if len(finals) == len(plan) else 2)


if __name__ == "__main__":
    main()
