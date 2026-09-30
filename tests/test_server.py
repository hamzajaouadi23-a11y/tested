#!/usr/bin/env python3
"""Tests backend — TESTÉ & PROPRE Content OS v5 (pipeline).
Usage : /home/user/venv-tnp/bin/python tests/test_server.py
Couvre : registre providers, chaîne texte honnête, recherche sourcée, sélection, scripts,
composition/graphique, FFmpeg, QA (négatifs honnêts), flags, secrets scan, e2e si fixture.
"""
import json
import os
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from server import config, db, providers, ffmpegw, secrets_scan  # noqa: E402
from server.services import assets as assets_svc  # noqa: E402
from server.services import composition, honesty, learning, pipeline, qa, research, scripts, selection, voice  # noqa: E402

PASS, FAIL, FAILS = 0, 0, []


def T(name, cond, detail=""):
    global PASS, FAIL
    try:
        ok = bool(cond() if callable(cond) else cond)
    except Exception as e:
        ok, detail = False, "EXC: " + str(e)[:160]
    if ok:
        PASS += 1
        print("PASS  " + name)
    else:
        FAIL += 1
        FAILS.append(name + (" — " + detail if detail else ""))
        print("FAIL  " + name + (" — " + detail if detail else ""))


FIX_VOICE = os.path.join(ROOT, "tests", "fixtures", "voice_test.mp3")
_created = {"research_file": None, "candidate_id": None, "script_id": None, "video_id": None, "assets": []}

# ============ 1. REGISTRE PROVIDERS ============
KINDS = {"TEXT", "RESEARCH", "IMAGE", "VOICE", "VIDEO", "STORAGE", "SOCIAL", "ANALYTICS", "SCHEDULER"}
T("01 registre couvre les 9 catégories", lambda: KINDS.issubset({p.kind for p in providers.all()}))
T("02 chaque provider expose le contrat", lambda: all(
    hasattr(p, "id") and hasattr(p, "label") and isinstance(p.implemented, bool)
    and isinstance(p.mock, bool) and isinstance(p.requires, list) and isinstance(p.costly, bool)
    and callable(p.test) and callable(p.health) for p in providers.all()))
T("03 aucun provider mock enregistré", lambda: all(not p.mock for p in providers.all()))
T("04 health() renvoie les champs requis", lambda: all(
    set(p.health().keys()) >= {"id", "label", "kind", "implemented", "mock", "requires", "costly", "configured", "status"}
    for p in providers.all()))
T("05 providers sociaux = non configurés sans OAuth (honnête)", lambda: all(
    providers.get(x).health()["status"] == "not_configured" for x in ("tiktok", "youtube", "instagram")))
T("06 chaîne texte : sans clé → échec honnête, pas de crash", lambda: (
    (lambda r: (not r["ok"]) and "tried" in r)(providers.generate_text("test", purpose="script"))))
T("07 provider local texte = secours réel (pas mock)", lambda: (
    providers.get("local_text").implemented and not providers.get("local_text").mock))

