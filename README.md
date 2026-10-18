# SafeFlipLab

**Budgeted Counterfactual Safety-Reversal Testing for Simplified Autonomous Driving Simulations.**

SafeFlipLab asks two questions inside one simplified highway-merge simulation
(HighwayEnv merge scenario, driven through the public `cornercaselab==0.3.0`
interface, Apache-2.0):

1. **Reversal question.** For a rule-based controller, can *increasing* the
   initial front gap (`front_gap += 2.0 m`) or *decreasing* the ego initial
   speed (`ego_speed -= 1.0 m/s`) ever *increase* simulated collision risk?
   And do the two interventions interact non-additively?
2. **Budget question.** Under an identical episode budget, does broad
   exploration (`WideExplore`) or repeat-first verification (`VerifyFirst`)
   nominate counter-intuitive candidates that hold up under an *independent*
   held-out audit?

All results are properties of a simplified simulator and one frozen
observation-only controller. **Nothing here is a real-road safety claim.**

## Closeout status (2026-10-17)

- **Engineering closeout: PASS.** Independent recomputation of 141 assertions,
  manifest gate PASS, doctor V01 17/17 + V02 7/7 GO, tests V01 **227** +
  V02 **143** all OK, 58/58 report artefacts byte-idempotent, full ledger
  reconciliation.
- **Scientific claim: INCONCLUSIVE** (a legitimate closeout outcome). V02
  closed as an exploratory/descriptive study; the two endpoints disagree in
  sign (M1 minimal forward TTC and M2 low-TTC step share move in opposite
  directions on Δgap, both in the "safer" direction descriptively); this is
  kept and disclosed, and cross-endpoint sign comparison is forbidden. No
  p-values, no significance claims; MDE=0.10 s is a sample-size planning
  example only.
- V01 formal (12,800 episodes): **permanent NO-GO** — implemented, never
  authorised, never run.
- Ledger figures (private project data, see below): **528** valid launches
  (V01 264 = smoke 24 + pilot 240; V02 264 = smoke 24 + pilot 240, including
  one V02 smoke error = D37); **748** total historical launches (= 528 valid
  + 220 voided first pilot). Audit/method comparisons on historical data are
  not independent (D42/D44): fixed code does not make historical data an
  independent comparison.

## Data availability (important)

This repository (PRIVATE snapshot) **includes** all source code, tests,
frozen/dev configs, phase result summaries (`reports/`, `v02/reports/`
reports/figures/CSV/JSON) and closeout documentation.

This repository **excludes** raw episode-level data and ledgers — `runs/` and
`v02/runs/` (raw per-episode JSON, `episode_ledger.csv*`, manifests, and the
voided first pilot `_buggy_pilot_run1/` backups). Those raw data are kept by
the project owner; reasonable requests can be made to the owner.

Consequently:

- `scripts/independent_verify_all.py` needs the **private raw data** for a
  full rerun (it reads only the ledgers and archived raw episode JSON);
  within this public package, reproducibility rests on the **test suites**
  (V01 227 + V02 143, synthetic/mock, no real episodes) and the **result
  summaries** (`reports/`).
- The original project's 201-file closeout manifest
  (`docs/FINAL_ARTIFACT_HASHES.csv` etc.) records the full set including
  `runs/`; this release's own scope is documented in `RELEASE_NOTES.md`
  §2.3. The two scopes are recorded independently. The original
  `scripts/build_final_manifest.py --check` targets the full scope (with
  `runs/`) and **does not apply inside this release** (it fails without
  `runs/`); integrity of this package is verified via
  `PUBLICATION_MANIFEST.csv` + `scripts/verify_publication.py`.

## Layout

```
safefliplab/     python package (adapter, generator, runner, ledger, methods, stats, report, cli)
v02/v02lab/      V02 package (anchors, conditions, TTC state, quartet, stats, report, cli)
configs/         dev_v01.json (smoke/pilot) and formal_v01.json (frozen formal plan)
v02/configs/     v02_frozen_v1.json (frozen V02 protocol) etc.
scripts/         helper scripts (manifest builder, independent verifier, release verifier)
tests/           V01 unit tests (no real episodes; mocks only inside tests)
v02/tests/       V02 unit tests
reports/         V01 phase reports and figures (real data only) + closeout report / paper draft (reports/v02/)
v02/reports/     V02 phase reports and figures
docs/            protocol, decision log, progress, handoff, owner guide, acceptance evidence
PUBLICATION_MANIFEST.csv   release integrity manifest (relpath/bytes/SHA-256)
RELEASE_NOTES.md           release notes (incl. data availability and absolute-path disclosure)
LICENSE / CITATION.cff / pyproject.toml / requirements.txt
```

`report --phase <phase>` outputs (V01):

```
<phase>_report.md          Chinese phase report (with budget-ledger appendix)
<phase>_episodes.csv|jsonl one row per billed episode
<phase>_anchors.csv        per-anchor four-condition counts/denominators/ratios/paired deltas
<phase>_budget_summary.csv budget cap/launched/unused (failures/unknowns are billed too)
<phase>_comparisons.csv    per-master-seed method comparison (blank when not computable)
<phase>_quartets.csv       full main quartet details
<phase>_margins.csv        exploratory continuous margins (non-protocol)
<phase>/figure_*.png       figures (only with real data)
```

