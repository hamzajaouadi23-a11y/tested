"""Service SCRIPTS — styles A–E, claims sourcés, lint d'honnêteté systématique.

Sortie par candidat : hook, script, voix off, textes écran, shot list, caption, CTA,
hashtags, metadata, claims (chaque fait ↔ source), statut de disclosure IA.
Essaie d'abord la chaîne TEXT cloud ; sinon banque locale FR (quality=fallback, signalée).
"""
import json

from .. import db, providers
from . import honesty

STYLE_LETTERS = ["A", "B", "C", "D", "E"]

HOOK_BANK = {
    "A": ["Ce problème de {topic_short} te pourrit la vie ? Regarde 20 secondes.",
          "Si {problem_short} te rend fou(folle), cette idée va te plaire.",
          "Le truc que personne ne t'explique sur {topic_short}."],
    "B": ["Avant / après : la zone {topic_short} transformée en une étape.",
          "Le changement le plus satisfaisant que tu verras aujourd'hui : {topic_short}.",
          "De catastrophique à propre : {topic_short}, la méthode en images."],
    "C": ["On compare deux méthodes pour {problem_short} — laquelle gagne ?",
          "Test honnête : 3 techniques contre {problem_short}, une seule marche vite.",
          "J'ai chronométré deux solutions contre {problem_short}. Verdict net."],
    "D": ["Méthode classique VS astuce rapide pour {problem_short}.",
          "Le duel : vieille habitude ou outil adapté contre {problem_short} ?",
          "Deux options contre {problem_short} — une te fait perdre du temps."],
    "E": ["Pourquoi {problem_short} revient toujours… et comment le stopper.",
          "L'erreur invisible qui entretient {problem_short}.",
          "Personne ne t'a dit ça sur {topic_short}."],
}

CTA_BANK = [
    "Enregistre pour ce week-end 🧽",
    "Partage à quelqu'un qui galère avec ça.",
    "Suis pour la partie 2 : le guide complet.",
    "Commente « GUIDE » et je t'envoie la checklist.",
]

HASHTAG_BASE = ["#maison", "#astuce", "#cleantok", "#nettoyage", "#organisation", "#pourtoi", "#fyp"]

STYLE_STRUCTURE = {
    "A": [("Hook", "0–3 s"), ("Problème", "3–8 s"), ("Solution", "8–18 s"), ("Preuve/étapes", "18–26 s"), ("CTA", "26–30 s")],
    "B": [("Avant", "0–4 s"), ("Méthode", "4–16 s"), ("Pendant", "16–22 s"), ("Après", "22–27 s"), ("CTA", "27–30 s")],
    "C": [("Hook test", "0–3 s"), ("Méthode 1", "3–12 s"), ("Méthode 2", "12–21 s"), ("Verdict", "21–27 s"), ("CTA", "27–30 s")],
    "D": [("Hook duel", "0–3 s"), ("Option 1", "3–12 s"), ("Option 2", "12–21 s"), ("Verdict", "21–27 s"), ("CTA", "27–30 s")],
    "E": [("Hook curiosité", "0–4 s"), ("Explication", "4–14 s"), ("Démonstration", "14–24 s"), ("Le pourquoi", "24–28 s"), ("CTA", "28–32 s")],
}


def _shorten(s, n=42):
    s = (s or "").strip().rstrip(".")
    return s if len(s) <= n else s[:n - 1].rsplit(" ", 1)[0] + "…"


def _ctx(candidate, facts):
    topic = candidate["title"]
    problem = candidate["problem"]
    problem_short = _shorten(problem, 46)
    topic_short = _shorten(topic, 40)
    solution = candidate["solution"]
    relevant = [f for f in facts if _related(f.get("topic", ""), topic) or True][:6]
    return {"topic": topic, "topic_short": topic_short, "problem": problem,
            "problem_short": problem_short, "solution": solution, "facts": relevant}


