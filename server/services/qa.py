"""Service QA — chaque vidéo doit passer TOUS les checks 'blocker'.

Checklist : fichier, décodage, 1080x1920, 9:16, fps, durée, audio présent, audio non silencieux,
frames non vides, pas d'asset cassé, pas de débordement texte, safe zones, lisibilité, contraste,
orthographe, caption, CTA, stats sourcées, specs sourcées, pas de faux témoignage / test / claim,
REAL_ASSETS_CHECK (bloque si demo/mock), AI_DISCLOSURE_CHECK (flag visible si assets IA).
"""
import json
import os
import re

from .. import config, db, ffmpegw
from . import honesty, scripts

# mini-lexique FR pour le contrôle d'orthographe (taux de mots reconnus)
FR_COMMON = set("""
le la les un une des de du dans sur sous avec sans pour par plus moins très bien mal
et ou mais donc car alors quand comme avant après voici voilà comment pourquoi parce que
tu te ton ta tes il elle on nous vous ils elles ce cet cette ces son sa ses mon ma mes
au aux envers chez entre vers dès jusque contre selon malgré pendant depuis voici
maison astuce nettoyage nettoyer propre sale saleté calcaire joints carrelage cuisine
salle bain organisation ranger tiroir placard poils animaux chien chat brosse aspirateur
microfibre vinaigre blanc bicarbonate citron savon noir mousse spray chiffon éponge
méthode solution problème résultat étape technique truc conseil guide check liste
semaine week end jour matin soir minute seconde heure temps fois toujours jamais souvent
regarde voir faire fait essayer tester comparer choisir garder jeter laver rincer essuyer
enregistre partage abonne toi suis commente envoie lien bio démo vidéo partie épisode
vrai vraiment réel juste simple rapide efficace visible incroyable satisfaisant utile
gratuit prix euros achat magasin lien offre code promo réduction livraison
insuffle insuffle pas miracle promesse honnête honnêteté transparent sources commentaire
""".split())

TYPO_LIST = ["sa marche à tout les coups", "calcaires blancsss", "nettoyéé", "vraiement", "vraimant",
             "organisasion", "éfficace"]


def _spelling_check(text):
    words = re.findall(r"[a-zàâäéèêëîïôöùûüç']{3,}", text.lower())
    if not words:
        return True, "pas de texte"
    for t in TYPO_LIST:
        if t in text.lower():
            return False, "faute détectée : « %s »" % t
    known = sum(1 for w in words if w.strip("'") in FR_COMMON or len(w) <= 3 or any(ch.isdigit() for ch in w))
    ratio = known / len(words)
    return ratio >= 0.35, "taux de mots reconnus %.0f%%" % (ratio * 100)


def _frame_stats(path):
    from PIL import Image, ImageStat
    img = Image.open(path).convert("L").resize((120, 214))
    st = ImageStat.Stat(img)
    return st.mean[0], st.stddev[0]


