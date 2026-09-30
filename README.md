# TESTÉ & PROPRE — CONTENT OS

**Source de vérité : ce dépôt GitHub.** Projet récupéré et organisé lors de la session « Night Shift » (2026-09-30).

## Contenu du dépôt

| Chemin | Rôle |
|---|---|
| `teste-et-propre/index.html` | **App principale V1+V2** — mono-fichier, zéro dépendance, hors ligne, localStorage (`tnp_`). NE PAS CASSER. |
| `teste-et-propre/V1-index-backup.html` | Copie intacte de la V1 |
| `teste-et-propre/PROJECT_HANDOFF.md` | Architecture & conventions de l'app |
| `teste-et-propre/CONTINUE-PROMPT.txt` | Prompt de reprise de session |
| `teste-et-propre/DEPLOYMENT-OPTIONS.md` | Options de déploiement permanent |
| `server/` | **Backend Production Pipeline** (Python stdlib) : registre de providers, recherche, scripts, voix, rendu FFmpeg, QA, approbation humaine |
| `studio/` | Interface web du pipeline de production (servie par le backend) |
| `tests/harness.js` | Harnais de tests Node (42 tests) de l'app mono-fichier |
| `tests/test_server.py` | Tests du backend pipeline |
| `data/` | Données d'exécution : SQLite, recherche, médias. `data/media/ready_to_post/` = vidéos finales |
| `workspace-01a0ef7d-…zip` | Archive d'origine du workspace (conservée — ne jamais supprimer) |

## Démarrage rapide

```bash
# 1) L'app de vente (statique, autonome)
cd teste-et-propre && python3 -m http.server 8080 --bind 0.0.0.0

# 2) Le pipeline de production (backend + Studio UI)
python3 server/app.py            # écoute sur 0.0.0.0:8090

# 3) Tests
node tests/harness.js            # 42 tests attendus : 42 PASS
python3 tests/test_server.py     # tests backend
```

## Principes NON négociables

1. **Zéro fausse promesse** : pas de viralité/vues/ventes « garanties », pas de faux témoignages, pas de fausses statistiques, pas de faux tests produits.
2. **Secrets côté serveur uniquement** : clés API dans `.env` (jamais commité — voir `.env.example`), jamais dans le frontend, jamais dans les backups.
3. **Publication humaine obligatoire** : `AUTO_PUBLISH = OFF`. Le pipeline s'arrête à `WAITING_APPROVAL`.
4. **DEMO ≠ PRODUCTION** : tout asset mock/démo bloque l'approbation production (QA `REAL_ASSETS_CHECK`).
5. Sauvegardes : GitHub + nouveaux ZIP numérotés (jamais d'écrasement).