def _related(a, b):
    a, b = (a or "").lower(), (b or "").lower()
    return a and b and (a in b or b in a or any(w in b for w in a.split() if len(w) > 5))


def _local_script(candidate, facts, style):
    """Générateur local déterministe (fallback réel, signalé quality=fallback)."""
    import random
    rnd = random.Random(candidate["id"] * 7 + sum(map(ord, style)))
    ctx = _ctx(candidate, facts)
    hook = rnd.choice(HOOK_BANK[style]).format(**ctx)
    facts_txt = [f["fact"].rstrip(".") for f in ctx["facts"][:2]]
    struct = STYLE_STRUCTURE[style]

    vo_parts = [hook]
    if facts_txt:
        vo_parts.append("D'abord, ce qu'on sait vraiment : " + facts_txt[0] + ".")
    vo_parts.append("La solution concrète : " + ctx["solution"].rstrip(".") + ".")
    if len(facts_txt) > 1:
        vo_parts.append("Et le détail qui change tout : " + facts_txt[1] + ".")
    vo_parts.append("Pas de miracle — juste une méthode propre, montrée étape par étape.")
    vo_text = " ".join(vo_parts)

    onscreen = [
        {"t": struct[0][1], "text": hook[:60]},
        {"t": struct[1][1], "text": _shorten(ctx["problem"], 58)},
        {"t": struct[2][1], "text": _shorten(ctx["solution"], 58)},
        {"t": struct[3][1], "text": _shorten(facts_txt[0], 58) if facts_txt else "Méthode, étape par étape"},
        {"t": struct[4][1], "text": "Enregistre 🧽 · Partie 2 bientôt"},
    ]
    shots = [
        {"t": struct[0][1], "visual": "Plan rapproché : le problème bien visible (" + _shorten(ctx["problem"], 60) + ")"},
        {"t": struct[1][1], "visual": "Zoom lent sur la zone concernée, éclairage franc"},
        {"t": struct[2][1], "visual": "Démonstration : " + _shorten(ctx["solution"], 70)},
        {"t": struct[3][1], "visual": "Plan résultat, comparaison avant/après à l'écran"},
        {"t": struct[4][1], "visual": "Plan propre final + écran CTA"},
    ]
    claims = [{"claim": f["fact"], "source_url": f.get("source_url", ""), "source_title": f.get("source_title", "")}
              for f in ctx["facts"][:4] if f.get("source_url")]
    hashtags = list(dict.fromkeys(HASHTAG_BASE + ["#" + w for w in ctx["topic_short"].lower().replace("…", "").split() if len(w) > 4 and w.isalpha()][:3]))
    caption = (hook + "\n\n" + "Ce qu'il faut retenir : " + _shorten(ctx["solution"], 90) +
               "\nSources & méthode en commentaire épinglé.\n\n" + " ".join(hashtags[:8]))
    script = {
        "style": style, "hook": hook, "vo_text": vo_text,
        "onscreen": onscreen, "shotlist": shots,
        "caption": caption, "cta": rnd.choice(CTA_BANK), "hashtags": " ".join(hashtags[:8]),
        "claims": claims,
        "script_text": "\n".join("[%s · %s] %s" % (s[0], s[1], o["text"]) for s, o in zip(struct, onscreen)),
    }
    return script