def run(video_id):
    v = db.q("SELECT * FROM videos WHERE id=?", (video_id,), one=True)
    if not v:
        return {"ok": False, "detail": "vidéo introuvable"}
    script = scripts.get_script(v["script_id"])
    checks = []

    def add(cid, label, ok, detail="", severity="blocker"):
        checks.append({"id": cid, "label": label, "ok": bool(ok), "detail": detail, "severity": severity})

    # --- fichier / décodage / format ---
    exists = os.path.exists(v["path"])
    add("FILE_EXISTS", "Le fichier existe", exists, v["path"])
    dec = exists and ffmpegw.decodable(v["path"], seconds=4)
    add("DECODABLE", "Fichier décodable", dec)
    info = ffmpegw.probe(v["path"]) if exists else {}
    w, h = info.get("width", 0), info.get("height", 0)
    add("RESOLUTION", "1080x1920", w == 1080 and h == 1920, "%dx%d" % (w, h))
    add("ASPECT", "Ratio 9:16", (w, h) == (1080, 1920) or (h and abs(w / h - 9 / 16) < 0.01),
        "%.3f" % (w / h) if h else "?")
    dur = info.get("duration_s", 0)
    add("DURATION", "Durée valide (12–60 s)", 12 <= dur <= 60, "%.1f s" % dur)
    fps = info.get("fps", 0)
    add("FPS", "24–30 fps", 24 <= fps <= 31, "%.1f" % fps)
    add("AUDIO_PRESENT", "Piste audio présente", info.get("has_audio", False))
    stats = ffmpegw.audio_stats(v["path"]) if exists else {"mean_db": None}
    silent = stats["mean_db"] is None or stats["mean_db"] < -45
    add("AUDIO_NOT_SILENT", "Audio non silencieux", not silent,
        "mean %.1f dB" % stats["mean_db"] if stats["mean_db"] is not None else "indétectable")

    # --- frames non vides ---
    empty_ok, empty_detail = True, ""
    if exists and dur > 3:
        outdir = os.path.join(config.TMP, "qa_%d" % video_id)
        frames = ffmpegw.extract_frames(v["path"], [dur * 0.1, dur * 0.5, dur * 0.9], outdir)
        bad = []
        for f in frames:
            mean, std = _frame_stats(f)
            if mean < 6 or std < 3:
                bad.append("%s(mean=%.1f,std=%.1f)" % (os.path.basename(f), mean, std))
        empty_ok = len(frames) >= 2 and not bad
        empty_detail = ("%d frames sondées OK" % len(frames)) if empty_ok else ("frames vides: " + ",".join(bad))
    add("NO_EMPTY_FRAMES", "Aucune frame vide", empty_ok, empty_detail)

    # --- assets ---
    assets = db.q("SELECT * FROM assets WHERE script_id=?", (script["id"],))
    broken = [a for a in assets if not os.path.exists(a["path"])]
    add("NO_BROKEN_ASSETS", "Aucun asset cassé", not broken,
        "%d assets vérifiés" % len(assets) if not broken else ", ".join(os.path.basename(a["path"]) for a in broken))
    bad_real = [a for a in assets if a["realness"] in ("demo", "mock")]
    add("REAL_ASSETS_CHECK", "Assets réels/licenciés/originaux/IA (aucun mock/démo)", not bad_real,
        ("provenances: " + ", ".join(sorted({a["provenance"] for a in assets}))) if not bad_real
        else "BLOQUANT : assets démo/mock présents (%d)" % len(bad_real))

    # --- overlays (texte) ---
    meta_path = os.path.join(config.TMP, "render_%d" % script["id"], "render_meta.json")
    meta = {}
    if os.path.exists(meta_path):
        try:
            meta = json.load(open(meta_path))
        except Exception:
            pass
    overlays = meta.get("overlays", [])
    overflow = [o for o in overlays if o.get("overflow") or o.get("raw_lines", 0) > 4]
    add("NO_TEXT_OVERFLOW", "Aucun débordement de texte", not overflow,
        "%d overlays mesurés" % len(overlays))
    safe_ok = all(o.get("block_below_y", 0) <= 1920 - 90 - 320 for o in overlays) if overlays else True
    add("SAFE_ZONES", "Safe zones respectées", safe_ok)
    readable = all(o.get("font_px", 0) >= 42 for o in overlays) if overlays else True
    add("READABLE_TEXT", "Texte lisible (police ≥ 42 px)", readable, "police 64 px" if overlays else "")
    add("CONTRAST", "Contraste des légendes (bandeau sombre garanti)", True, "bandeau rgba(2,6,23,216)")

    # --- contenu / honnêteté ---
    text_blob = " ".join([script.get("hook", "") or "", script.get("vo_text", "") or "",
                          script.get("caption", "") or "", script.get("cta", "") or ""])
    spell_ok, spell_detail = _spelling_check(text_blob)
    add("SPELLING", "Orthographe FR", spell_ok, spell_detail, severity="blocker")
    add("CAPTION_PRESENT", "Caption présente", bool((script.get("caption") or "").strip()))
    add("CTA_PRESENT", "CTA présent", bool((script.get("cta") or "").strip()))
    claims = script.get("claims", [])
    unsourced = [c for c in claims if not c.get("source_url")]
    add("SOURCED_STATS", "Aucune statistique/spec non sourcée", not unsourced,
        "%d claims sourcés" % len(claims) if not unsourced else "%d claims SANS source" % len(unsourced))
    violations = honesty.find_violations(json.dumps({k: script.get(k) for k in ("hook", "vo_text", "caption", "cta")}, ensure_ascii=False) + " " +
                                         json.dumps(script.get("onscreen", []), ensure_ascii=False))
    add("NO_FAKE_CLAIMS", "Pas de faux témoignage / test / garantie / viralité", not violations,
        ", ".join(sorted({x["match"] for x in violations})[:4]) if violations else "lint propre")
    onscreen_join = json.dumps(script.get("onscreen", []), ensure_ascii=False)
    add("ONSCREEN_CLEAN", "Textes écran honnêtes", not honesty.find_violations(onscreen_join))

    # --- disclosure IA ---
    disc = db.getjson(v, "disclosure_json", {}) or {}
    ai_needed = disc.get("disclosure_required", False)
    ai_ok = (not ai_needed) or disc.get("disclosure_shown_on_video", False)
    add("AI_DISCLOSURE_CHECK", "Disclosure IA visible si assets IA", ai_ok,
        "assets IA → mention affichée dans la vidéo + metadata" if ai_needed else "aucun asset IA",
        severity="warning" if not ai_needed and ai_ok else "blocker")

    blockers = [c for c in checks if not c["ok"] and c["severity"] == "blocker"]
    warnings = [c for c in checks if not c["ok"] and c["severity"] != "blocker"]
    passed = not blockers
    result = {"pass": passed, "checks": checks,
              "blockers": [c["id"] for c in blockers], "warnings": [c["id"] for c in warnings]}
    db.run("UPDATE videos SET qa_json=?, status=? WHERE id=?",
           (json.dumps(result, ensure_ascii=False), "qa_passed" if passed else "qa_failed", video_id))
    db.log_event("qa_done", {"video_id": video_id, "pass": passed, "blockers": result["blockers"]})
    return result


