# RECOVERY STATUS — TESTÉ & PROPRE · CONTENT OS

Date : 2026-09-30 (session « Night Shift »)
Responsable : agent Arena (récupération + reconstruction du pipeline)

## APP STATUS
- **App de vente V1+V2 (`teste-et-propre/index.html`)** : ✅ RÉCUPÉRÉE INTACTE depuis `TESTE-PROPRE-BACKUP-V3.zip` (MD5 `55cae67e65771f1aa193a4baa1cecde8` conforme à `LATEST-BACKUP.txt`). Servie sur le port 8080.
- **Backend Production Pipeline (`server/` + `studio/`)** : 🚧 EN CONSTRUCTION dans cette session (le ZIP d'origine ne contenait **aucun** serveur : l'app était 100 % statique).

## TEST STATUS
- Harnais V2 recréé en fichier permanent : `tests/harness.js` → **TESTS: 42 | PASS: 42 | FAIL: 0** (3 exécutions stables).
- Syntaxe JS vérifiée (`node --check`) : OK.
- Tests backend : en cours d'écriture.

## CURRENT COMMIT
- `927056c` — chore: recover project from V3 backup into Git tracking

## CURRENT BRANCH
- `arena/01a0efa9-tested` (branche de session Arena — la consigne demandait `nightshift-v5` ; la session est verrouillée sur cette branche, donc tout le travail Night Shift y est fait. `main` n'est PAS modifiée.)

## TAGS
- `stable-before-nightshift` → `7dd7a72` (état vierge avant toute modification)
- `v5.0-recovered` → `927056c` (baseline récupérée et testée)

## WORKING FEATURES (app V2 — vérifiées par tests)
- Product Lab (10 hooks / 5 idées / 3 scripts faceless FR-EN)
- Script Builder (Hook/Problème/Démo/Résultat/CTA, VO, texte écran, plans)
- Content Tracker (CRUD, statuts, métriques, tri) + Winners
- Mode Clients : brief → pack 3 vidéos → export texte + HTML imprimable
- Prospects CRM (8 statuts), Démo Reel, Vendre (page de vente 49/79/129 €), contenus de prospection
- Persistance localStorage `tnp_*`, échappement XSS, honnêteté des claims (test dédié)
- Couverture complète data-action ↔ ACTIONS, tabs ↔ sections

## BROKEN FEATURES
- Aucune détectée dans l'app V2 (42/42).

## MOCK FEATURES (existant AVANT cette session)
- L'ancien « générateur de DÉMO » produisait des **scripts/storyboards textuels** marqués DEMO — aucune vidéo réelle n'existait : pas de média, pas de voix, pas de rendu. C'était du texte, pas un faux MP4.
- Aucun provider, aucune API, aucune persistance serveur n'existaient (100 % navigateur).

## REAL FEATURES (nouvelles, cette session)
- Toolchain réelle installée : Python 3.11 + venv, Pillow, requests, **FFmpeg 7.0.2 statique** (via imageio-ffmpeg), Node 22.
- Backend pipeline : voir NIGHTSHIFT-REPORT.md (registre de providers, SQLite, recherche, scripts, voix, rendu, QA, approbation).

## MISSING FEATURES (comblées ou en cours cette session)
- Registre de providers (TEXT/RESEARCH/IMAGE/VOICE/VIDEO/STORAGE/SOCIAL/ANALYTICS/SCHEDULER) : 🚧
- Recherche réelle sourcée : 🚧
- Génération de MP4 réels 1080x1920 + voix off FR réelle : 🚧
- QA automatique + REAL_ASSETS_CHECK + AI_DISCLOSURE_CHECK : 🚧
- Connexions sociales officielles (OAuth) : ⛔ bloqué sans tokens utilisateur — UI préparée, statut honnête « non configuré ».