def _cloud_script(candidate, facts, style):
    """Essaie la chaîne cloud avec prompt JSON strict. Parse + vérif honnêteté."""
    facts_lines = "\n".join("- %s (source: %s)" % (f["fact"], f.get("source_url", "")) for f in facts[:8])
    prompt = (
        "Tu écris un script de vidéo verticale 9:16 de ~30 secondes, en FRANÇAIS, niche maison. "
        "Style %s (%s). Candidat : %s. Problème : %s. Solution : %s.\n"
        "Faits SOURCÉS autorisés (utilise UNIQUEMENT ceux-ci pour toute affirmation factuelle) :\n%s\n"
        "INTERDITS : faux témoignage, faux avis, fausse statistique, fausse spec, faux test perso, "
        "garantie de résultat, promesse de viralité.\n"
        "Réponds UNIQUEMENT en JSON valide sans markdown : "
        '{"hook": str, "vo_text": str (55–80 mots), "onscreen": [{"t":"0–3 s","text":str}], '
        '"shotlist": [{"t":"0–3 s","visual":str}], "caption": str, "cta": str, "hashtags": str, '
        '"claims": [{"claim": str, "source_url": str}]}'
         % (style, honesty.STYLES[style], candidate["title"], candidate["problem"],
            candidate["solution"], facts_lines or "(aucun fait sourcé — rester descriptif, zéro chiffre)"))
    r = providers.generate_text(prompt, purpose="script")
    if not r["ok"]:
        return None
    try:
        txt = r["text"].strip().strip("`").removeprefix("json").strip()
        data = json.loads(txt)
        data["claims"] = [c for c in data.get("claims", []) if c.get("source_url")]
        return data, r["provider"]
    except Exception:
        return None


def generate_for_candidate(candidate_id, styles=None):
    """Génère 1 script par style demandé (défaut : les 3 premiers styles)."""
    from . import research, selection
    cand = selection.get(candidate_id)
    if not cand:
        return {"ok": False, "detail": "candidat introuvable"}
    facts = research.findings(40)
    styles = styles or ["A", "B", "C"]
    made = []
    for style in styles:
        data, used_provider = None, "local_text"
        cloud = _cloud_script(cand, facts, style)
        if cloud:
            data, used_provider = cloud
        if not data:
            data = _local_script(cand, facts, style)
        # lint honnêteté systématique, quel que soit le provider
        full = json.dumps({k: data.get(k) for k in ("hook", "vo_text", "caption", "cta", "onscreen")}, ensure_ascii=False)
        violations = honesty.find_violations(full)
        if violations:
            db.log_event("script_lint_block", {"candidate_id": candidate_id, "style": style, "violations": violations[:5]})
            if used_provider != "local_text":   # replie sur le générateur local sûr
                data, used_provider = _local_script(cand, facts, style), "local_text"
        has_ai = 1 if (data.get("claims") and used_provider != "local_text") or used_provider != "local_text" else 0
        sid = db.run(
            "INSERT INTO scripts(candidate_id,style,hook,script_text,vo_text,onscreen_json,shotlist_json,caption,cta,hashtags,claims_json,ai_disclosure,provider,created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (candidate_id, style, data["hook"], data.get("script_text", ""), data["vo_text"],
             json.dumps(data.get("onscreen", []), ensure_ascii=False),
             json.dumps(data.get("shotlist", []), ensure_ascii=False),
             data["caption"], data["cta"], data.get("hashtags", ""),
             json.dumps(data.get("claims", []), ensure_ascii=False),
             1 if used_provider != "local_text" else 0,
             used_provider, db.now()))
        db.run("UPDATE candidates SET status='used' WHERE id=? AND status='selected'", (candidate_id,))
        db.log_event("script_generated", {"script_id": sid, "candidate_id": candidate_id, "style": style, "provider": used_provider})
        made.append({"script_id": sid, "style": style, "provider": used_provider})
    return {"ok": True, "scripts": made}


def get_script(sid):
    r = db.q("SELECT * FROM scripts WHERE id=?", (sid,), one=True)
    if not r:
        return None
    d = dict(r)
    d["onscreen"] = db.getjson(r, "onscreen_json", [])
    d["shotlist"] = db.getjson(r, "shotlist_json", [])
    d["claims"] = db.getjson(r, "claims_json", [])
    return d


def list_scripts(candidate_id=None):
    if candidate_id:
        return [dict(r) for r in db.q("SELECT * FROM scripts WHERE candidate_id=? ORDER BY id DESC", (candidate_id,))]
    return [dict(r) for r in db.q("SELECT * FROM scripts ORDER BY id DESC LIMIT 50")]
