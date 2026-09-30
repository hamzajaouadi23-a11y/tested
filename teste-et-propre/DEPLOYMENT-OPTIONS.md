# Déploiement — TESTÉ & PROPRE CONTENT OS

L'app = UN seul fichier statique : `index.html`. Aucun serveur, aucune base de données, aucune dépendance.
Elle peut donc être hébergée gratuitement et DÉFINITIVEMENT sur n'importe quel hébergeur statique.

## Situation actuelle (environnement Arena)
| Accès | Statut |
|---|---|
| Aperçu Live Arena (port 8080) | Fonctionne tant que la session est active (le serveur s'arrête entre deux tours ; je le relance à chaque tour). Non partageable publiquement. |
| Lien public litter.catbox.moe | TEMPORAIRE (~72 h). Partageable, HTML exécutable. |
| Lien direct {port}-{sandbox}.e2b.app | Bloqué par jeton de sécurité (403). Inutilisable. |

## Pourquoi pas de lien permanent depuis ici
Un lien permanent exige un COMPTE chez un hébergeur (le compte garantit que le site t'appartient et reste en ligne).
Aucun compte/jeton n'est disponible dans cet environnement, et je ne crée pas de compte à ta place avec de fausses informations.

## Options pour un lien PERMANENT et GRATUIT (ordre de simplicité)
1. **Netlify Drop** (le plus simple, ~2 min, 0 code) : app.netlify.com/drop → compte gratuit → glisser-déposer le dossier contenant `index.html` → lien `https://xxxx.netlify.app` permanent.
2. **GitHub Pages** : compte GitHub gratuit → nouveau dépôt public → envoyer `index.html` → Settings > Pages > branche main → `https://TON-PSEUDO.github.io/NOM/`.
3. **Cloudflare Pages** : compte gratuit → Workers & Pages → Upload assets → glisser `index.html`.
4. **Option automatique (recommandée si tu veux que JE le fasse)** : crée un compte gratuit Netlify (ou GitHub), génère un « token d'accès personnel » et donne-le-moi dans le chat ; je déploie et je te renvoie le lien permanent. (Révoque le token ensuite si tu veux.)

## Important
- Les données (prospects, clients, packs…) sont dans le localStorage du NAVIGATEUR de chaque appareil/lien. Changer de lien ou d'appareil = données séparées. Garder UN lien principal et utiliser l'export pour sauvegarder.
- Un lien permanent = une seule adresse à garder : c'est aussi ce qui évite de perdre tes prospects.
