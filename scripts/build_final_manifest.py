"""Build (and verify) the final delivery manifest artefacts.

Read-only w.r.t. the project's scientific data: it hashes existing files and
rewrites only derived manifest artefacts.

    .venv\\Scripts\\python.exe scripts/build_final_manifest.py          # regenerate
    .venv\\Scripts\\python.exe scripts/build_final_manifest.py --check  # verify only

Outputs
-------
* ``docs/FINAL_ARTIFACT_HASHES.csv``  — per-file SHA-256 (authoritative file set)
* ``docs/FINAL_ARTIFACT_COUNTS.md``   — **generated** counts summary
* the ``GENERATED-COUNTS`` block inside ``docs/FINAL_DELIVERY_MANIFEST.md``

Why this exists
---------------
The first version of the manifest kept file counts and byte totals as *hand-written*
text. The file set changed between edits, so the document ended up asserting three
different totals (186 / 187 / 188). Hand-maintained counts in a delivery manifest
are a defect class of their own: they will drift. Counts are therefore now
generated from the CSV, and ``--check`` fails if the document ever disagrees.
"""
from __future__ import annotations

import csv
import hashlib
import os
import re
import sys
from pathlib import Path

# GH-2: internal audit tool. Defaults to the repository root; override with
# SAFEFLIPLAB_ROOT when the project tree lives elsewhere. NOTE: running without
# --check rewrites the derived manifests under docs/, so use it only in a full
# project checkout (never in the published snapshot, whose docs/ are frozen).
ROOT = Path(os.environ.get("SAFEFLIPLAB_ROOT", str(Path(__file__).resolve().parent.parent)))
MANIFEST = ROOT / "docs" / "FINAL_DELIVERY_MANIFEST.md"
CSV_PATH = ROOT / "docs" / "FINAL_ARTIFACT_HASHES.csv"
COUNTS_PATH = ROOT / "docs" / "FINAL_ARTIFACT_COUNTS.md"

BEGIN = "<!-- BEGIN:GENERATED-COUNTS -->"
END = "<!-- END:GENERATED-COUNTS -->"
KBEGIN = "<!-- BEGIN:GENERATED-KEYHASHES -->"
KEND = "<!-- END:GENERATED-KEYHASHES -->"

#: key anti-tamper anchors rendered into the manifest (path, label, canonical_json?)
KEY_HASHES = [
    ("v02/configs/v02_frozen_v1.json", "**规范 JSON（协议指纹）**", True),
    ("v02/configs/v02_frozen_v1.json", "原始字节", False),
    ("configs/formal_v01.json", "原始字节（V01 冻结，**未执行**）", False),
    ("runs/episode_ledger.csv", "原始字节（V01 权威账本）", False),
    ("runs/episode_ledger.csv.buggy_pilot_run1", "原始字节（V01 作废首轮 pilot，历史留痕）", False),
    ("v02/runs/smoke/episode_ledger.csv", "原始字节", False),
    ("v02/runs/pilot/episode_ledger.csv", "原始字节", False),
    ("reports/v02/REPORT.zh-CN.md", "原始字节（中文结题报告）", False),
    ("reports/v02/PAPER_DRAFT_EN.md", "原始字节（英文论文初稿）", False),
    ("docs/FINAL_CLOSURE_DECISIONS.md", "原始字节", False),
    ("docs/LEDGER_RECONCILIATION_20261016.md", "原始字节（账本对账）", False),
    ("docs/FINAL_CLOSEOUT_20261016.md", "原始字节（**本结题报告**）", False),
    ("scripts/independent_verify_all.py", "原始字节（独立复算器）", False),
]

