"""Scan anti-secrets — exécuté par les tests et tools/precheck.sh avant chaque commit.

Bloque tout ce qui ressemble à un token réel dans les fichiers suivis par git.
"""
import os
import re
import subprocess
import sys

PATTERNS = {
    "google_api_key": r"AIza[0-9A-Za-z_\-]{35}",
    "github_token": r"gh[pousr]_[0-9A-Za-z]{20,}",
    "openai_key": r"sk-[0-9A-Za-z]{20,}",
    "anthropic_key": r"sk-ant-[0-9A-Za-z_\-]{20,}",
    "aws_key": r"AKIA[0-9A-Z]{16}",
    "google_oauth": r"ya29\.[0-9A-Za-z_\-]{20,}",
    "slack_token": r"xox[baprs]-[0-9A-Za-z\-]{10,}",
    "elevenlabs_key": r"sk_[0-9a-f]{32,}",
    "private_key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "generic_assignment": r"(?:api[_-]?key|secret|token)\s*[=:]\s*['\"][0-9A-Za-z_\-]{30,}['\"]",
}

ALLOW_FILES = {".env.example", "secrets_scan.py", "CONTINUE-PROMPT.txt"}
ALLOW_PATTERNS = [r"AIza-your", r"xxx+", r"\.\.\.", r"example", r"placeholder", r"<.*>", r"VOTRE_"]


def _tracked_files(root):
    try:
        out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, timeout=30)
        if out.returncode == 0:
            return [os.path.join(root, f) for f in out.stdout.splitlines() if f.strip()]
    except Exception:
        pass
    files = []
    for dp, dn, fn in os.walk(root):
        if any(x in dp for x in ("/.git", "/node_modules", "/__pycache__", "/.venv")):
            continue
        files.extend(os.path.join(dp, f) for f in fn)
    return files


def scan(root):
    findings = []
    for path in _tracked_files(root):
        base = os.path.basename(path)
        if base in ALLOW_FILES or base.endswith((".png", ".jpg", ".mp4", ".mp3", ".zip", ".pyc", ".sqlite")):
            continue
        try:
            txt = open(path, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for name, pat in PATTERNS.items():
            for m in re.finditer(pat, txt):
                snippet = m.group(0)[:60]
                if any(re.search(a, snippet, re.IGNORECASE) for a in ALLOW_PATTERNS):
                    continue
                line = txt[:m.start()].count("\n") + 1
                findings.append({"file": os.path.relpath(path, root), "line": line, "type": name, "match": snippet[:24] + "…"})
    return findings


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = scan(root)
    if out:
        print("⛔ SECRETS POTENTIELS DÉTECTÉS — commit INTERDIT :")
        for f in out:
            print("  - %s:%d [%s] %s" % (f["file"], f["line"], f["type"], f["match"]))
        sys.exit(1)
    print("✅ Scan secrets : aucun secret détecté")
