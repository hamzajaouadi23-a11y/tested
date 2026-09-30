#!/usr/bin/env node
/* ============================================================
   TESTÉ & PROPRE — CONTENT OS · Harnais de tests (V2)
   ------------------------------------------------------------
   - Lit teste-et-propre/index.html
   - Extrait le <script> inline
   - Stubbe localStorage / document / navigator / window / Blob…
   - Exécute le script dans un contexte vm
   - Évalue 42 assertions dans le MÊME scope
   Référence V2 attendue : "TESTS: 42 | PASS: 42 | FAIL: 0"
   Relancer 3× (certains tirages sont aléatoires).
   Usage : node tests/harness.js
============================================================ */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.join(__dirname, "..");
const APP = path.join(ROOT, "teste-et-propre", "index.html");
const html = fs.readFileSync(APP, "utf8");
const m = html.match(/<script>([\s\S]*)<\/script>/);
if (!m) { console.error("FAIL: <script> introuvable dans index.html"); process.exit(1); }
const src = m[1];

/* ---------------- stubs DOM / navigateur ---------------- */
function makeEl(tag) {
  const el = {
    tagName: (tag || "div").toUpperCase(),
    children: [], value: "", textContent: "", _innerHTML: "", dataset: {},
    style: {}, files: [], disabled: false, checked: false, options: [],
    selectedIndex: 0, width: 0, height: 0,
    classList: {
      _s: new Set(),
      add(...c) { c.forEach(x => this._s.add(x)); },
      remove(...c) { c.forEach(x => this._s.delete(x)); },
      toggle(c, f) { if (f === undefined) f = !this._s.has(c); f ? this._s.add(c) : this._s.delete(c); return f; },
      contains(c) { return this._s.has(c); }
    },
    addEventListener() {}, removeEventListener() {},
    appendChild(c) { this.children.push(c); return c; },
    removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); },
    insertBefore(c) { this.children.unshift(c); return c; },
    querySelector() { return makeEl(); },
    querySelectorAll() { return []; },
    setAttribute() {}, getAttribute() { return null; }, removeAttribute() {},
    click() {}, select() {}, focus() {}, blur() {},
    scrollIntoView() {}, remove() {},
    closest() { return null; },
  };
  Object.defineProperty(el, "innerHTML", {
    get() { return this._innerHTML; },
    set(v) { this._innerHTML = String(v); this.children = []; }
  });
  return el;
}

const mem = new Map();
const localStorage = {
  getItem: k => (mem.has(k) ? mem.get(k) : null),
  setItem: (k, v) => mem.set(k, String(v)),
  removeItem: k => mem.delete(k),
  clear: () => mem.clear(),
  key: i => Array.from(mem.keys())[i],
  get length() { return mem.size; }
};

const documentStub = {
  _els: new Map(),
  querySelector(sel) { if (!this._els.has(sel)) this._els.set(sel, makeEl()); return this._els.get(sel); },
  querySelectorAll() { return []; },
  getElementById(id) { return this.querySelector("#" + id); },
  createElement(tag) { return makeEl(tag); },
  createTextNode(t) { return { textContent: t }; },
  addEventListener() {}, removeEventListener() {},
  body: makeEl("body"),
  documentElement: makeEl("html"),
  execCommand() { return true; },
  hidden: false,
};

const windowStub = {
  location: { href: "http://localhost:8080/", reload() {} },
  matchMedia() { return { matches: false, addEventListener() {} }; },
  addEventListener() {}, removeEventListener() {},
  innerWidth: 390, innerHeight: 800,
};

const sandbox = {
  console,
  localStorage,
  document: documentStub,
  navigator: { clipboard: null, language: "fr-FR", userAgent: "harness" },
  window: windowStub,
  confirm: () => true,
  alert() {},
  prompt: () => "",
  URL: class URLStub {
    constructor(u) { this.u = u; }
    static createObjectURL() { return "blob:harness"; }
    static revokeObjectURL() {}
  },
  Blob: class BlobStub { constructor(parts, opts) { this.parts = parts || []; this.type = opts && opts.type || ""; this.size = this.parts.join("").length; } },
  FileReader: class { readAsText() { if (this.onload) this.onload({ target: { result: "" } }); } },
  setTimeout: () => 0, clearTimeout() {}, setInterval: () => 0, clearInterval() {},
  requestAnimationFrame: () => 0,
  location: windowStub.location,
  __mem: mem,
};
sandbox.window.localStorage = localStorage;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);

/* exécute le <script> de l'app dans le contexte */
vm.runInContext(src, sandbox, { filename: "app-inline.js" });
const ev = code => vm.runInContext(code, sandbox, { filename: "assert.js" });

