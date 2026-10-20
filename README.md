# SafeFlipLab

**Budgeted Counterfactual Safety-Reversal Testing for Simplified Autonomous Driving Simulations.**

SafeFlipLab is a **budgeted counterfactual safety-evaluation toolkit** (a
research instrument for intervention/reversal questions under a fixed episode
budget) **and** a **reproducible research-engineering artifact** (ledger-first
billing, byte-level publication manifest, zero-episode test suites). It is not
a safety-certification tool.

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

## What you can do with it

- **Ask a counterfactual reversal question** on a frozen simulator + frozen
  rule controller, using a four-condition paired design (00 / 10 / 01 / 11)
  and anchor-level bootstrap intervals.
- **Account for every episode**: launch-before-run billing, per-scope budget
  caps, no free retries; failed attempts are still billed and disclosed
  (D37 is a real example).
- **Audit nominations independently**: a held-out audit stream with
  method-dependent seeds. The historical D42/D44 non-independence is disclosed,
  not hidden.
- **Reproduce the engineering claims offline**: 242 V01 + 143 V02 unit tests
  and a byte-level publication-manifest check, with **zero** simulator
  episodes and **zero** files written to `runs/`.
- **Read the negative result honestly**: all four primary intervals cross
  zero, M1/M2 disagree on `Δgap`, and the endpoint resolution is the same
  order as the observed effect.

## How the four-condition design works

The reversal question uses a 2×2 counterfactual design. A **quartet** is four
episodes that share one perturbation draw and vary two frozen intervention
factors:

| Factor | 0 (off) | 1 (on) |
|---|---|---|
| `front_gap` | baseline | `+2.0 m` |
| `ego_speed` | baseline | `−1.0 m/s` |

```
2×2 counterfactual matrix (one quartet = four shared-draw runs)

                    front_gap
              off              +2.0 m
        ┌────────────────┬────────────────┐
        │       00       │       10       │   ego_speed off
        │    baseline    │    gap only    │
        ├────────────────┼────────────────┤
        │       01       │       11       │   ego_speed −1.0 m/s
        │   speed only   │   gap+speed    │
        └────────────────┴────────────────┘
```

Because all four cells of a quartet share the same perturbation draw, the
paired differences (`10−00`, `01−00`, `11−00`, and their interaction) cancel
shared noise at the anchor level. The **anchor** (a frozen scenario/controller
pair) is the independent unit; 95% intervals come from an anchor-level cluster
bootstrap over 18 anchors.

## Project status

| Item | Status |
|---|---|
| Engineering closeout | **PASS** — independent recomputation of 141 assertions, manifest gate PASS, doctor V01 17/17 + V02 7/7 GO, 58/58 report artefacts byte-idempotent, full ledger reconciliation |
| Scientific claim | **INCONCLUSIVE** (a legitimate closeout outcome; exploratory/descriptive) |
| Tests (offline, zero episodes) | **V01 242 OK (skipped=1)** / **V02 143 OK** |
| V01 formal (12,800 episodes) | **permanent NO-GO** — implemented, never authorised, never run |
| Repository visibility | as configured in the repository settings |

## Scientific status and limits

- V02 closed as an exploratory/descriptive study; the two endpoints disagree in
  sign (M1 minimal forward TTC and M2 low-TTC step share move in opposite
  directions on Δgap, both in the "safer" direction descriptively); this is
  kept and disclosed, and cross-endpoint sign comparison is forbidden. No
  p-values, no significance claims; MDE=0.10 s is a sample-size planning
  example only.
- The V02 binary collision endpoint is nearly information-free in this design:
  **2 collision events across 54 quartets** (conditions `00` and `10` one each);
  condition `11` never collided (`reverse=0`, `rescue=1` — a single event).
  This is why V02 uses a continuous endpoint.
- Ledger figures (private project data, see below): **528** valid launches
  (V01 264 = smoke 24 + pilot 240; V02 264 = smoke 24 + pilot 240, including
  one V02 smoke error = D37); **748** total historical launches (= 528 valid
  + 220 voided first pilot). Audit/method comparisons on historical data are
  not independent (D42/D44): fixed code does not make historical data an
  independent comparison.

## Real results summary (V02 pilot, real data)

Source: `v02/reports/pilot_report.md` — a real HighwayEnv run (240 billed
episodes, 54 usable quartets, 18 anchors). Descriptive only; the confirmatory
sampling assumptions did not hold, so **no p-value is reported**.

**M1 — per-episode minimal forward TTC (seconds).** Negative Δ = the
intervention reduced the safety margin (reversal direction).

| Contrast | Meaning | Point estimate (s) | 95% anchor-level cluster-bootstrap interval | Anchors |
|---|---|---|---:|---:|
| delta_gap | 10−00 (gap) | +0.0127 | [−0.0525, +0.0769] | 18 |
| delta_speed | 01−00 (speed) | +0.0327 | [−0.0589, +0.1243] | 18 |
| delta_both | 11−00 (both) | +0.0030 | [−0.0436, +0.0526] | 18 |
| i_lin | interaction | −0.0424 | [−0.1465, +0.0613] | 18 |

