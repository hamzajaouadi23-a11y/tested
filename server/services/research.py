"""Service RECHERCHE — sépare toujours FACT / SOURCE / ANALYSIS / ANGLE.

Règles :
- Chaque fait DOIT référencer une source (url + titre + date de récupération). Sans source : rejeté.
- Jamais de statistique inventée. Les analyses sont des interprétations, pas des faits.
- Deux moteurs : import opérateur (data/research/inbox/*.json) et Gemini grounding (si clé).
"""
import json
import os
import shutil
import time

from .. import config, db, providers

QUERIES_NICHE = [
    "problèmes maison les plus recherchés 2026 nettoyage",
    "tendances TikTok nettoyage #cleantok 2026",
    "produits maison viraux démonstration visuelle 2026",
    "poils d'animaux solutions maison avis",
    "organisation cuisine petits espaces tendances",
    "appareils ménagers utiles meilleures ventes 2026",
]

REQUIRED_KEYS = ("topic", "sources", "facts")


def _valid_fact(f, source_urls):
    return (isinstance(f, dict) and f.get("fact") and f.get("source_url")
            and f["source_url"] in source_urls)


def import_inbox():
    """Importe data/research/inbox/*.json. Chaque fait sans URL de source connue est rejeté."""
    import glob
    imported, rejected, runs = 0, 0, []
    for path in sorted(glob.glob(os.path.join(config.RESEARCH_INBOX, "*.json"))):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            rejected += 1
            db.log_event("research_import_error", {"file": os.path.basename(path), "error": str(e)[:200]})
            continue
        if not all(k in data for k in REQUIRED_KEYS):
            rejected += 1
            db.log_event("research_import_error", {"file": os.path.basename(path), "error": "clés requises manquantes"})
            continue
        run_id = db.run("INSERT INTO research_runs(provider,niche,status,queries_json,notes,created_at) VALUES(?,?,?,?,?,?)",
                        ("research_import", data.get("niche", config.NICHE), "done",
                         json.dumps(data.get("queries", [])), "import " + os.path.basename(path), db.now()))
        src_ids = {}
        for s in data["sources"]:
            if not s.get("url"):
                continue
            sid = db.run("INSERT INTO sources(url,title,publisher,retrieved_at) VALUES(?,?,?,?)",
                         (s["url"], s.get("title", ""), s.get("publisher", ""),
                          s.get("retrieved_at", db.now())))
            src_ids[s["url"]] = sid
        n_facts = 0
        for f in data["facts"]:
            if not _valid_fact(f, src_ids):
                rejected += 1
                continue
            db.run("INSERT INTO facts(run_id,source_id,topic,fact,analysis,angle,created_at) VALUES(?,?,?,?,?,?,?)",
                   (run_id, src_ids[f["source_url"]], data.get("topic", ""), f["fact"],
                    f.get("analysis", ""), f.get("angle", ""), db.now()))
            n_facts += 1
        imported += 1
        for c in data.get("candidates", []):
            add_candidate(c, run_id=run_id)
        done_dir = os.path.join(config.RESEARCH, "processed")
        os.makedirs(done_dir, exist_ok=True)
        shutil.move(path, os.path.join(done_dir, time.strftime("%Y%m%d-%H%M%S-") + os.path.basename(path)))
        db.log_event("research_imported", {"file": os.path.basename(path), "facts": n_facts, "run_id": run_id})
        runs.append({"run_id": run_id, "facts": n_facts, "file": os.path.basename(path)})
    return {"ok": True, "imported_files": imported, "rejected": rejected, "runs": runs}


def add_candidate(c, run_id=None):
    required = ("title", "problem", "solution")
    if not all(c.get(k) for k in required):
        return None
    return db.run(
        "INSERT INTO candidates(run_id,title,niche,problem,solution,product_name,product_url,price,scores_json,risk,status,created_at)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,'proposed',?)",
        (run_id, c["title"], c.get("niche", config.NICHE), c["problem"], c["solution"],
         c.get("product_name", ""), c.get("product_url", ""), c.get("price", ""),
         json.dumps(c.get("scores", {}), ensure_ascii=False), c.get("risk", ""), db.now()))


def run_gemini_research():
    """Recherche live via Gemini + grounding (si clé configurée). Parse un JSON strict."""
    if not providers.get("research_gemini").configured():
        return {"ok": False, "detail": "GEMINI_API_KEY non configurée — utiliser l'import inbox"}
    prompt = (
        "Tu es un analyste de contenu short-form. Recherche ACTUELLE (2026) sur la niche : produits/problèmes maison "
        "(nettoyage, cuisine, organisation, poils d'animaux, appareils utiles). "
        "Réponds UNIQUEMENT en JSON valide, sans markdown : "
        '{"topic": str, "sources": [{"url","title"}], "facts": [{"fact","source_url","analysis","angle"}]} '
        "avec 6 à 10 faits VÉRIFIABLES et sourcés, aucune statistique sans source.")
    r = providers.generate_text(prompt, purpose="research")
    if not r["ok"]:
        db.log_event("research_gemini", {"ok": False, "stage": "generate",
                                         "detail": r.get("detail", "")[:200],
                                         "tried": r.get("tried", []), "skipped": r.get("skipped", [])})
        return {"ok": False, "detail": "échec génération: " + r.get("detail", "")[:200], "tried": r.get("tried", [])}
    try:
        txt = r["text"].strip().strip("`").removeprefix("json").strip()
        data = json.loads(txt)
        data["niche"] = config.NICHE
        tmp = os.path.join(config.RESEARCH_INBOX, "gemini_%d.json" % int(time.time()))
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        out = import_inbox()
        out["provider"] = r["provider"]
        db.log_event("research_gemini", {"ok": True, "provider_used": out["provider"],
                                         "provider_fallback": bool(r.get("fallback")),
                                         "facts_imported": sum(x.get("facts", 0) for x in out.get("runs", [])),
                                         "model": r.get("model")})
        return out
    except Exception as e:
        db.log_event("research_gemini", {"ok": False, "stage": "parse", "detail": str(e)[:150]})
        return {"ok": False, "detail": "JSON Gemini non parsable: %s" % str(e)[:150]}


def run():
    """AUTO_RESEARCH : d'abord l'import (données opérateur), puis Gemini si configuré."""
    results = []
    imp = import_inbox()
    if imp["imported_files"]:
        results.append(imp)
    if config.AUTO_RESEARCH and providers.get("research_gemini").configured():
        g = run_gemini_research()
        results.append(g)
    if not results:
        return {"ok": False, "detail": "aucune recherche disponible : déposer du JSON dans data/research/inbox "
                                       "ou configurer GEMINI_API_KEY", "results": []}
    return {"ok": True, "results": results}


def findings(limit=100):
    rows = db.q("""
        SELECT f.id, f.topic, f.fact, f.analysis, f.angle, f.created_at,
               s.url AS source_url, s.title AS source_title, s.retrieved_at
        FROM facts f LEFT JOIN sources s ON s.id = f.source_id
        ORDER BY f.id DESC LIMIT ?""", (limit,))
    return [dict(r) for r in rows]


def runs():
    return [dict(r) for r in db.q("SELECT * FROM research_runs ORDER BY id DESC LIMIT 30")]
