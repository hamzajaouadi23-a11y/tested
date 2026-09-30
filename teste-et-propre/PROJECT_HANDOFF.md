# TESTÉ & PROPRE — CONTENT OS · Handoff Projet (V2)

## 1. Ce que c'est
Application web **mono-fichier** (`index.html`, HTML + CSS + JS inline, zéro dépendance, zéro build).
Deux usages :
1. **CONTENT OS (V1)** — générateur de contenu pour business "faceless" TikTok/Reels/Shorts.
2. **MACHINE DE VENTE freelance (V2)** — système pour vendre des packs de vidéos courtes (3 vidéos = 49 € par défaut) à des commerces locaux, et gérer tout le cycle : prospection → démo → offre → paiement → production → livraison → suivi.

## 2. Architecture
- **Un seul fichier** : `teste-et-propre/index.html` (HTML, `<style>` inline, `<script>` inline).
- `V1-index-backup.html` = copie intacte de la V1 (avant V2).
- Aucun framework, aucune lib externe, aucun appel réseau : fonctionne **hors ligne** une fois chargé.
- Persistance : **localStorage**, préfixe `tnp_`.

### Clés localStorage
| Clé | Contenu |
|---|---|
| `tnp_products` | Produits (Product Lab V1) |
| `tnp_videos` | Vidéos suivies (Content Tracker) |
| `tnp_scripts` | Scripts sauvegardés (Script Builder) |
| `tnp_gens` | Générations Lab par produit `{productId: {hooks, ideas, minis}}` |
| `tnp_settings` | `{lang:"fr"|"en", paymentLink:"", pack:"49"|"79"|"129"}` |
| `tnp_clients` | Fiches clients V2 |
| `tnp_packs` | Packs générés `{clientId: {concepts:[3], generatedAt, ...}}` |
| `tnp_prospects` | Prospects V2 |
| `tnp_demos` | Démos générées V2 (max 12) |
| `tnp_sales` | Dernier contenu de prospection généré |

## 3. Sections (tabs) — `data-tab` → `section#sec-<tab>`
`pilotage` (Accueil : workflow 8 étapes + checklist objectif 1er client + KPIs) ·
`clients` (brief + pack 3 vidéos + export/livraison) ·
`prospects` (CRM simple, 8 statuts, compteurs) ·
`demo` (générateur de démo Reel 15–30 s, marqué DEMO) ·
`vendre` (réglages offre + page de vente + contenus de prospection) ·
`lab` (Product Lab V1) · `builder` (Script Builder V1) ·
`tracker` (Content Tracker V1) · `winners` (analytics V1).

## 4. Conventions de code
- **État** : variables globales chargées depuis `store` ; après chaque mutation → `store.set(...)` puis re-render de la section concernée.
- **Rendu** : fonctions `renderX()` sans framework (innerHTML + template literals). `renderAll()` les appelle toutes. Toujours échapper les données utilisateur avec `esc()`.
- **Événements** : délégation unique `document.addEventListener("click", ...)` sur `[data-action]` → map `ACTIONS`; `change` sur `[data-change]`. **Ne jamais** utiliser d'attributs `onclick` inline.
- Formulaires : listeners `submit` directs (`#product-form`, `#video-form`, `#client-form`, `#prospect-form`, `#demo-form`).
- Générateurs : banques de templates FR/EN (`HOOKS`, `IDEAS`, `MINIS`, `BUILD`) pour la V1 ; moteur V2 FR-only : `genClientPack(client)`, `genDemoV2(name,type,offer)`, `genSalesContent()`, `clientHooks(c)` — interpolation via objets contexte, jamais de placeholder `{...}` non résolu.
- Utilitaires clés : `uid`, `esc`, `num/int`, `fmtN/fmtE`, `sample/shuffle/pick1`, `safeUrl`, `locTag`, `asciiSlug`, `toast`, `copyText`.
- Export pack client : `packPlainText` (presse-papier) + `packHTMLDoc` (Blob HTML téléchargeable, printable → PDF).

## 5. Principes produit (à respecter)
- **Zéro fausse promesse** : pas de viralité/vues/ventes « garanties », pas de faux témoignages. Le texte honnête est vérifié par test (`claims honnêtes`).
- Contenu **faceless** : plans mains/produits/ambiance, captures d'écran, jamais d'exigence d'apparition du client.
- L'utilisateur final **ne code pas** : tout réglage externe = champ simple (ex. lien de paiement dans « Vendre »).
- Rétro-compatibilité des imports JSON (V1 → V2 tolérante aux clés manquantes).

## 6. Lancer / tester
```bash
# servir (preview Arena attend 0.0.0.0:8080)
cd teste-et-propre && python3 -m http.server 8080 --bind 0.0.0.0
# vérification syntaxe JS
python3 -c "import re;open('/tmp/app.js','w').write(re.search(r'<script>([\s\S]*)</script>', open('index.html').read()).group(1))"
node --check /tmp/app.js
# tests fonctionnels (harnais Node avec faux DOM) — voir CONTINUE-PROMPT.txt
node /tmp/harness.js   # 42 tests attendus : 42 PASS
```
Le harnais stubbe `localStorage`, `document`, `navigator`, `window`, puis exécute le `<script>` de la page + assertions (génération, métriques, persistence, classements, honnêteté des claims). **Relancer le harnais après toute modif.**

## 7. Idées d'évolution (non demandées, optionnelles)
- Partage du lien de la page de vente en page réellement publique (page statique dédiée).
- Historique des livraisons par client ; facture PDF simple.
- Relances automatiques (date de follow-up → rappel sur le dashboard).
- Multi-prix par client (pack choisi à la commande, figé dans la fiche).
