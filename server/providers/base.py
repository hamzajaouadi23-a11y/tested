"""Base Provider — contrat unique :
id, label, kind, implemented, mock, requires, costly, configured(), test(), health(), safe_http().

NE JAMAIS coder en dur un provider dans la logique métier : les services passent par le registre.
"""
import json
import time
import urllib.error
import urllib.request


class Provider:
    id = "base"
    label = "Provider"
    kind = "generic"        # TEXT | RESEARCH | IMAGE | VOICE | VIDEO | STORAGE | SOCIAL | ANALYTICS | SCHEDULER
    implemented = False     # l'adaptateur est-il écrit ?
    mock = True             # produit-il de fausses données ?
    requires = []           # variables d'environnement requises (noms seulement)
    costly = False          # peut coûter de l'argent ?
    quality = "standard"    # "fallback" pour les secours locaux

    def configured(self):
        from .. import config
        return all(config.secret_configured(k) for k in self.requires)

    def test(self):
        """Test RÉEL du provider. Retourne dict(ok, detail, latency_ms)."""
        if not self.implemented:
            return {"ok": False, "detail": "adaptateur non implémenté", "latency_ms": 0}
        if self.requires and not self.configured():
            return {"ok": False, "detail": "non configuré (clés manquantes : " + ", ".join(self.requires) + ")", "latency_ms": 0}
        return {"ok": True, "detail": "configuré", "latency_ms": 0}

    def health(self):
        t = self.test()
        if not self.implemented:
            s = "not_implemented"
        elif self.mock:
            s = "mock"
        elif not self.configured():
            s = "not_configured"
        elif t["ok"]:
            s = "ok"
        else:
            s = "error"
        return {"id": self.id, "label": self.label, "kind": self.kind, "implemented": self.implemented,
                "mock": self.mock, "requires": self.requires, "costly": self.costly,
                "configured": self.configured(), "status": s, "test": t, "quality": self.quality}

    # -------- HTTP robuste : retries intelligents (429 / 5xx temporaires / timeouts), jamais infinis --------
    def safe_http(self, url, payload=None, headers=None, method=None, timeout=25, retries=2, raw=False):
        headers = dict(headers or {})
        data = None
        if payload is not None:
            data = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        attempt, last_err = 0, None
        while attempt <= retries:
            attempt += 1
            t0 = time.time()
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method=method or ("POST" if data else "GET"))
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    body = r.read()
                    latency = int((time.time() - t0) * 1000)
                    if raw:
                        return {"ok": True, "raw": body, "status": r.status, "latency_ms": latency, "headers": dict(r.headers)}
                    return {"ok": True, "json": json.loads(body.decode("utf-8", "replace")), "status": r.status, "latency_ms": latency}
            except urllib.error.HTTPError as e:
                code = e.code
                body = b""
                try:
                    body = e.read()[:400]
                except Exception:
                    pass
                last_err = {"ok": False, "status": code, "detail": body.decode("utf-8", "replace")[:300]}
                if code == 429 or 500 <= code < 600:
                    time.sleep(min(2 ** attempt, 8))  # backoff borné
                    continue
                return last_err  # erreur définitive (4xx autre que 429) : pas de retry
            except Exception as e:  # timeout, DNS, SSL…
                last_err = {"ok": False, "status": 0, "detail": str(e)[:300]}
                time.sleep(min(2 ** attempt, 8))
        return last_err