# (glob-pattern, category, description)
INCLUDE = [
    ("README.md", "root", "English README"),
    ("README.zh-CN.md", "root", "Chinese README"),
    ("LICENSE", "root", "licence"),
    ("CITATION.cff", "root", "citation metadata"),
    ("pyproject.toml", "root", "packaging"),
    ("requirements.txt", "root", "dependencies"),
    ("scripts/*.py", "script", "offline generators + independent verifiers (zero episodes)"),
    ("configs/*.json", "config", "V01 frozen/dev configs"),
    ("safefliplab/*.py", "source-v01", "V01 source"),
    ("tests/*.py", "test-v01", "V01 unit tests"),
    ("v02/configs/*.json", "config", "V02 configs"),
    ("v02/v02lab/*.py", "source-v02", "V02 source"),
    ("v02/tests/*.py", "test-v02", "V02 unit tests"),
    ("v02/README.md", "v02", "V02 README"),
    ("v02/runs/*/episode_ledger.csv", "ledger", "V02 phase ledgers (authoritative budget record)"),
    ("v02/runs/*/episode_ledger.schema.json", "ledger", "V02 ledger schema fingerprint (header SHA-256)"),
    ("v02/runs/manifest_*.json", "ledger", "V02 phase manifests"),
    ("v02/reports/*.csv", "report-v02", "V02 tabular results"),
    ("v02/reports/*.json", "report-v02", "V02 summaries"),
    ("v02/reports/*.md", "report-v02", "V02 phase reports"),
    ("v02/reports/*/*.png", "figure", "V02 figures"),
    ("runs/episode_ledger.csv", "ledger", "V01 authoritative ledger"),
    ("runs/episode_ledger.csv.buggy_pilot_run1", "ledger", "V01 voided first pilot (historical fact)"),
    ("runs/manifest_*.json", "ledger", "V01 manifests"),
    ("reports/*.csv", "report-v01", "V01 tabular results"),
    ("reports/*.json", "report-v01", "V01 summaries"),
    ("reports/*.md", "report-v01", "V01 phase reports"),
    ("reports/pilot/*.png", "figure", "V01 figures"),
    ("reports/smoke/*.png", "figure", "V01 figures"),
    ("reports/v02/*.md", "report-final", "FINAL Chinese report + English paper draft"),
    ("docs/*.md", "doc", "documentation"),
    ("docs/*.txt", "evidence", "archived evidence (tests / audit / recomputation)"),
    ("docs/*.csv", "evidence", "evidence tables"),
]

SKIP_PARTS = {".venv", "__pycache__", ".git", "backups", "tmp_audit"}
#: the manifest set must not hash itself (self-reference / chicken-and-egg)
SELF = {"docs/FINAL_ARTIFACT_HASHES.csv", "docs/FINAL_DELIVERY_MANIFEST.md",
        "docs/FINAL_ARTIFACT_COUNTS.md"}