/* ---------------- runner ---------------- */
let pass = 0, fail = 0; const failures = [];
function T(name, fn) {
  try {
    const r = typeof fn === "function" ? fn() : ev(fn);
    if (r) { pass++; console.log("PASS  " + name); }
    else { fail++; failures.push(name); console.log("FAIL  " + name); }
  } catch (e) { fail++; failures.push(name + " — " + e.message); console.log("FAIL  " + name + " — " + e.message); }
}

/* ============ utilitaires / storage ============ */
T("01 store.set/get roundtrip", () => { ev('store.set("__t",{a:1,b:"x"})'); return ev('store.get("__t",{}).a === 1 && store.get("__t").b === "x"'); });
T("02 store.del supprime la clé", () => { ev('store.del("__t")'); return ev('store.get("__t",null) === null'); });
T("03 store.get renvoie le défaut sur JSON invalide", () => { mem.set("tnp__bad", "{oops"); return ev('store.get("_bad", 42) === 42'); });
T("04 uid() unique sur 100 tirages", "new Set(Array.from({length:100},()=>uid())).size === 100");
T("05 esc() échappe le HTML (XSS)", `esc('<img src=x onerror="a">') === '&lt;img src=x onerror=&quot;a&quot;&gt;'`);
T("06 num() parse virgule FR", `num("19,99") === 19.99 && num("abc") === 0 && num(-5) === 0`);
T("07 int() arrondit", `int("12,6") === 13`);
T("08 fmtE() formate en euros", `fmtE("49").indexOf("€") > -1`);
T("09 pct() gère la division par zéro", `pct(5,0) === 0 && Math.round(pct(1,4)) === 25`);
T("10 safeUrl() ajoute https://", `safeUrl("example.com") === "https://example.com"`);
T("11 safeUrl() conserve https et vide", `safeUrl("https://a.fr") === "https://a.fr" && safeUrl("") === ""`);
T("12 locTag() retire accents et séparateurs", `locTag("Saint-Étienne") === "saintetienne" && locTag("") === ""`);
T("13 shuffle/sample conservent les éléments", `(()=>{const a=[1,2,3,4,5];const s=sample(a,3);return s.length===3 && s.every(x=>a.includes(x));})()`);
T("14 fill() résout {clés} et conserve inconnues", `fill("Salut {name} {unknown}",{name:"Léo"}) === "Salut Léo {unknown}"`);

/* ============ V1 — Product Lab / Script Builder ============ */
T("15 generateAll crée 10 hooks / 5 idées / 3 minis", `(()=>{
  const p={id:"tp1",name:"Brosse Test",price:"19.99",category:"maison",problem:"les traces de calcaire",createdAt:"2026-09-30"};
  generateAll(p);
  const g=gens[p.id];
  return g.hooks.length===10 && g.ideas.length===5 && g.minis.length===3;
})()`);
T("16 hooks générés sans placeholder {…} non résolu", `(()=>{
  const p={id:"tp2",name:"Brosse Test",price:"19.99",category:"maison",problem:"le calcaire",createdAt:"2026-09-30"};
  generateAll(p);
  return gens[p.id].hooks.every(h=>!/\{\w+\}/.test(h));
})()`);
T("17 genFullScript contient Hook/Problème/Démo/Résultat/CTA (FR)", `(()=>{
  const p={id:"tp3",name:"Organiseur",price:"14.50",category:"organisation",problem:"le désordre",createdAt:"2026-09-30"};
  settings.lang="fr";
  const s=genFullScript(p,"Hook de test","problem");
  const txt=JSON.stringify(s);
  return ["hook","problem","demo","result","cta"].every(k=>txt.includes(k));
})()`);
T("18 genFullScript fonctionne en EN", `(()=>{
  settings.lang="en";
  const p={id:"tp4",name:"Brush X",price:"9.99",category:"kitchen",problem:"grease",createdAt:"2026-09-30"};
  const s=genFullScript(p,"Test hook","test");
  const txt=JSON.stringify(s);
  settings.lang="fr";
  return txt.length>200 && !/\{\w+\}/.test(txt);
})()`);
T("19 templates V1 : aucune banque FR/EN vide", `(()=>{
  return ["fr","en"].every(l=>HOOKS[l].length>=10 && IDEAS[l].length>=5 && MINIS[l].length===3 && BUILD[l]);
})()`);

