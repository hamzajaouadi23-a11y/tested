# ❓ QUESTIONS-FOR-USER — à ta convenance (aucune n'est bloquante pour l'instant)

1. **Clés providers** — Gemini / Groq / Mistral (texte), Azure / ElevenLabs (voix) : veux-tu les connecter ? Coût éventuel = ta décision. L'app est 100 % utilisable en offline en attendant ; place les clés dans `.env` (jamais commité), pas besoin d'autre chose.
2. **Publication des 3 vidéos en attente** (`ready_to_post/video_01/02/03`) : publication = action **humaine uniquement** (règle AUTO_PUBLISH=OFF). OK pour poster toi-même avec `POSTING_GUIDE.md`, ou me dire de préparer les fichiers autrement ?
3. **Branche** — tu avais demandé `nightshift-v5` puis `recovery/current-work` : la session est verrouillée sur `arena/01a0efa9-tested`. Souhaites-tu, hors session, renommer/forker cette branche sur GitHub (1 clic) ? Les tags `stable-live-2026-09-30` / `recovery-current-work` peuvent servir de points de départ.
4. **Lien live pérenne** — l'URL de preview Arena change à chaque session (sandbox éphémère). Si tu veux un lien fixe sans relancer, il faut un hébergement dédié (p. ex. VPS/Render ~0–5€/mois) : je ne crée rien de payant sans ton feu vert.
5. **Apprentissage** — pour activer `enough_data`, il faut les métriques réelles de 5 vidéos postées (vues 2 s / complètes…). Veux-tu un mini-mode « saisie métriques » dans le Studio, ou continuer via `analytics:save` ?