**M2 — share of steps with forward TTC below the low-TTC threshold** (smaller
is safer, the *opposite* sign convention from M1, D43). Condition means:
`00` = 0.0234, `10` = 0.0252, `01` = 0.0127, `11` = 0.0172.

**C13 — binary collision endpoint**: 2 collisions across 54 quartets
(`00` = 1, `10` = 1, `01` = 0, `11` = 0); `11` never collided
(`reverse` = 0, `rescue` = 1).

All four M1 intervals **cross zero**: the observed effect size is the same
order as the endpoint resolution, so the data **cannot support a
safety-reversal conclusion**. M1 and M2 disagree in sign on `Δgap`, which is
disclosed rather than resolved.

## Key figures

**Architecture** — text-only pipeline diagram (V01/V02 + safety gates):

![SafeFlipLab pipeline architecture (V01/V02 + safety gates)](docs/assets/architecture.svg)

**Real V02 pilot results** — real HighwayEnv data, from `v02/reports/pilot/`:

![Figure 1 — per-condition TTC across the four conditions](v02/reports/pilot/figure_1_condition_ttc.png)

*Figure 1 — per-condition TTC (real pilot data).*

![Figure 2 — anchor-level contrast forest](v02/reports/pilot/figure_2_anchor_contrast_forest.png)

*Figure 2 — anchor-level contrast forest (real pilot data).*

![Figure 4 — per-anchor delta, both interventions](v02/reports/pilot/figure_4_per_anchor_delta_both.png)

*Figure 4 — per-anchor delta for the `both` intervention (real pilot data).*

**Result summary** — M1 forest (anchor-level point estimates + 95% bootstrap
intervals) and per-anchor `delta_gap` scatter, generated read-only from the
published summaries by `examples/read_real_results.py`:

![Result summary — M1 forest and per-anchor delta_gap (real pilot data)](docs/assets/result_summary.png)

*Result summary — all four M1 intervals cross zero (grey), consistent with the
INCONCLUSIVE closeout. See `examples/read_real_results.py`.*

## CLI at a glance

| Command | What it does | Side effects |
|---|---|---|
| `python -m safefliplab doctor` | read-only environment/interface check (17 checks) | **none** (never creates a ledger) |
| `python -m safefliplab smoke --max-episodes 24` | at most 24 **real billed** episodes | writes `runs/`; needs owner authorisation |
| `python -m safefliplab pilot --max-episodes 240` | at most 240 **real billed** episodes | writes `runs/`; needs owner authorisation |
| `python -m safefliplab report --phase pilot` | rebuild report artefacts from the ledger | writes `reports/` |
| `python -m safefliplab formal --confirm --max-episodes 12800` | prepared only | **refuses** (EXIT 2) before any file is created |
| `cd v02 && python -m v02lab doctor` | V02 read-only checks | none |
| `python scripts/verify_publication.py` | two-scope manifest check | none |

## Data availability (important)

This repository snapshot **includes** all source code, tests,
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
  (V01 242 + V02 143, synthetic/mock, no real episodes) and the **result
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

Expected output: `Ran 242 tests, OK (skipped=1)` (227 original tests + 7
side-effect regression tests added in v1.1 + 8 CI-offline-guard tests added in
v1.2.0). The single skip needs the
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
| `docs/assets/architecture.svg` | text-only pipeline diagram (V01/V02 + gates) |
| `EXAMPLES.md` | synthetic demo + how to read the frozen results |
| `TESTING.md` | commands, expected counts (242 / 143), repeat-run policy, CI |
| `DATA_AVAILABILITY.md` | included/excluded data, 528 vs 748 episodes, request process |
| `CONTRIBUTING.md` | ground rules, style, PR checklist |
| `SECURITY.md` | reporting channel, secrets policy, gates |
| `CHANGELOG.md` | v1.0, v1.1 and v1.2.0 engineering history |
| `PUBLICATION_SCOPE.md` | v1.0 frozen research package vs v1.1/v1.2 engineering scope |
| `RELEASE_NOTES.md` | v1.0 release notes: data availability, absolute-path disclosure, scope (§2.3) |
| `RELEASE_NOTES_v1.2.0.md` | v1.2.0 (pending) release notes |
| `scripts/ci_offline_guard.py` | executable offline guard (blocks real-simulator launch patterns) |
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
upstreams retain their own licences (HighwayEnv MIT, Gymnasium MIT, NumPy
BSD-3-Clause, Pillow HPND, matplotlib license, pygame LGPL). See
`docs/PROVENANCE.md` and `docs/ATTRIBUTION.md`. Citation metadata:
`CITATION.cff`.

## Getting help and contributing

- Bugs / questions: open an issue in this repository. Include the command,
  expected vs actual, Python version, and the output of
  `python -m safefliplab doctor`.
- Security: report privately via a GitHub **security advisory** — see
  `SECURITY.md`. Do not open a public issue.
- Contributions: read `CONTRIBUTING.md` first. Real simulation episodes need
  explicit authorisation; frozen data and conclusions must not be rewritten.
