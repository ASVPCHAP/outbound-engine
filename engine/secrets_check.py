"""Blocks commits that contain key-shaped strings. Run by .githooks/pre-commit.

    python -m engine.secrets_check            # checks staged files
    python -m engine.secrets_check FILE...    # checks the given files
"""
import re
import subprocess
import sys

PATTERNS = [
    ("Anthropic key", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("Airtable token", re.compile(r"pat[A-Za-z0-9]{14}\.[a-f0-9]{64}")),
    ("Bearer token", re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}")),
    ("Key assignment", re.compile(
        r"^\s*[A-Z_]*(KEY|SECRET|TOKEN|PAT)\s*=\s*['\"]?[A-Za-z0-9_\-\.]{16,}['\"]?\s*$",
        re.MULTILINE)),
]


def find_secrets(text):
    return [label for label, rx in PATTERNS if rx.search(text)]


def main(paths):
    if not paths:
        out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                             capture_output=True, text=True, check=True).stdout
        paths = out.split()
    bad = []
    for p in paths:
        try:
            text = open(p, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        bad += [f"{p}: {label}" for label in find_secrets(text)]
    if bad:
        print("Commit blocked, possible secrets:\n  " + "\n  ".join(bad))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