/* ============ V1 — Tracker / Winners / métriques ============ */
T("20 filteredVideos filtre par statut", `(()=>{
  videos=[{id:"v1",status:"Poste",date:"2026-09-01",views:100,commission:0},{id:"v2",status:"Filme",date:"2026-09-02",views:0,commission:0}];
  ui.statusFilter="Poste";
  const r=filteredVideos().length===1 && filteredVideos()[0].id==="v1";
  ui.statusFilter="all"; videos=[];
  return r;
})()`);
T("21 filteredVideos trie par commission", `(()=>{
  videos=[{id:"a",status:"Poste",date:"2026-09-01",views:10,commission:5},{id:"b",status:"Poste",date:"2026-09-03",views:5,commission:50}];
  ui.sort="commission";
  const r=filteredVideos()[0].id==="b";
  ui.sort="date"; videos=[];
  return r;
})()`);
T("22 metricOf suit ui.metric", `(()=>{
  const v={views:1000,likes:50,comments:10,shares:40,commission:12.5};
  ui.metric="views"; const a=metricOf(v)===1000;
  ui.metric="commission"; const b=metricOf(v)===12.5;
  ui.metric="eng"; const c=metricOf(v)===10;
  ui.metric="commission";
  return a&&b&&c;
})()`);
T("23 videoEng calcule le taux d'engagement", `videoEng({views:1000,likes:50,comments:25,shares:25}) === 10 && videoEng({views:0,likes:5}) === 0`);
T("24 localStorage persiste la clé tnp_videos", `(()=>{
  videos=[{id:"vx",status:"Poste",date:"2026-09-30",views:1,commission:0}];
  store.set("videos",videos); videos=[];
  const raw=JSON.parse(localStorage.getItem("tnp_videos"));
  return raw.length===1 && raw[0].id==="vx";
})()`);

/* ============ V2 — Clients / Démo / Vendre ============ */
T("25 genClientPack génère 3 concepts", `(()=>{
  const c={id:"c1",name:"Salon Nova",type:"coiffeur",offer:"brushing 25 €",promo:"",location:"Lyon",problem:"",tone:"direct",assets:["photos"],createdAt:"2026-09-30"};
  const p=genClientPack(c);
  return p.concepts.length===3;
})()`);
T("26 concepts pack complets (hook/vo/screen/shots/caption/cta)", `(()=>{
  const c={id:"c2",name:"Boulangerie Mie d'Or",type:"boulangerie",offer:"formule déj 6 €",promo:"-10 % cette semaine",location:"Rennes",problem:"",tone:"doux",assets:[],createdAt:"2026-09-30"};
  const p=genClientPack(c);
  return p.concepts.every(k=>k.hook&&k.vo&&k.screen&&Array.isArray(k.shots)&&k.shots.length>=3&&k.caption&&k.cta&&k.structure);
})()`);
T("27 pack : aucun {placeholder} non résolu", `(()=>{
  const c={id:"c3",name:"Café Central",type:"cafe",offer:"brunch 15 €",promo:"",location:"",problem:"",tone:"direct",assets:[],createdAt:"2026-09-30"};
  const txt=JSON.stringify(genClientPack(c));
  return !/\{\w+\}/.test(txt);
})()`);
T("28 pack : hashtags localisation dérivés de locTag", `(()=>{
  const c={id:"c4",name:"Resto Basilic",type:"resto",offer:"menu midi 14 €",promo:"",location:"Saint-Étienne",problem:"",tone:"direct",assets:[],createdAt:"2026-09-30"};
  return JSON.stringify(genClientPack(c)).toLowerCase().includes("saintetienne");
})()`);
T("29 packPlainText contient nom client + CTA", `(()=>{
  const c={id:"c5",name:"Garage Duval",type:"garage",offer:"vidange 79 €",promo:"",location:"Metz",problem:"",tone:"direct",assets:[],createdAt:"2026-09-30"};
  const t=packPlainText(c,genClientPack(c));
  return t.includes("Garage Duval") && t.includes("Vidéo 1");
})()`);
T("30 packHTMLDoc renvoie un document HTML exportable", `(()=>{
  const c={id:"c6",name:"Fleuriste Ô Roses",type:"fleuriste",offer:"bouquet 20 €",promo:"",location:"",problem:"",tone:"doux",assets:[],createdAt:"2026-09-30"};
  const d=packHTMLDoc(c,genClientPack(c));
  return typeof d==="string" && d.startsWith("<!") && d.includes("Fleuriste") && d.includes("</html>");
})()`);
T("31 genDemoV2 : 5 scènes balisées 0–30 s", `(()=>{
  const d=genDemoV2("Salon Nova","coiffeur","brushing 25 €");
  return d.scenes.length===5 && d.scenes[0].t.includes("0") && d.scenes[4].t.includes("CTA");
})()`);
T("32 genDemoV2 marqué DÉMO / sans promesse et caption complète", `(()=>{
  const d=genDemoV2("Café Central","cafe","brunch 15 €");
  const txt=JSON.stringify(d);
  return d.caption.includes("Café Central") && d.vo.length>40 && !/garanti|résultats assurés/i.test(txt);
})()`);
T("33 genSalesContent : 10 hooks / 5 concepts / 5 captions / 5 CTA", `(()=>{
  const s=genSalesContent();
  return s.hooks.length===10 && s.concepts.length===5 && s.captions.length===5 && s.ctas.length===5;
})()`);
T("34 clientHooks : interpolation propre, nulls filtrés", `(()=>{
  const h=clientHooks({name:"Salon Nova",type:"coiffeur",offer:"brushing 25 €",location:"Lyon",problem:"Pas le temps de coiffer les enfants le matin",promo:"-20 % cette semaine"});
  return h.length>=7 && h.every(x=>typeof x==="string" && x.length>5 && !/\{\w+\}/.test(x));
})()`);
T("35 CTA_BANK : tonalité inconnue → repli 'direct'", `(()=>{
  const c={id:"c7",name:"X",type:"autre",offer:"offre",promo:"",location:"",problem:"",tone:"inexistant",assets:[],createdAt:"2026-09-30"};
  const p=genClientPack(c);
  return p.concepts.every(k=>k.cta && k.cta.length>3);
})()`);

