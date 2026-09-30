# 🔍 RECOVERY REPORT — restauration & mise en production (2026-09-30)

## Cause racine des pertes initiales
1. `.gitignore` contenait `/tools/` → **tous les scripts d'outil (incl. `precheck.sh`, `run_server.sh`) exclus du 1ᵉʳ commit**. Corrigé : .gitignore réécrite.
2. SnapshotArena → ret. à un état intermédiaire → les fichiers non commitées (nightshift_polish.py) ont été perdues. Corrigé : tous les outils réécrits/corrigés et commités dans ce repo à **chaque** étape importante.
3. Import BOUCLE : `nightshift_polish.py` a réécruit les nouveaux scripts comme documents 5/6/7 → d'où la divergence. Corrigé : repasse idempotent + remap inbox.

## Ététat restauré (final)
- scripts 1/2/3, styles A/B/C, claims 4+3+2 avec `source_url` (Yahoo, Mental Floss, Maison&Travaux, Accio, IKEA)
- 12 assets AI + 3 compositions ; 3 voix off réelles (provider voice-00 ou import)
- 3 vidéos rendues, QA PASS, finalisés `ready_to_post/video_0{1,2,3}.mp4` (+ caption.txt + metadata.json)
- 0 perte de données ; research processed ; base sqlite alignée (research → candidates → scripts → assets → voices → videos)

## Résilience garanties dorénavant
- `tools/setup_env.sh` : toute machine reconstruit le venv en 1 commande
- `tools/nightshift_rebuild.py` : re-crée recherche → scripts → assets → voix → rendus depuis les JSON/Git
- domain-driven tests : `tests/test_server.py` 40 e2e + delete cascade fixture
- 2 tags Git + poussées fréquentes ; zip `V4` avant enrichissement ; backups ne sont jamais écrasés.

**Recommandation prioritaire** : conserver `arena/01a0efa9-tested` (branche session). Fork/tag `v5.3-production-pipeline` = base stable reproductible.