CATEGORY_NOTE = {
    "root": "README（中/英）、LICENSE、CITATION.cff、pyproject.toml、requirements.txt",
    "script": "`scripts/`：清单生成器 + **独立复算器** + F-06 取证（均零 episode）",
    "config": "V01 冻结/开发配置 + V02 冻结配置与 schema",
    "source-v01": "`safefliplab/` 源码",
    "source-v02": "`v02/v02lab/` 源码",
    "test-v01": "`tests/`（V01 单元测试；**测试数见 `docs/V13_FINAL_V01_TESTS_20261016.txt`**）",
    "test-v02": "`v02/tests/`（V02 单元测试；**测试数见 `docs/V13_FINAL_V02_TESTS_20261016.txt`**）",
    "ledger": "V01/V02 账本（唯一预算权威）+ 阶段 manifest + V01 无效首轮备份",
    "report-v01": "V01 阶段报告 / CSV / JSON",
    "report-v02": "V02 阶段报告 / CSV / JSON",
    "figure": "V01 7 张 + V02 8 张真实数据图",
    "report-final": "**中文结题报告** + **英文论文初稿**",
    "doc": "协议、决策、审计、交接、指南",
    "evidence": "测试/审计/复算证据的归档文本",
    "v02": "V02 README",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[Path] = set()
    for pattern, category, desc in INCLUDE:
        for path in sorted(ROOT.glob(pattern)):
            if not path.is_file() or path in seen:
                continue
            if SKIP_PARTS & set(path.parts):
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel in SELF:
                continue
            rows.append({
                "path": rel,
                "category": category,
                "description": desc,
                "bytes": str(path.stat().st_size),
                "sha256": sha256(path),
            })
            seen.add(path)
    rows.sort(key=lambda r: (r["category"], r["path"]))
    return rows


def canonical_json_sha256(path: Path) -> str:
    import json as _json
    with open(path, encoding="utf-8") as fh:
        obj = _json.load(fh)
    return hashlib.sha256(
        _json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def render_keyhashes() -> str:
    """Render the anti-tamper anchor table from the files themselves."""
    lines = [KBEGIN]
    for rel, label, canonical in KEY_HASHES:
        path = ROOT / rel
        if not path.exists():
            lines.append(f"| `{rel}` | {label} | **缺失（MISSING）** |")
            continue
        digest = canonical_json_sha256(path) if canonical else sha256(path)
        lines.append(f"| `{rel}` | {label} | `{digest[:16]}` |")
    lines.append(KEND)
    return "\n".join(lines)


def render_counts(rows: list[dict[str, str]]) -> str:
    per: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        per.setdefault(r["category"], []).append(r)
    total = len(rows)
    total_bytes = sum(int(r["bytes"]) for r in rows)
    lines = [
        BEGIN,
        f"**合计 `{total}` 个文件 / `{total_bytes}` 字节**",
        "",
        "> 本区块由 `scripts/build_final_manifest.py` **生成**，**请勿手工修改**。",
        "> 权威文件集合与逐文件 SHA-256 见 `docs/FINAL_ARTIFACT_HASHES.csv`。",
        "> 生成器**不**把清单自身（本 MD / CSV / 本计数文件）计入，避免自引用。",
        "",
        "| 类别 | 文件数 | 说明 |",
        "|---|---:|---|",
    ]
    for cat in sorted(per):
        lines.append(f"| `{cat}` | {len(per[cat])} | {CATEGORY_NOTE.get(cat, '')} |")
    lines.append(f"| **合计** | **{total}** | 分类表算术合计须等于文件总数 |")
    lines.append("")
    lines.append(f"**分类表算术合计 = {total} = 文件总数 = CSV 行数 = {len(rows)}。**")
    lines.append(END)
    return "\n".join(lines)


def write_counts_md(block: str) -> None:
    body = (
        "# SafeFlipLab — 交付物计数（FINAL ARTIFACT COUNTS）\n\n"
        "> **本文件由 `scripts/build_final_manifest.py` 生成，请勿手工编辑。**\n"
        "> 每次文件集合变化后重新运行生成器即可同步。\n\n" + block + "\n"
    )
    COUNTS_PATH.write_text(body, encoding="utf-8")


def update_manifest_block(block: str, keyblock: str) -> None:
    text = MANIFEST.read_text(encoding="utf-8")
    for begin, end in ((BEGIN, END), (KBEGIN, KEND)):
        if begin not in text or end not in text:
            raise SystemExit(f"{MANIFEST} is missing the {begin} / {end} markers")
    text = _swap(text, BEGIN, END, block)
    text = _swap(text, KBEGIN, KEND, keyblock)
    MANIFEST.write_text(text, encoding="utf-8")


def _swap(text: str, begin: str, end: str, block: str) -> str:
    head, rest = text.split(begin, 1)
    _old, tail = rest.split(end, 1)
    return head + block + tail


def check() -> int:
    """Verify every `<n> 个文件` / `<n> 字节` claim in the manifest equals the CSV."""
    if not CSV_PATH.exists():
        print("FAIL: FINAL_ARTIFACT_HASHES.csv is missing")
        return 1
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    total = len(rows)
    total_bytes = sum(int(r["bytes"]) for r in rows)

    text = MANIFEST.read_text(encoding="utf-8")
    # strip inline-code backticks so "`188` 个文件" is matched like "188 个文件"
    plain = text.replace("`", "")
    failures: list[str] = []

    # every "<n> 个文件" occurrence must be the true total
    for m in re.finditer(r"(\d[\d,]*)\s*个文件", plain):
        got = int(m.group(1).replace(",", ""))
        if got != total:
            failures.append(f"manifest says {got} 个文件; CSV total is {total}")
    for m in re.finditer(r"(\d[\d,]*)\s*字节", plain):
        got = int(m.group(1).replace(",", ""))
        if got != total_bytes:
            failures.append(f"manifest says {got} 字节; CSV total is {total_bytes}")

    # the generated category table must sum to the total
    seen_cats: dict[str, int] = {}
    for m in re.finditer(r"\|\s*`([a-z0-9\-]+)`\s*\|\s*(\d+)\s*\|", text):
        seen_cats[m.group(1)] = int(m.group(2))
    if seen_cats:
        s = sum(seen_cats.values())
        if s != total:
            failures.append(f"category table sums to {s}; CSV total is {total}")

    # the generated key-hash table must agree with the files on disk
    by_path = {r["path"]: r["sha256"] for r in rows}
    n_hashrows = 0
    for m in re.finditer(r"^\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|\s*`([0-9a-f]{16})`\s*\|",
                         text, re.MULTILINE):
        path, label, short = m.group(1), m.group(2), m.group(3)
        n_hashrows += 1
        if "规范 JSON" in label:
            real = canonical_json_sha256(ROOT / path) if (ROOT / path).exists() else None
        else:
            real = by_path.get(path)
            if real is None and (ROOT / path).exists():
                real = sha256(ROOT / path)      # ledger/script files not in the CSV glob set
        if real is None:
            failures.append(f"key-hash table lists {path!r} which does not exist")
        elif not real.startswith(short):
            failures.append(f"key-hash table {path}: {short} but actual is {real[:16]}")

    if failures:
        print("MANIFEST COUNT CHECK: FAIL")
        for f in dict.fromkeys(failures):
            print("   * " + f)
        return 1
    print(f"MANIFEST COUNT CHECK: PASS  (files={total}, bytes={total_bytes}, "
          f"categories={len(seen_cats)}, key_hash_rows={n_hashrows})")
    return 0


def main() -> int:
    if "--check" in sys.argv:
        return check()
    rows = collect()
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["path", "category", "description", "bytes", "sha256"])
        w.writeheader()
        w.writerows(rows)
    block = render_counts(rows)
    keyblock = render_keyhashes()
    write_counts_md(block)
    update_manifest_block(block, keyblock)
    print(f"hashed {len(rows)} files -> {CSV_PATH}")
    print(f"counts block      -> {COUNTS_PATH} and {MANIFEST.name}")
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
