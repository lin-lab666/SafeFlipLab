"""Verify this release snapshot against PUBLICATION_MANIFEST.csv.

Two scopes are reported explicitly:

  * **v1.0 research package** — every row recorded in
    ``PUBLICATION_MANIFEST.csv`` must exist and match byte-for-byte
    (size + SHA-256), *except* the files listed in ``V11_UPDATED``, which the
    v1.1 engineering pass intentionally edited. Their original v1.0 hashes stay
    recorded in the frozen manifest and in ``docs/FINAL_ARTIFACT_HASHES.csv``;
    the manifest itself is never rewritten.
  * **v1.1 engineering scope** — files added after v1.0 (docs, CI, examples,
    the new regression test) are allowed when they match ``POST_V1_PATTERNS``;
    anything else on disk that is not in the manifest is a hard FAIL (EXTRA).

Runtime artefacts are ignored exactly like ``.gitignore`` treats them
(``runs/``, ``v02/runs/``, caches, egg-info, build outputs): they are not part
of either scope.

Run from anywhere:  python scripts/verify_publication.py

Note: the generator (build_publication_manifest.py) lives in the release
audit directory, not in this package; regeneration is a release-time action.
The manifest is frozen at v1.0 (commit ``baee8bec…``); see
``PUBLICATION_SCOPE.md``.
"""
from __future__ import annotations

import csv
import fnmatch
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "PUBLICATION_MANIFEST.csv"

V1_COMMIT = "baee8becb796b0fe4f067a0c4cb5fbac237c58b9"

# Self-referential files are not listed in the manifest itself.
SELF_EXCLUDE = {
    (ROOT / "PUBLICATION_MANIFEST.csv").relative_to(ROOT).as_posix(),
    (ROOT / "scripts" / "verify_publication.py").relative_to(ROOT).as_posix(),
}

# v1.1 (GH-2 engineering pass) intentionally updated these v1.0 files.
# Each entry states why; the v1.0 bytes remain recorded in the frozen manifest.
V11_UPDATED: dict[str, str] = {
    "README.md": "P1-02/P1-04: test side-effect policy + executable V02 test command",
    "README.zh-CN.md": "P1-02/P1-04: same fixes as README.md (Chinese)",
    "CITATION.cff": "P1-03: repository-code points at the published repository",
    "pyproject.toml": "P2: urls/classifiers/keywords/test extra; setuptools>=77 for PEP 639 license",
    "requirements.txt": "P2: state parity with the pyproject 'sim' extra",
    ".gitignore": "P2: build/coverage artefacts",
    "safefliplab/experiments.py": "P1-01: formal refusal before any filesystem side effect",
    "safefliplab/doctor.py": "DOCTOR-01: budget check is strictly read-only (no runs/ creation)",
    "tests/test_report_cli.py": "P1-01: CLI formal guard mocks the scheduler (no side effects)",
    "scripts/build_final_manifest.py": "P2: ROOT overridable via SAFEFLIPLAB_ROOT",
    "scripts/independent_verify_all.py": "P2: ROOT overridable via SAFEFLIPLAB_ROOT",
}

# v1.1 files that may appear on disk without being part of the v1.0 manifest.
# Keep this list as narrow as possible: named documents / directories only.
POST_V1_PATTERNS = [
    "PUBLICATION_SCOPE.md",
    "INSTALLATION.md",
    "QUICKSTART.md",
    "ARCHITECTURE.md",
    "EXAMPLES.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "TESTING.md",
    "DATA_AVAILABILITY.md",
    "CHANGELOG.md",
    ".github/**",
    "examples/**",
    "docs/assets/architecture.svg",
    "docs/assets/offline-demo-output.txt",
    "tests/test_formal_no_side_effects.py",
    "tests/test_doctor_readonly.py",
]

# Directories that are never part of either scope (mirror .gitignore).
IGNORED_DIR_NAMES = {
    ".venv", "venv", "__pycache__", ".git", ".workbuddy",
    ".pytest_cache", "build", "dist", "htmlcov",
}
IGNORED_TOP_DIRS = {"runs", "v02/runs"}
IGNORED_FILES = {".coverage"}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _ignored(rel: str, parts: tuple[str, ...]) -> bool:
    if any(p in IGNORED_DIR_NAMES for p in parts):
        return True
    if any(p.endswith(".egg-info") for p in parts):
        return True
    if rel in IGNORED_FILES:
        return True
    return any(rel == d or rel.startswith(d + "/") for d in IGNORED_TOP_DIRS)


def _post_v1(rel: str) -> bool:
    for pat in POST_V1_PATTERNS:
        if pat.endswith("/**"):
            if rel.startswith(pat[:-3] + "/"):
                return True
        elif fnmatch.fnmatchcase(rel, pat):
            return True
    return False


def main() -> int:
    if not MANIFEST.is_file():
        print(f"PUBLICATION MANIFEST CHECK: FAIL (missing {MANIFEST})")
        return 1

    with open(MANIFEST, newline="", encoding="utf-8") as fh:
        rows = [(r["relpath"], int(r["bytes"]), r["sha256"]) for r in csv.DictReader(fh)]

    fails: list[str] = []
    v1_verified = 0
    updated_seen: list[str] = []

    # 1) v1.0 rows: byte-exact unless intentionally updated in v1.1.
    for rel, size, want in rows:
        p = ROOT / rel
        if not p.is_file():
            fails.append(f"MISSING: {rel}")
            continue
        if rel in V11_UPDATED:
            updated_seen.append(rel)
            continue
        st = p.stat()
        if st.st_size != size:
            fails.append(f"BYTES: {rel} manifest={size} disk={st.st_size}")
        got = sha256_of(p)
        if got != want:
            fails.append(f"HASH: {rel} manifest={want[:16]}... disk={got[:16]}...")
        v1_verified += 1

    for rel in sorted(set(V11_UPDATED) - set(updated_seen)):
        # A whitelisted update must still exist in the manifest (it is a v1.0 file).
        fails.append(f"STALE-WHITELIST: {rel} is in V11_UPDATED but not in the manifest")

    # 2) disk set: manifest rows + self-tooling + v1.1 additions only.
    disk = {
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*")
        if p.is_file()
        and not _ignored(p.relative_to(ROOT).as_posix(), p.parts)
    }
    listed = {rel for rel, _, _ in rows}
    added_v11 = {rel for rel in disk - listed - SELF_EXCLUDE if _post_v1(rel)}
    for extra in sorted(disk - listed - SELF_EXCLUDE - added_v11):
        fails.append(f"EXTRA (not in manifest or v1.1 scope): {extra}")
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
    print("PUBLICATION MANIFEST CHECK (v1.0 research package + v1.1 engineering scope): PASS")
    print(f"  v1.0 rows verified byte-exact: {v1_verified}/{len(rows)}")
    print(f"  v1.1 intentionally updated: {len(updated_seen)}")
    for rel in sorted(updated_seen):
        print(f"    ~ {rel}  ({V11_UPDATED[rel]})")
    print(f"  v1.1 added files (post-v1.0): {len(added_v11)}")
    for rel in sorted(added_v11):
        print(f"    + {rel}")
    print(f"  manifest rows={len(rows)}, manifest bytes={total_bytes}  "
          f"(frozen v1.0 = commit {V1_COMMIT[:7]})")
    print("EXIT CODE = 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
