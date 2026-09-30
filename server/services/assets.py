"""Service ASSETS — provenance TOUJOURS déclarée :
user (opérateur) > licensed > original > ai > composition. Jamais de média scrapé.

- Les fichiers opérateur se déposent dans data/media/inbox/ + assets_manifest.json :
  {"script_12_shot_1.png": {"provenance": "user|licensed|original|ai|demo", "license": "...", "note": "..."}}
- Les shots manquants : génération IA si configurée, sinon composition graphique locale (réel).
- Un asset 'demo'/'mock' bloquera la QA production (REAL_ASSETS_CHECK).
"""
import glob
import json
import os
import shutil

from .. import config, db, providers

VALID_PROVENANCE = {"user", "licensed", "original", "ai", "composition"}
REALNESS = {"user": "real", "licensed": "real", "original": "real", "ai": "ai", "composition": "composition"}


def load_manifest():
    path = os.path.join(config.MEDIA_INBOX, "assets_manifest.json")
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _provenance_for(filename, manifest):
    info = manifest.get(filename, {})
    prov = info.get("provenance", "user")
    if prov in ("demo", "mock"):
        return prov, prov, info
    if prov not in VALID_PROVENANCE:
        prov = "user"
    return prov, REALNESS[prov], info


def import_inbox_for_script(script_id):
    """Importe les fichiers script_<id>_shot_<i>.(png|jpg|jpeg|webp|mp4) depuis l'inbox."""
    manifest = load_manifest()
    imported = []
    patterns = [os.path.join(config.MEDIA_INBOX, "script_%d_shot_*.png" % script_id),
                os.path.join(config.MEDIA_INBOX, "script_%d_shot_*.jpg" % script_id),
                os.path.join(config.MEDIA_INBOX, "script_%d_shot_*.jpeg" % script_id),
                os.path.join(config.MEDIA_INBOX, "script_%d_shot_*.webp" % script_id),
                os.path.join(config.MEDIA_INBOX, "script_%d_shot_*.mp4" % script_id)]
    files = sorted({f for p in patterns for f in glob.glob(p)})
    for f in files:
        base = os.path.basename(f)
        prov, realness, info = _provenance_for(base, manifest)
        dest = os.path.join(config.ASSETS, base)
        existing = db.q("SELECT id FROM assets WHERE script_id=? AND path=?", (script_id, dest), one=True)
        if existing:
            continue  # idempotent : ne pas dupliquer un asset déjà importé
        shutil.copy2(f, dest)
        aid = db.run("INSERT INTO assets(script_id,path,kind,provenance,license,realness,note,created_at) VALUES(?,?,?,?,?,?,?,?)",
                     (script_id, dest, "video" if base.endswith(".mp4") else "image", prov,
                      info.get("license", ""), realness, info.get("note", ""), db.now()))
        imported.append({"asset_id": aid, "file": base, "provenance": prov, "realness": realness})
        db.log_event("asset_imported", imported[-1])
    return imported


def _ensure_module_pil():
    import PIL  # noqa
    return True


def generate_missing(script, present_count):
    """Génère les shots manquants : IA (si configurée) puis composition locale (toujours)."""
    sid = script["id"]
    shots = script["shotlist"]
    made = []
    img_provider = providers.get("image_gemini")
    comp = providers.get("composition")
    for i, shot in enumerate(shots, start=1):
        existing = db.q("SELECT id FROM assets WHERE script_id=? AND path LIKE ?",
                        (sid, "%%shot_%d.%%" % i), one=True)
        if existing:
            continue
        prompt = "Photorealistic vertical photo, household context: " + shot["visual"]
        out = os.path.join(config.ASSETS, "script_%d_shot_%d.png" % (sid, i))
        done = False
        if img_provider.configured():
            r = img_provider.generate(prompt, out)
            if r["ok"]:
                db.run("INSERT INTO assets(script_id,path,kind,provenance,license,realness,note,created_at) VALUES(?,?,?,?,?,?,?,?)",
                       (sid, out, "image", "ai", "", "ai", "prompt: " + shot["visual"][:160], db.now()))
                made.append({"shot": i, "provenance": "ai"})
                done = True
        if not done and comp.test()["ok"]:
            from . import composition
            path = composition.render_panel(out, title=script["hook"], subtitle=shot["visual"], index=i, total=len(shots))
            db.run("INSERT INTO assets(script_id,path,kind,provenance,license,realness,note,created_at) VALUES(?,?,?,?,?,?,?,?)",
                   (sid, path, "image", "composition", "", "composition", "panneau graphique local", db.now()))
            made.append({"shot": i, "provenance": "composition"})
    return made


def acquire_for_script(script_id):
    from . import scripts
    script = scripts.get_script(script_id)
    if not script:
        return {"ok": False, "detail": "script introuvable"}
    imported = import_inbox_for_script(script_id)
    made = generate_missing(script, len(imported))
    rows = [dict(r) for r in db.q("SELECT * FROM assets WHERE script_id=? ORDER BY id", (script_id,))]
    # résumé du provider image employé (traçabilité fallback — visible dans les événements)
    counts = {"user": 0, "licensed": 0, "original": 0, "ai": 0, "composition": 0}
    for r in rows:
        if r["provenance"] in counts:
            counts[r["provenance"]] += 1
    if counts["ai"]:
        image_provider = "image_gemini"
    elif counts["user"] or counts["licensed"] or counts["original"]:
        image_provider = "image_import"
    elif rows:
        image_provider = "composition"
    else:
        image_provider = None
    fallback = image_provider not in (None, "image_gemini")  # tête de chaîne = cloud
    summary = {"image_provider_used": image_provider, "image_fallback": fallback,
               "provenance_counts": {k: v for k, v in counts.items() if v}}
    db.log_event("assets_ready", {"script_id": script_id, "imported": len(imported),
                                  "generated": len(made), **summary})
    return {"ok": True, "imported": imported, "generated": made, "total": len(rows),
            "realness": sorted({r["realness"] for r in rows}), **summary}


def list_assets(script_id):
    return [dict(r) for r in db.q("SELECT * FROM assets WHERE script_id=? ORDER BY id", (script_id,))]
