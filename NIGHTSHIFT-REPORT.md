# NIGHTSHIFT REPORT — nuit du 2026-09-30 (run réel, compte CleanTok FR)

## 1. Mission & résultat
Produire un lot de **3 vidéos TikTok verticales 9:16, 30-45 s, FR, produits shopping**, validées QA + rendues avec vraie voix off, prêtes à poster sur `data/accounts/v2-maison.json`. **RÉSULTAT : 3/3 en état `WAITING_APPROVAL` (QA pass, 0 blocker, 0 warning)**, fichiers dans `data/media/ready_to_post/`.

## 2. Entrées de veille (web, 30/09/2026)
Sources consultées : Accio (tendances TikTok Shop 2026), Yahoo Shopping (test brosse à récurer électrique 2026), Mental Floss (article ChomChom Roller, 98 000 notations ~4,6/5), Maison & Travaux (cuisine modulable/tiroirs 2026 FR), visibrain (#CleanTok ~100 Md vues), trendsicle.com, viralcleaning.nl, homemadesimple.com. 10 faits extraits avec angle marketing dans `data/research/nightshift_2026-09-30.json`.

## 3. Sélection (top 3 sur 5 candidats)
| Candidat | Score | Pourquoi |
|---|---|---|
| Mini brosse électrique (Accio) | 82 | Trend CleanTok fort, résultat visible, achat petite somme, "5000 ventes/j TikTok" + avis positifs |
| Rouleau anti-poils ChomChom (Mental Floss) | 75 | Produit humain, cadeau, peu de risque, usage simple (pas d'adhésif), réutilisable |
| Organiseurs tiroirs (Accio) | 70 | Produit organisation n°1 : avant/après viral, achat modulable, "addictif" selon TikTok |

## 4. Sortie (vidéos + scripts)
| # | Fichier | Script | Durée | Style | QA | Incidents corrigés |
|---|---|---|---|---|---|---|
| 1 | `video_01.mp4` | "À quatre pattes pour récurer tes joints ?" | 34,3 s | A (Crunchy Before/After) | Pass | écrire en: scaling d || Ruff fallback |
| 2 | `video_02.mp4` | "Ton canapé peut rester blanc (même avec un chien)" | 35,2 s | B (Worst First) | Pass | QA NO_FAKE_CLAIMS sur "4,6/5" → déplacé dans claims_json + caption réécrite |
| 3 | `video_03.mp4` | "Les tiroirs rangés en 3 secondes chrono" | 35,5 s | C (3 Battle Test) | Pass | émojis non dessinables → mappés en ✓/✗ |

Chaque `metadata.json` : caption, claims avec URLs de sources, tags, vérifié conformité TikTok, note légale "Contenu créé avec assistance IA... ".

## 5. Ancien add_voice vote
**`voice-00`** (féminine FR narration, sélectionnée par l'utilisateur cette nuit) — appliquée aux 3 voix off (34,3 s / 35,2 s / 35,5 s, ~24 nouveaux mots/min, naturelles 80-140 mots/min nos VO ≈ 90-100 mots/min à vitesse normale).

## 6. Ce qui a bien marché / mal
👍 pipeline complet opérationnel en 2,5 min/vidéo ; QA a bloqué (à juste titre) 2 violations avant production, pas après ; rendu 1080 p H.264 30 fps CRF 21 en ~30-60 s par segment ; voix réelles (v3+ voice-00).
👎 rendu initial trop lent (zoompan sur d*FPS) ; sanitization des émojis absente dans composition ; IDs pipeline réécrits non recréés sans script 5/6/7 renommés en 1/2/3. Tous corrigés dans `tools/`, testés par `tests/test_server.py` (40/40).

## 7. Commentaires / suites
- Admin studio : ouvrir `http://localhost:8090` (local) — thumbnails + boutons “publier” par vidéo (publier humain uniquement).
- Prochaine amélioration : script d'enchaînement de pose `tools/publish_manual.py` (sélection vidéo, horodatage, réécriture caption); mesurer la vitesse traitement sur fraîche requête pour accélérer de 50 %.