## Quick start (Windows, Python 3.13)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[sim]"
.\.venv\Scripts\python.exe -m safefliplab doctor
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected output: `Ran 234 tests, OK (skipped=1)` (227 original tests + 7
side-effect regression tests added in v1.1). The single skip needs the
project-internal legacy ledger (`runs/episode_ledger.csv`), which the published
snapshot does not contain — it is a **designed skip**. The tests launch **no
real episodes** and **do not write `runs/` into the repository root** (since
GH-2, the `formal` refusal path returns before any filesystem side effect). If
your checkout still has a `runs/` residue from an earlier version (a gitignored
test artefact), delete it before re-running.

V02 tests (switch into `v02/` first; the interpreter stays at the parent level):

```powershell
cd v02
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected output: `Ran 143 tests, OK`.

**CLI safety notice**: `smoke`/`pilot` launch **real billed episodes** (every
launched episode, including failed/interrupted ones, is billed before it
starts; there are no free retries). This snapshot contains no ledger; read
`docs/OWNER_GUIDE.zh-CN.md` and `docs/REPRODUCTION_MANUAL.zh-CN.md` before
running any simulation. `formal` is prepared only, requires an explicit human
GO, and is NO-GO in this closeout state.

## Offline demo (no simulation)

```bash
python examples/offline_demo.py
```

A synthetic walkthrough of the four-condition design (FakeAdapter semantics,
zero episodes, zero files). It prints `SYNTHETIC OUTPUT - NOT EXPERIMENTAL
RESULTS` and must not be quoted as a result. See `EXAMPLES.md` and
`QUICKSTART.md`.

## Documentation

| Document | Purpose |
|---|---|
| `INSTALLATION.md` | extras (`test` / `sim`), platform notes, offline installs |
| `QUICKSTART.md` | 5-minute offline path |
| `ARCHITECTURE.md` | module map, ledger/billing gate, adapters, report pipeline, safety gates |
| `EXAMPLES.md` | synthetic demo + how to read the frozen results |
| `TESTING.md` | commands, expected counts (234 / 143), repeat-run policy, CI |
| `DATA_AVAILABILITY.md` | included/excluded data, 528 vs 748 episodes, request process |
| `CONTRIBUTING.md` | ground rules, style, PR checklist |
| `SECURITY.md` | reporting channel, secrets policy, gates |
| `CHANGELOG.md` | v1.0 and v1.1 engineering history |
| `PUBLICATION_SCOPE.md` | v1.0 frozen research package vs v1.1 engineering scope |
| `docs/` (frozen) | closeout evidence: claims register, research audit, ledger reconciliation |

## Data integrity and independent recomputation

- Every file's relpath/bytes/SHA-256 is listed in `PUBLICATION_MANIFEST.csv`;
  verify (tampering with any row, adding or deleting files exits non-zero):

  ```powershell
  .\.venv\Scripts\python.exe scripts\verify_publication.py
  ```

- `scripts/independent_verify_all.py` reads only the ledgers and archived raw
  episode JSON, imports neither project report nor stats module, and recomputes
  every published statistic from scratch (141 assertions passed at closeout).
  Its `ROOT` constant points at the original project path
  (`D:\SafeFlipLab`) and **requires the private raw data** to run fully;
  change it to the local checkout path when running elsewhere.

## Reproducibility

* All seeds are SHA-256 derived (`safefliplab/seeds.py`); Python `hash()` is
  never used.
* `dev_seed = 20261011` for smoke/pilot only; the 8 formal master seeds are
  frozen in `configs/formal_v01.json` (formal NO-GO, never run).
* Every launched episode - including failed and interrupted ones - is billed
  before it starts; there are no free retries (the ledger is private data and
  is not part of this package).
* Dependency pins: `requirements.txt` (cornercaselab 0.3.0 from the pinned
  GitHub tag, HighwayEnv 1.10.2, Gymnasium 1.2.2).

## Licence and attribution

SafeFlipLab's own code is Apache-2.0 (see `LICENSE`). The simulation
interface is reused from CornerCaseLab v0.3.0 (Apache-2.0, (c) 吴昊霖 /
lin-lab666) as an installed dependency; HighwayEnv/Gymnasium and their
upstreams retain their own licences. See `docs/PROVENANCE.md` and
`docs/ATTRIBUTION.md`. Citation metadata: `CITATION.cff`.

## Getting help and contributing

- Bugs / questions: open an issue in this private repository (collaborators
  only). Include the command, expected vs actual, Python version, and the
  output of `python -m safefliplab doctor`.
- Security: report privately via a GitHub **security advisory** — see
  `SECURITY.md`. Do not open a public issue.
- Contributions: read `CONTRIBUTING.md` first. Real simulation episodes need
  explicit authorisation; frozen data and conclusions must not be rewritten.
