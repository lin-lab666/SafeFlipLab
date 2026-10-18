# Data availability

## What this repository contains

- Full source code: `safefliplab/` (V01, 16 modules) and `v02/v02lab/`
  (V02, 18 modules).
- Unit tests: `tests/` (22 files) and `v02/tests/` (10 files) — synthetic
  data / `FakeAdapter` only; no real episodes.
- Frozen and development configurations: `configs/`, `v02/configs/`.
- Aggregate results: `reports/` and `v02/reports/` (reports, figures, CSVs,
  JSON summaries), frozen at v1.0.
- Closeout documentation: `docs/` (64 files), including the claims register,
  the research audit, the ledger reconciliation and the decision log.

## What this repository does NOT contain

- Raw per-episode JSON and the ledgers under `runs/` and `v02/runs/`
  (762 files in the original project: 490 + 272).
- The first, voided pilot round's backups (`runs/_buggy_pilot_run1/` and its
  ledger) — they exist in the project owner's archive, not here.

The published snapshot therefore cannot re-run
`scripts/independent_verify_all.py` end-to-end: the recomputation needs the
private ledgers and episode JSON. Reproducibility inside this repository is
anchored on the unit test suites (V01 + V02, zero real episodes) and the
aggregate reports under `reports/`.

## The accounting numbers (for orientation)

| Quantity | Value | Meaning |
|---|---:|---|
| Valid episodes | **528** | V01 264 (smoke 24 + pilot 240) + V02 264 (smoke 24 + pilot 240) |
| Historical launches | **748** | 528 valid + 220 voided first-round pilot |
| Voided pilot | **220** | first-round pilot, phase-isolation defect; archived, never mixed into statistics |
| Known error | **1** | V02 smoke episode 0 (`D37`): billed, archived as error, not re-run |

Ledger detail (valid activity ledger): 528 semantic rows for 264 episodes
(launch + outcome per episode). The frozen backup ledger holds 488 semantic
rows = 244 episodes (24 smoke overlapping the activity ledger + 220 voided
pilot). See `docs/LEDGER_RECONCILIATION_20261016.md` for the full audit,
including the "row vs episode" distinction.

## How to request the raw data

The project owner keeps the raw data. Reasonable requests can be made by
opening an issue in this repository (it is private, so only collaborators can
see it) or by contacting the maintainer through the repository's own contact
channel. Requests should state the intended use and whether results will be
published; the owner decides case by case. No email address is published here
on purpose.

## Licence boundary

- **Code and documentation in this repository**: Apache License 2.0 (see
  `LICENSE`).
- **Raw episode data / ledgers (not included)**: not covered by the repository
  licence; their use requires the owner's permission.
- **CornerCaseLab v0.3.0** (external dependency, Apache-2.0): the simulation
  interface (scenario schema, HighwayEnv adapter, pilot controllers) is reused
  as an installed dependency, with attribution in `docs/ATTRIBUTION.md` and
  `CITATION.cff`.

## What the data can and cannot support

All statistical statements in this repository are **descriptive and
exploratory**. The four bootstrap intervals for the primary endpoint all cross
zero; M1 and M2 disagree in direction on `Δgap`; endpoint resolution
(0.003–0.033 s observed vs ~0.2 s known systematic bias) is the same order as
the effects. "Not detected" must not be read as "no effect", and nothing here
supports real-road safety claims. See `docs/CLAIMS_REGISTER.zh-CN.md` (C1–C18,
X1–X17) and `PUBLICATION_SCOPE.md`.
