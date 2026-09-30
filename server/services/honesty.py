"""Règles d'honnêteté — partagées entre génération (scripts) et QA.

INTERDITS (bloquants) : faux témoignages, faux avis, fausses ventes, fausses statistiques,
fausses specs, faux tests perso, garanties de résultat, promesses de viralité,
stats non sourcées (chiffre sans URL de source dans les claims).
"""
import re

NEG = r"(?:pas de |sans |aucun[ne]? |jamais de |n'(?:est|y a) )"

BANNED_PATTERNS = [
    r"\bgaranti[es]?\b(?! de conformité)",
    r"\bvues garanties\b",
    r"\bviralit[ée] garantie\b",
    r"\bventes garanties\b",
    r"\br[ée]sultats? garantis?\b",
    r"\bdevenir viral\b",
    r"\b\d+ ?% de (?:r[ée]sultats?|satisfaction)\b",
    r"\btest[ée] (?:par|pendant) \d+ (?:jours?|semaines?) (?:personnellement|chez moi)\b",
    r"\b(?:j'ai |j’ai )achet[ée] (?:pour toi|pour vous)\b",
    r"\bavis clients??:\b",
    r"\b\d+([ .]\d+)?[ /]5\b",                          # fausse note
    r"\bmeilleur(?:e|s)? du march[ée]\b",
    r"\bn° ?1\b",
]

def find_violations(text):
    """Retourne la liste des interdits trouvés (hors négations honnêtes)."""
    if not text:
        return []
    cleaned = re.sub(NEG + r"[^.\n]*", "", text.lower())
    hits = []
    for pat in BANNED_PATTERNS:
        for m in re.finditer(pat, cleaned, re.IGNORECASE):
            hits.append({"pattern": pat, "match": m.group(0)})
    return hits


def clean(text):
    """True si aucun interdit."""
    return not find_violations(text)


STYLES = {
    "A": "Problème → Solution",
    "B": "Avant → Après",
    "C": "Test",
    "D": "Comparaison",
    "E": "Curiosité",
}

DISCLOSURE_LINE = "Contenu créé avec assistance IA (visuels/voix). Aucun achat requis."