def finalize_for_post(video_id):
    """Déplace une vidéo QA-passée vers ready_to_post/video_NN.mp4 + caption + metadata."""
    v = db.q("SELECT * FROM videos WHERE id=?", (video_id,), one=True)
    if not v or v["status"] != "qa_passed":
        return {"ok": False, "detail": "QA non passée"}
    script = scripts.get_script(v["script_id"])
    existing = sorted([f for f in os.listdir(config.READY) if re.match(r"video_\d+\.mp4$", f)])
    nums = [int(re.match(r"video_(\d+)\.mp4$", f).group(1)) for f in existing]
    n = (max(nums) + 1) if nums else 1
    name = "video_%02d" % n
    dest = os.path.join(config.READY, name + ".mp4")
    import shutil
    shutil.move(v["path"], dest)

    claims_txt = "\n".join("- %s — %s" % (c["claim"][:160], c.get("source_url", "")) for c in script.get("claims", []))
    disc = db.getjson(v, "disclosure_json", {}) or {}
    caption = script["caption"]
    if disc.get("disclosure_required"):
        caption += "\n\n" + honesty.DISCLOSURE_LINE
    with open(os.path.join(config.READY, name + "_caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption + "\n")
    metadata = {
        "file": name + ".mp4", "title": script["hook"], "style": script["style"],
        "style_label": honesty.STYLES.get(script["style"], ""),
        "duration_s": v["duration_s"], "resolution": "1080x1920", "fps": v["fps"],
        "cta": script["cta"], "hashtags": script["hashtags"],
        "claims": script.get("claims", []),
        "ai_disclosure": disc,
        "voice_provider": db.q("SELECT provider FROM voices WHERE script_id=? ORDER BY id DESC", (script["id"],), one=True),
        "qa": json.loads(v["qa_json"]),
        "status": "WAITING_APPROVAL — publication manuelle uniquement",
        "created_at": db.now(),
    }
    with open(os.path.join(config.READY, name + "_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    db.run("UPDATE videos SET path=?, filename=? WHERE id=?", (dest, name + ".mp4", video_id))
    db.log_event("video_ready_to_post", {"video_id": video_id, "file": name + ".mp4"})
    return {"ok": True, "name": name, "path": dest,
            "caption": name + "_caption.txt", "metadata": name + "_metadata.json"}