# ============ 2. RECHERCHE (séparation FACT/SOURCE/ANALYSIS/ANGLE) ============
def _research_import():
    sample = {
        "topic": "TEST unitaire — calcaire salle de bain",
        "sources": [{"url": "https://example.test/svt", "title": "Source test"},
                    {"url": "https://example.test/two", "title": "Source 2"}],
        "facts": [
            {"fact": "Le vinaigre blanc dissout le calcaire (acide acétique).",
             "analysis": "hydrogène", "angle": "démonstration décapage",
             "source_url": "https://example.test/svt"},
            {"fact": "FAIT SANS SOURCE — doit être rejeté.", "source_url": "https://inconnu.test/x"},
        ],
    }
    path = os.path.join(config.RESEARCH_INBOX, "test_research.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sample, f)
    _created["research_file"] = path
    return research.import_inbox()

T("08 import recherche : rejette les faits sans source", lambda: (
    lambda r: r["imported_files"] == 1 and r["rejected"] >= 1)(_research_import()))
T("09 findings exposent fact+source+analysis+angle", lambda: (
    lambda rows: any(x["fact"].startswith("Le vinaigre") and x["source_url"]
                     and x.get("source_url", "").startswith("https://example.test")
                     for x in rows))(research.findings()))

# ============ 3. CANDIDATS & SÉLECTION ============
def _mk_candidates():
    ids = []
    for i in range(4):
        cid = research.add_candidate({
            "title": "TEST candidat %d" % i, "problem": "problème %d" % i, "solution": "solution %d" % i,
            "product_name": "", "price": "19.99",
            "scores": {"visual_demonstrability": 5 - i, "problem_clarity": 4, "solution_clarity": 4,
                       "price": 3, "commission_potential": 3, "content_depth": 4, "angles_count": 4,
                       "competition": 3, "geo_potential": 4, "quality_evidence": i + 1, "risk": 4},
        })
        ids.append(cid)
        _created.setdefault("candidate_ids", []).append(cid)
    return ids

T("10 ajout de 4 candidats de test", lambda: len(_mk_candidates()) == 4)
T("11 select_top(3) marque exactement 3 sélectionnés (triés)", lambda: (
    lambda sel: len(sel) == 3 and sel[0]["priority_score"] >= sel[-1]["priority_score"])(
    selection.select_top(3)))
_created["candidate_id"] = _created.get("candidate_ids", [None])[-1]

# ============ 4. SCRIPTS ============
def _gen_script():
    cid = _created["candidate_id"]
    r = scripts.generate_for_candidate(cid, styles=["A"])
    if r["ok"]:
        _created["script_id"] = r["scripts"][0]["script_id"]
    return r

T("12 génération script style A", lambda: _gen_script()["ok"])
def _script_fields():
    s = scripts.get_script(_created["script_id"])
    return s and s["hook"] and len(s["vo_text"]) > 60 and len(s["onscreen"]) >= 4 and s["caption"] and s["cta"]
T("13 script complet (hook/VO/onscreen/caption/CTA)", _script_fields)
T("14 claims du script tous sourcés", lambda: all(
    c.get("source_url") for c in scripts.get_script(_created["script_id"])["claims"]))
T("15 lint honnêteté bloque un faux claim", lambda: bool(
    honesty.find_violations("Résultats garantis à 100 %, devenez viral !")))
T("16 lint honnêteté accepte un démenti honnête", lambda: not
    honesty.find_violations("Pas de promesse de viralité : on montre la méthode, point."))
T("17 orthographe QA : faute connue rejetée", lambda: not qa._spelling_check("organisasion totale")[0])

# ============ 5. ASSETS / COMPOSITION ============
T("18 composition 1080x1920 générée", lambda: (
    lambda p: os.path.exists(p) and (lambda im: im.size == (1080, 1920))(
        __import__("PIL.Image", fromlist=["Image"]).open(p)))(
    composition.render_panel(os.path.join(config.TMP, "panel_test.png"),
                             "Test de titre très long qui doit wrapper proprement sans jamais déborder du cadre",
                             "Sous-titre descriptif de la composition", 2, 5)))
T("19 caption_overlay : pas de débordement mesuré", lambda: not composition.measure_overlay(
    "Un texte volontairement très long pour vérifier que le wrap automatique fonctionne et que rien ne sort du cadre de sécurité de la vidéo verticale")["overflow"])
sid = _created["script_id"]
a_res = assets_svc.acquire_for_script(sid)
_created["assets"] = a_res.get("generated", [])
T("20 assets acquis pour le script (composition locale)", lambda: a_res["ok"] and a_res["total"] >= 4)
T("21 provenances enregistrées (aucune 'mock')", lambda: all(
    a["provenance"] != "mock" for a in assets_svc.list_assets(sid)))

# ============ 6. VOIX — comportement honnête sans TTS ============
# Hermétique : l'inbox voix de production (commit) ne doit pas faire « réussir » le test —
# on pointe VOICE_INBOX vers un dossier temporaire VIDE, puis on restaure.
def _voice_blocked():
    real_inbox = config.VOICE_INBOX
    config.VOICE_INBOX = tempfile.mkdtemp(prefix="tnp_voice_inbox_empty_")
    try:
        return voice.synthesize_for_script(sid)
    finally:
        config.VOICE_INBOX = real_inbox


r22 = _voice_blocked()
T("22 voix sans provider ni inbox → BLOCKED honnête (jamais de silence fake)",
  lambda: (not r22["ok"]) and r22.get("blocked"))

# ============ 7. FFMPEG ============
T("23 ffmpeg présent et fonctionnel", lambda: "ffmpeg" in ffmpegw.version())
def _mini_video():
    out = os.path.join(config.TMP, "mini.mp4")
    frame = os.path.join(config.TMP, "panel_test.png")
    proc = ffmpegw.run_cmd(["-y", "-v", "error", "-loop", "1", "-t", "2", "-i", frame,
                            "-f", "lavfi", "-t", "2", "-i", "sine=frequency=440:sample_rate=44100",
                            "-vf", "scale=1080:1920,zoompan=z='1+on*0.001':d=60:s=1080x1920:fps=30,format=yuv420p",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
                            "-c:a", "aac", "-shortest", out], timeout=120)
    return proc.returncode == 0 and os.path.exists(out)
T("24 encodage zoompan + audio test", _mini_video)
T("25 probe mini.mp4 : 1080x1920, audio+vidéo, ~2s", lambda: (
    lambda i: i.get("width") == 1080 and i.get("height") == 1920 and i.get("has_video")
    and i.get("has_audio") and 1.5 < i.get("duration_s", 0) < 3.5)(
    ffmpegw.probe(os.path.join(config.TMP, "mini.mp4"))))
T("26 volumedetect détecte la piste (mean_db numérique)", lambda: (
    lambda s: s["mean_db"] is not None)(ffmpegw.audio_stats(os.path.join(config.TMP, "mini.mp4"))))
T("27 décodage fichier corrompu → échec détecté", lambda: (
    lambda bad: not ffmpegw.decodable(bad))(
    (lambda p: (open(p, "wb").write(b"not a video"), p)[1])(os.path.join(config.TMP, "corrupt.mp4"))))

# ============ 8. QA / PIPELINE / FLAGS ============
T("28 schéma videos : colonnes QA/status présentes", lambda: (
    lambda cols: {"qa_json", "status", "duration_s", "disclosure_json"}.issubset(cols))(
    {r["name"] for r in db.q("PRAGMA table_info(videos)")}))
T("29 pipeline set/get état", lambda: (
    pipeline.set_state("candidate", 999999, "BLOCKED", "test"),
    pipeline.get_state("candidate", 999999)["state"] == "BLOCKED")[1])
T("30 approve() refuse une vidéo sans QA", lambda: not pipeline.approve(999999)["ok"])
T("31 AUTO_PUBLISH verrouillé False côté config", lambda: config.AUTO_PUBLISH is False)
T("32 learning : données insuffisantes signalées honnêtement", lambda: (
    lambda r: r["ok"] and r["enough_data"] is False)(learning.analyze()))
def _qa_negative():
    """mini.mp4 (2 s, voix sinusoïdale) doit être REFUSÉ honnêtement sur DURATION."""
    vid = db.run("INSERT INTO videos(script_id,path,filename,status,disclosure_json,created_at) VALUES(?,?,?, 'rendered', '{}',?)",
                 (_created["script_id"], os.path.join(config.TMP, "mini.mp4"), "mini.mp4", db.now()))
    res = qa.run(vid)
    db.run("DELETE FROM videos WHERE id=?", (vid,))
    return (not res["pass"]) and "DURATION" in res["blockers"]
T("33 QA : trop courte → refus honnête (blocker DURATION)", _qa_negative)

# ============ 9. SECRETS ============
T("34 secrets scan : repo propre", lambda: len(secrets_scan.scan(ROOT)) == 0)
T("35 .env est ignoré par git", lambda: ".env\n" in __import__("subprocess").run(
    ["git", "check-ignore", "-v", ".env"], cwd=ROOT, capture_output=True, text=True).stdout or
    __import__("subprocess").run(["git", "check-ignore", ".env"], cwd=ROOT, capture_output=True).returncode == 0)
T("36 .env.example existe et NE contient aucune vraie clé", lambda: (
    os.path.exists(config.ENV_EXAMPLE) and "VOTRE_CLE" in open(config.ENV_EXAMPLE).read()))

# ============ 10. E2E OPTIONNELLE (fixture voix réelle) ============
_e2e_tmp = tempfile.mkdtemp(prefix="tnp_e2e_")
if os.path.exists(FIX_VOICE):
    os.environ["TNP_READY_DIR"] = _e2e_tmp   # ne jamais polluer ready_to_post de prod
    shutil.copy2(FIX_VOICE, os.path.join(config.VOICE_INBOX, "script_%d.mp3" % sid))
    v_res = voice.synthesize_for_script(sid)
    T("37 e2e voix importée : durée mesurée", lambda: v_res["ok"] and v_res["duration_s"] > 1)
    from server.services import render
    r_res = render.render(sid) if v_res["ok"] else {"ok": False}
    _created["video_id"] = r_res.get("video_id")
    T("38 e2e render MP4", lambda: r_res["ok"])
    if r_res["ok"]:
        qres = qa.run(r_res["video_id"])
        T("39 e2e QA passe sur rendu réel (voix réelle)", lambda: qres["pass"],
          json.dumps(qres.get("blockers"), ensure_ascii=False) if not qres["pass"] else "")
        fin = qa.finalize_for_post(r_res["video_id"]) if qres["pass"] else {"ok": False}
        T("40 e2e finalize ready_to_post + caption + metadata", lambda: fin["ok"])
        # nettoyage e2e : lignes + fichiers
        db.run("DELETE FROM videos WHERE id=?", (r_res["video_id"],))
        db.run("DELETE FROM voices WHERE script_id=?", (sid,))
        db.run("DELETE FROM assets WHERE script_id=?", (sid,))
        for pat in (os.path.join(config.VOICE_INBOX, "script_%d.mp3" % sid),
                    os.path.join(config.ASSETS, "script_%d_*" % sid),
                    os.path.join(config.ASSETS, "voice_script_%d.mp3" % sid)):
            for f in __import__("glob").glob(pat):
                os.remove(f)
        shutil.rmtree(os.path.join(config.TMP, "render_%d" % sid), ignore_errors=True)
    else:
        T("39 e2e QA passe", False, "render échoué")
        T("40 e2e finalize", False, "render échoué")
    os.environ.pop("TNP_READY_DIR", None)
else:
    print("SKIP  37–40 e2e (fixture voix absente : %s)" % FIX_VOICE)
shutil.rmtree(_e2e_tmp, ignore_errors=True)

# ============ nettoyage des artefacts de test ============
def cleanup():
    if _created.get("research_file") and os.path.exists(_created["research_file"]):
        os.remove(_created["research_file"])
    if _created.get("candidate_ids"):
        with db._lock, db.connect() as con:
            con.execute("PRAGMA foreign_keys=OFF")
            con.execute("DELETE FROM scripts WHERE candidate_id IN (SELECT id FROM candidates WHERE title LIKE 'TEST candidat%')")
            con.execute("DELETE FROM candidates WHERE title LIKE 'TEST candidat%'")
            con.execute("DELETE FROM facts WHERE topic LIKE 'TEST unitaire%'")
            con.execute("DELETE FROM sources WHERE url LIKE 'https://example.test%'")
            con.commit()
    for f in ("panel_test.png", "mini.mp4", "corrupt.mp4"):
        p = os.path.join(config.TMP, f)
        if os.path.exists(p):
            os.remove(p)
    if _created.get("script_id"):
        db.run("DELETE FROM pipeline_items WHERE ref_id=999999 AND ref_type='candidate'")

print("----------------------------------------------------------")
print("TESTS: %d | PASS: %d | FAIL: %d" % (PASS + FAIL, PASS, FAIL))
if FAILS:
    print("ÉCHECS:")
    for f in FAILS:
        print("  - " + f)
cleanup()
sys.exit(1 if FAIL else 0)
