#!/usr/bin/env python3
"""Passe éditoriale opérateur — batch Night Shift 2026-09-30.

Contenu édité à la main, sourcé par les faits de la recherche (aucun claim sans source).
Règle : aucun faux témoignage, aucune fausse statistique, aucune garantie.
Les clés du dict EDITS (5/6/7) correspondent aux anciens ids de staging ;
nightshift_rebuild.py re-mappe vers les ids réels (styles A/B/C).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import db  # noqa: E402

Y = "https://shopping.yahoo.com/home-garden/cleaning/article/best-spin-scrubbers-174055249.html"
YR = "https://shopping.yahoo.com/home-garden/cleaning/review/amazon-khelfer-electric-spin-scrubber-review-151416560.html"
A = "https://www.accio.com/blog/what-to-sell-on-tiktok-shop-15-viral-products-to-maximize-your-profits"
YL = "https://www.yahoo.com/lifestyle/articles/pet-hair-everywhere-tiktok-famous-234000504.html"
MF = "https://www.mentalfloss.com/smart-shopping/chomchom-pet-hair-remover"
MT = "https://www.maison-travaux.fr/renovation-par-piece/cuisine-renovation-par-piece/en-2026-dites-adieu-aux-rangements-classiques-dans-la-cuisine-voici-la-nouvelle-tendance-qui-arrive-et-qui-va-tout-changer-571198.html"

EDITS = {
    5: {  # style A — Problème → Solution · spin scrubber
        "hook": "À quatre pattes pour récurer tes joints ? Arrête tout de suite.",
        "vo_text": ("Récurer les joints de carrelage à la main, c'est long, ça fait mal au dos, "
                    "et le résultat déçoit. La solution tient dans une main : une mini brosse électrique "
                    "rotative à embouts interchangeables. Tu la guides, elle frotte. Dans un test Yahoo "
                    "Shopping de 2026, ce type d'appareil a nettoyé une salle de bain entière en moins de "
                    "trente minutes. Joints, robinetterie, plaques : un embout pour chaque surface. "
                    "Limite honnête : compte trois à quatre heures de charge pour environ quatre-vingt-dix "
                    "minutes d'usage. Enregistre pour ta prochaine session ménage."),
        "onscreen": [
            {"t": "0–3 s", "text": "À quatre pattes pour récurer tes joints ?"},
            {"t": "3–8 s", "text": "Le problème : frotter à la main, sans résultat"},
            {"t": "8–18 s", "text": "La solution : brosse rotative multi-embouts"},
            {"t": "18–26 s", "text": "Test 2026 : une sdb en moins de 30 min*"},
            {"t": "26–30 s", "text": "Charge : 3-4 h pour ~90 min. Enregistre 🧽"},
        ],
        "shotlist": [
            {"t": "0–3 s", "visual": "Macro : joints de carrelage encrassés, eau qui coule"},
            {"t": "3–8 s", "visual": "Main qui frotte péniblement avec une éponge"},
            {"t": "8–18 s", "visual": "La brosse rotative en action sur les joints, mousse"},
            {"t": "18–26 s", "visual": "Embouts interchangeables présentés un par un"},
            {"t": "26–30 s", "visual": "Joints propres et robinetterie brillante"},
        ],
        "caption": ("À quatre pattes pour récurer tes joints ? Arrête tout de suite.\n\n"
                    "Une mini brosse électrique rotative multi-embouts frotte à ta place. "
                    "*Test Yahoo Shopping 2026 : salle de bain en moins de 30 min. "
                    "Charge 3–4 h pour ~90 min d'autonomie (source en commentaire épinglé).\n\n"
                    "#maison #nettoyage #cleantok #astuce #salledebain #pourtoi #fyp"),
        "cta": "Enregistre pour ta prochaine session ménage 🧽",
        "hashtags": "#maison #nettoyage #cleantok #astuce #salledebain #pourtoi #fyp",
        "claims": [
            {"claim": "Test Yahoo Shopping 2026 : une salle de bain entière nettoyée en moins de 30 minutes avec une brosse électrique rotative.", "source_url": Y, "source_title": "The 3 best spin scrubbers of 2026 — Yahoo Shopping"},
            {"claim": "Charge annoncée de 3 à 4 heures pour environ 90 minutes de nettoyage.", "source_url": Y, "source_title": "The 3 best spin scrubbers of 2026 — Yahoo Shopping"},
            {"claim": "Les embouts interchangeables permettent de nettoyer douche, sols, étagères et cuisine avec le même appareil.", "source_url": YR, "source_title": "Khelfer Electric Spin Scrubber Review — Yahoo Shopping"},
            {"claim": "Accio classe les mini brosses électriques parmi les catégories au potentiel maximal (5/5) en 2026.", "source_url": A, "source_title": "What to Sell on TikTok Shop 2026 — Accio"},
        ],
    },
    6: {  # style B — Avant → Après · rouleau anti-poils
        "hook": "Ton canapé est plein de poils malgré l'aspirateur ? Regarde la fin.",
        "vo_text": ("Les poils incrustés dans le tissu, même l'aspirateur les rate. Avant : un canapé "
                    "couvert de poils. La méthode : un rouleau en nylon, sans aucun adhésif, qui piège "
                    "les poils dans un réservoir intérieur. De petits aller-retour, un clic, et le "
                    "réservoir se vide. Selon Yahoo Lifestyle, ce type de rouleau se trouve entre "
                    "quatorze et vingt-cinq dollars, et Mental Floss relève plus de quatre-vingt-dix-huit "
                    "mille évaluations à quatre virgule six sur cinq. Après : un canapé propre, et zéro "
                    "recharge jetable à racheter. Enregistre pour le prochain passage."),
        "onscreen": [
            {"t": "0–4 s", "text": "AVANT : canapé couvert de poils 🐾"},
            {"t": "4–16 s", "text": "Rouleau nylon — zéro adhésif jetable"},
            {"t": "16–22 s", "text": "Petits aller-retour… ça monte tout seul"},
            {"t": "22–27 s", "text": "APRÈS : un clic, le réservoir se vide"},
            {"t": "27–30 s", "text": "~14–25 $* — enregistre 🐾"},
        ],
        "shotlist": [
            {"t": "0–4 s", "visual": "Canapé en tissu couvert de poils clairs, lumière rasante"},
            {"t": "4–16 s", "visual": "Le rouleau blanc tenu en main au-dessus du canapé"},
            {"t": "16–22 s", "visual": "Aller-retour du rouleau, les poils se décollent"},
            {"t": "22–27 s", "visual": "Ouverture du réservoir rempli de poils"},
            {"t": "27–30 s", "visual": "Canapé impeccable, plan large"},
        ],
        "caption": ("Ton canapé est plein de poils malgré l'aspirateur ? Regarde la fin.\n\n"
                    "Un rouleau nylon réutilisable piège les poils dans un réservoir — sans adhésif jetable. "
                    "*Prix constatés 14–25 $ (Yahoo Lifestyle) — et 98 000+ évaluations rapportées par "
                    "Mental Floss. Liens en commentaire épinglé.\n\n"
                    "#maison #animaux #poils #cleantok #astuce #pourtoi #fyp"),
        "cta": "Enregistre pour le prochain passage sur le canapé 🐾",
        "hashtags": "#maison #animaux #poils #cleantok #astuce #pourtoi #fyp",
        "claims": [
            {"claim": "Le rouleau capture les poils dans une chambre interne vidable, sans ruban adhésif jetable.", "source_url": YL, "source_title": "This TikTok-Famous Roller Is Only $14 at Walmart — Yahoo Lifestyle"},
            {"claim": "Prix constaté entre 14 $ (promo Walmart) et ~25 $ (prix habituel).", "source_url": YL, "source_title": "This TikTok-Famous Roller Is Only $14 at Walmart — Yahoo Lifestyle"},
            {"claim": "Mental Floss rapporte plus de 98 000 évaluations avec une moyenne de 4,6/5 sur Amazon pour ce produit.", "source_url": MF, "source_title": "ChomChom pet hair remover — Mental Floss"},
        ],
    },
    7: {  # style C — Test · organisation de tiroirs
        "hook": "Test : 2 méthodes pour sauver un tiroir chaotique. Une seule tient dans le temps.",
        "vo_text": ("Méthode une : tout empiler et prier. Verdict rapide : ça tient deux jours. "
                    "Méthode deux : vider complètement, trier par usage réel, puis donner une case à "
                    "chaque objet avec des séparateurs ajustables. Chronomètre en main, la deux prend "
                    "quinze minutes une seule fois — et elle tient, parce que chaque objet a sa place. "
                    "Selon Accio, ce format avant-après est l'un des plus regardés du CleanTok, et "
                    "Maison et Travaux confirme que le rangement compartimenté est la tendance cuisine "
                    "de 2026. Enregistre le plan : tu le refais ce week-end."),
        "onscreen": [
            {"t": "0–3 s", "text": "TEST : 2 méthodes contre le tiroir chaos"},
            {"t": "3–12 s", "text": "Méthode 1 : empiler et prier ❌"},
            {"t": "12–21 s", "text": "Méthode 2 : vider, trier, compartimenter"},
            {"t": "21–27 s", "text": "Verdict : la 2 tient dans le temps ✅"},
            {"t": "27–30 s", "text": "Enregistre le plan 🗄"},
        ],
        "shotlist": [
            {"t": "0–3 s", "visual": "Tiroir de cuisine débordant, vu de dessus"},
            {"t": "3–12 s", "visual": "La pile s'écroule, on galère à refermer"},
            {"t": "12–21 s", "visual": "Tiroir vidé, tri sur le plan de travail, pose des séparateurs"},
            {"t": "21–27 s", "visual": "Tiroir compartimenté parfait, vu de dessus"},
            {"t": "27–30 s", "visual": "Zoom final sur l'ordre, main qui referme en douceur"},
        ],
        "caption": ("Test : 2 méthodes pour sauver un tiroir chaotique. Une seule tient dans le temps.\n\n"
                    "Vider → trier → compartimenter : 15 min une fois, pour un ordre qui dure. "
                    "Format avant/après plébiscité sur #CleanTok (Accio) · rangement compartimenté = "
                    "tendance cuisine 2026 (Maison & Travaux). Liens en commentaire épinglé.\n\n"
                    "#organisation #maison #cleantok #cuisine #astuce #pourtoi #fyp"),
        "cta": "Enregistre le plan pour ce week-end 🗄",
        "hashtags": "#organisation #maison #cleantok #cuisine #astuce #pourtoi #fyp",
        "claims": [
            {"claim": "Accio : les vidéos avant/après d'organisation de tiroirs font partie des formats les plus regardés du #CleanTok, avec des taux de retour faibles.", "source_url": A, "source_title": "What to Sell on TikTok Shop 2026 — Accio"},
            {"claim": "Maison & Travaux : la tendance cuisine 2026 privilégie tiroirs profonds et rangement compartimenté.", "source_url": MT, "source_title": "Tendance rangement cuisine 2026 — Maison & Travaux"},
        ],
    },
}


def apply_edit(sid, e):
    script_text = "\n".join("[%s] %s" % (o["t"], o["text"]) for o in e["onscreen"])
    db.run("""UPDATE scripts SET hook=?, vo_text=?, script_text=?, onscreen_json=?, shotlist_json=?,
              caption=?, cta=?, hashtags=?, claims_json=?, provider=? WHERE id=?""",
           (e["hook"], e["vo_text"], script_text,
            json.dumps(e["onscreen"], ensure_ascii=False),
            json.dumps(e["shotlist"], ensure_ascii=False),
            e["caption"], e["cta"], e["hashtags"],
            json.dumps(e["claims"], ensure_ascii=False),
            "local_text+editorial", sid))
    db.log_event("editorial_polish", {"script_id": sid, "claims": len(e["claims"]), "by": "operator-nightshift"})


def main():
    for sid, e in EDITS.items():
        s = db.q("SELECT id, style FROM scripts WHERE id=?", (sid,), one=True)
        if not s:
            print("script %d introuvable — utiliser nightshift_rebuild.py" % sid)
            sys.exit(1)
        apply_edit(sid, e)
        print("✔ script %d édité — %d claims sourcés" % (sid, len(e["claims"])))
    print("OK")


if __name__ == "__main__":
    main()
