# ❓ QUESTIONS-FOR-USER — à ta convenance (aucune n'est bloquante pour l'instant)

0. **🔑 ACTION UNIQUE requise pour l'URL publique permanente (10 min, zéro code, zéro secret dans Git)** —
   j'ai tout préparé côté repo (Dockerfile à la racine, railway.toml validé, /health, volume persistant, seed non-destructif, auto-deploy).
   **Cause prouvée de ton erreur « Railpack failed to prepare the build » : Railway buildait la branche `main` (qui ne contient qu'un `workspace-*.zip`) — pas notre branche.**
   Il ne reste QUE ce clic manuel, impossible pour moi sans ton login : dans Railway,
   **Service → Settings → Source → Branch → sélectionner `arena/01a0efa9-tested`** → **Deploy**.
   Détails/preuves dans `DEPLOY-RAILWAY.md` (encadré rouge en tête). Dès le 1er deploy OK, envoie-moi l'URL `*.up.railway.app` pour la vérif HTTP externe + tag `stable-railway`.
1. **Clés providers** — Gemini / Groq / Mistral (texte), Azure / ElevenLabs (voix) : veux-tu les connecter ? Coût éventuel = ta décision. L'app est 100 % utilisable en offline en attendant ; place les clés dans `.env` (jamais commité), pas besoin d'autre chose.
2. **Publication des 3 vidéos en attente** (`ready_to_post/video_01/02/03`) : publication = action **humaine uniquement** (règle AUTO_PUBLISH=OFF). OK pour poster toi-même avec `POSTING_GUIDE.md`, ou me dire de préparer les fichiers autrement ?
3. **Branche** — tu avais demandé `nightshift-v5` puis `recovery/current-work` : la session est verrouillée sur `arena/01a0efa9-tested`. Souhaites-tu, hors session, renommer/forker cette branche sur GitHub (1 clic) ? Les tags `stable-live-2026-09-30` / `recovery-current-work` peuvent servir de points de départ.
4. **Lien live pérenne** — l'URL de preview Arena change à chaque session (sandbox éphémère). Si tu veux un lien fixe sans relancer, il faut un hébergement dédié (p. ex. VPS/Render ~0–5€/mois) : je ne crée rien de payant sans ton feu vert.
5. **Apprentissage** — pour activer `enough_data`, il faut les métriques réelles de 5 vidéos postées (vues 2 s / complètes…). Veux-tu un mini-mode « saisie métriques » dans le Studio, ou continuer via `analytics:save` ?

## 6. 🔴 Matrice des blocages réseau du sandbox (mesurée le 30/09 — pourquoi je ne peux pas déployer à ta place)
Egress autorisé : github.com · registry.npmjs.org · pypi.org UNIQUEMENT.
Bloqués (TLS sortant coupé) : api.railway.app · backboard.railway.app · api.render.com · api.cloudflare.com · api.trycloudflare.com · localtunnel.me · bore.pub · serveo.net · api.vercel.com · api.netlify.com · api.fly.io · api.pythonanywhere.com.
GitHub Pages : le token d'App Arena n'a PAS la permission Pages (403 "Resource not accessible by integration").
=> Toute CLI (Railway/Render/fly/cloudflared/serveo) est inutilisable DEPUIS le sandbox. Le seul canal = push GitHub (déclenche un build Railway/Render SI le service suit notre branche) — vient d'être refait (7464e50 / queue).
=> Reste UNE action, ~90 s, dans TON navigateur : Railway → service → Settings → Source → Branch = `arena/01a0efa9-tested` → Deploy (+ Volume /data si pas déjà fait + Generate Domain). Alternative sans compte PaaS : activer GitHub Pages (Settings → Pages → branch arena + root) = URL publique statique immédiate pour l'app V2 offline (sans backend).
