# Changelog

All notable engineering changes. The **research record is frozen**: scientific
data, results and conclusions do not change between these entries (see
`PUBLICATION_SCOPE.md`).

## v1.1 — engineering update (2026-10-18, branch `engineering/open-source-readiness`)

**Research data and conclusions: unchanged.** No episodes were launched; no
ledger, result or `docs/` file was modified.

### Fixed

- **Formal refusal had filesystem side effects (P1-01).** `run_formal_phase`
  constructed a `PhaseDriver` (creating `runs/` and an empty ledger) before
  raising the refusal. The refusal now happens first: flags are validated and
  the standard `RuntimeError` is raised **before** any file is created;
  `EXIT=2` and the message are unchanged. The CLI guard test now mocks the
  scheduler, and `tests/test_formal_no_side_effects.py` pins the behaviour.
- **`doctor` created a ledger (DOCTOR-01).** The read-only budget check
  constructed `EpisodeLedger` on a missing path. It now checks for the file
  first and reports `no ledger in this checkout (0/<cap>)` without touching the
  disk. Pinned by `tests/test_doctor_readonly.py`.
- **`test` extra missed `cornercaselab` (GH2-B-01).** A fresh
  `pip install -e ".[test]"` could not run 14 tests that import
  `cornercaselab`. The extra now includes the pinned git dependency, and
  `requirements.txt` states that tests need those types but launch no
  episodes.

### Changed

- `CITATION.cff`: `repository-code` now points at
  `https://github.com/lin-lab666/SafeFlipLab`.
- `pyproject.toml`: `setuptools>=77` (PEP 639 `license = "Apache-2.0"`),
  `[project.urls]`, `classifiers`, `keywords`, and a `test` extra.
  The `License :: OSI Approved` classifier was removed because PEP 639
  forbids combining it with a license expression (found by an actual install).
- `requirements.txt`: clarifies parity with the `sim` extra and the test
  suite's needs.
- `.gitignore`: adds `.coverage`, `htmlcov/`, `build/`, `dist/`.
- `README.md` / `README.zh-CN.md`: executable V02 test command, expected counts
  (234 / 143), the designed skip, and the no-residue test policy.
- `scripts/verify_publication.py`: two-scope verification
  (`V11_UPDATED` whitelist + `POST_V1_PATTERNS` additions).
- `scripts/build_final_manifest.py`, `scripts/independent_verify_all.py`:
  `ROOT` defaults to the repository root, overridable via
  `SAFEFLIPLAB_ROOT`.

### Added

- `INSTALLATION.md`, `QUICKSTART.md`, `ARCHITECTURE.md`, `EXAMPLES.md`,
  `CONTRIBUTING.md`, `SECURITY.md`, `TESTING.md`, `DATA_AVAILABILITY.md`,
  `CHANGELOG.md` (this file), `PUBLICATION_SCOPE.md`.
- `examples/offline_demo.py` — synthetic, offline demo (FakeAdapter semantics,
  zero episodes, zero files).
- `.github/workflows/ci.yml` — manual-only CI (Python 3.11/3.12/3.13 matrix,
  read-only token, no secrets, offline guard).
- `tests/test_formal_no_side_effects.py`, `tests/test_doctor_readonly.py` —
  7 new regression tests (V01 total: 227 → 234).
- **Public-readiness presentation (OS-3)**: README status block (tests, closeout,
  scientific status, visibility neutral), a "what you can do" summary, a CLI
  table, `docs/assets/architecture.svg` (text-only pipeline diagram) and
  `docs/assets/offline-demo-output.txt` (real demo output, marked SYNTHETIC).
  The V02 binary-endpoint disclosure was added to the README (2 collision
  events across 54 quartets). No promotional claims were added.

### Verification

```text
V01: Ran 234 tests, OK (skipped=1)      EXIT 0   (twice in a row, no runs/)
V02: Ran 143 tests, OK                  EXIT 0
python scripts/verify_publication.py    PASS, EXIT 0
```

## v1.0 — research package (2026-10-17, commit `baee8becb796b0fe4f067a0c4cb5fbac237c58b9`)

- Initial public snapshot of the SafeFlipLab exploratory closeout.
- 202 files on disk; `PUBLICATION_MANIFEST.csv` registers 200 files /
  3,111,181 bytes (byte-level SHA-256).
- Engineering closeout PASS; scientific claim **INCONCLUSIVE**.
- `.gitattributes` (`* -text`) pins byte-exact checkouts on every platform.
- The prior commit `0f63b73` was the initial release; `baee8be` added the
  `.gitattributes` fix and the regenerated manifest / release notes.

### Research status at v1.0 (unchanged since)

- V01: binary collision endpoint had zero variance (264/264 zero collisions) —
  formal permanently NO-GO.
- V02: continuous min-TTC endpoint; all four primary 95% intervals cross zero;
  M1 and M2 disagree in direction on `Δgap`; endpoint resolution and effect size
  are the same order (`0.003–0.033 s` vs `~0.2 s` known bias).
- No p-values, no significance claims; hypotheses INCONCLUSIVE or
  NOT ESTABLISHED.
