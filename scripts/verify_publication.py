"""Verify this release snapshot against PUBLICATION_MANIFEST.csv.

Checks (any failure exits 1):
  1. every manifest row: file exists, bytes match, SHA-256 matches
  2. no extra/missing files on disk vs the manifest
     (excluding the manifest itself and this verifier)

Run from anywhere:  python scripts/verify_publication.py

Note: the generator (build_publication_manifest.py) lives in the release
audit directory, not in this package; regeneration is a release-time action.
"""
from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "PUBLICATION_MANIFEST.csv"

# Self-referential files are not listed in the manifest itself.
SELF_EXCLUDE = {
    (ROOT / "PUBLICATION_MANIFEST.csv").relative_to(ROOT).as_posix(),
    (ROOT / "scripts" / "verify_publication.py").relative_to(ROOT).as_posix(),
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not MANIFEST.is_file():
        print(f"PUBLICATION MANIFEST CHECK: FAIL (missing {MANIFEST})")
        return 1

    with open(MANIFEST, newline="", encoding="utf-8") as fh:
        rows = [(r["relpath"], int(r["bytes"]), r["sha256"]) for r in csv.DictReader(fh)]

    fails: list[str] = []

    # 1) row-by-row: existence + bytes + hash
    for rel, size, want in rows:
        p = ROOT / rel
        if not p.is_file():
            fails.append(f"MISSING: {rel}")
            continue
        st = p.stat()
        if st.st_size != size:
            fails.append(f"BYTES: {rel} manifest={size} disk={st.st_size}")
        got = sha256_of(p)
        if got != want:
            fails.append(f"HASH: {rel} manifest={want[:16]}... disk={got[:16]}...")

    # 2) set equality (disk vs manifest), excluding self-referential tooling
    disk = {
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*")
        if p.is_file()
        and not any(part in {".venv", "__pycache__", ".git", ".workbuddy"} for part in p.parts)
    }
    listed = {rel for rel, _, _ in rows}
    for extra in sorted(disk - listed - SELF_EXCLUDE):
        fails.append(f"EXTRA (not in manifest): {extra}")
    for missing in sorted(listed - disk):
        fails.append(f"MANIFEST-ONLY (file absent): {missing}")

    if fails:
        print(f"PUBLICATION MANIFEST CHECK: FAIL ({len(fails)} problem(s))")
        for f in fails[:50]:
            print(f"  {f}")
        if len(fails) > 50:
            print(f"  ... and {len(fails) - 50} more")
        return 1

    total_bytes = sum(size for _, size, _ in rows)
    print(f"PUBLICATION MANIFEST CHECK: PASS  (files={len(rows)}, bytes={total_bytes})")
    print("EXIT CODE = 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