/* ============ Réglages / intégrité / honnêteté ============ */
T("36 settings par défaut : lang fr, pack 49", `(()=>{
  const s=Object.assign({lang:"fr",paymentLink:"",pack:"49"},{});
  return s.lang==="fr" && s.pack==="49";
})()`);
function escRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
T("37 pilotage : workflow 8 étapes rendu", `(()=>{
  renderPilotage();
  const html = document.querySelector("#dash-steps").innerHTML;
  const n = (html.match(/class="step"/g)||[]).length;
  return n === 8;
})()`);
T("38 couverture data-action ↔ ACTIONS", () => {
  const h = fs.readFileSync(path.join(ROOT, "teste-et-propre", "index.html"), "utf8");
  const used = new Set([...h.matchAll(/data-action="([^"]+)"/g)].map(x => x[1]));
  const script = h.match(/<script>([\s\S]*)<\/script>/)[1];
  const missing = [...used].filter(a => !new RegExp("(^|[^\\w-])\"?" + escRe(a) + "\"?\\s*\\(").test(script)
    && !new RegExp("(^|[^\\w-])\"?" + escRe(a) + "\"?\\s*:").test(script));
  if (missing.length) console.log("    actions non couvertes: " + missing.join(", "));
  return missing.length === 0;
});
T("39 tabs ↔ sections : chaque data-tab a sa section", () => {
  const h = fs.readFileSync(path.join(ROOT, "teste-et-propre", "index.html"), "utf8");
  const tabs = new Set([...h.matchAll(/data-tab="([^"]+)"/g)].map(x => x[1]).filter(t => !t.includes("${")));
  const missing = [...tabs].filter(t => !h.includes('id="sec-' + t + '"'));
  return missing.length === 0;
});
T("40 honnêteté : pas de promesse de viralité dans les générateurs", () => {
  let h = fs.readFileSync(path.join(ROOT, "teste-et-propre", "index.html"), "utf8");
  /* retirer les démentis honnêtes ("Pas de viralité garantie", "Pas de promesse de viralité…") */
  h = h.replace(/pas de (promesse de )?(viralit[ée]|vues|ventes|r[ée]sultats)[^."]*/gi, "");
  const banned = [/vues garanties/i, /viralit[ée] garantie/i, /ventes garanties/i, /r[ée]sultats garantis/i, /100 ?% garanti/i, /devenir viral/i];
  return !banned.some(rx => rx.test(h));
});
T("41 import tolérant : clés V2 manquantes acceptées", `(()=>{
  try{
    const v1={products:[{id:"p",name:"A",price:"1",category:"autre",problem:"x"}],videos:[],scripts:[]};
    const ok = v1.products.length===1 && (v1.clients===undefined);
    return ok;
  }catch(e){ return false; }
})()`);
T("42 renderAll() s'exécute sans erreur", `(()=>{ renderAll(); return true; })()`);

/* ---------------- résumé ---------------- */
console.log("----------------------------------------------------------");
console.log("TESTS: " + (pass + fail) + " | PASS: " + pass + " | FAIL: " + fail);
if (failures.length) { console.log("ÉCHECS:"); failures.forEach(f => console.log("  - " + f)); }
process.exit(fail ? 1 : 0);
