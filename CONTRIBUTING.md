# Contributing

Thanks for considering a contribution. This repository is the **engineering
wrapper** around a frozen exploratory study; the rules below exist to keep the
research record intact.

## Ground rules (non-negotiable)

1. **No real simulation episodes without explicit authorisation.** `smoke` /
   `pilot` consume billed episodes; `formal` is NO-GO. Do not run them, and do
   not add code/tests that launch them.
2. **Do not modify frozen research data**: `reports/`, `docs/` (existing
   files), `configs/`, `v02/v02lab/`, `v02/tests/`, and
   `PUBLICATION_MANIFEST.csv` are v1.0 evidence. Hash mismatches are caught by
   `scripts/verify_publication.py`.
3. **Do not rewrite conclusions.** The study is `INCONCLUSIVE`; M1/M2 disagree
   in direction on `Δgap`. A PR that "fixes" this by changing endpoints,
   thresholds or wording will be rejected.
4. **No over-claiming**: no "significant", "proven", "first", "safer" (see
   `docs/CLAIMS_REGISTER.zh-CN.md` X1–X17).

## Development setup

```bash
python -m venv .venv
./.venv/bin/pip install -e ".[test]"     # Windows: .\.venv\Scripts\python.exe ...
python -m unittest discover -s tests -q   # expected: Ran 234, OK (skipped=1)
cd v02 && python -m unittest discover -s tests -q   # expected: Ran 143, OK
```

## Code style

- Python 3.11+; standard library first; no new runtime dependency without
  discussion (the `sim`/`test` extras are pinned on purpose).
- Keep modules small and explicit; prefer dataclasses and plain functions.
- No absolute paths in code; resolve from `Path(__file__)` or an environment
  variable (`SAFEFLIPLAB_ROOT` for the audit scripts).
- UTF-8 + LF for all text files (`.gitattributes` enforces byte-exact
  checkouts).
- Tests are `unittest`-style (pytest can run them, but must not be required).
  Every bug fix should come with a regression test that fails before the fix.

## Pull requests

- One logical change per PR; describe **why**, list the commands you ran, and
  paste the test summary (counts + exit codes).
- Run `python scripts/verify_publication.py` before submitting: it must PASS
  (v1.0 rows byte-exact except the explicit `V11_UPDATED` whitelist; new files
  only within `POST_V1_PATTERNS`).
- If you add an engineering file, add its path to `POST_V1_PATTERNS` in
  `scripts/verify_publication.py` (smallest possible pattern; no `*` catch-alls).
- Do not include generated artefacts (`runs/`, caches, `*.egg-info`).

## Commit messages

Short imperative subject, then a short body:

```text
Fix formal refusal to run before filesystem side effects

- validate flags and raise before PhaseDriver construction
- add zero-side-effect regression tests
- keep the refusal message and EXIT=2 semantics unchanged
```

## Reporting problems

Use the private repository's issues (or a private security advisory for
vulnerabilities — see `SECURITY.md`). Include: command, expected vs actual,
Python version, and the output of `python -m safefliplab doctor`.
