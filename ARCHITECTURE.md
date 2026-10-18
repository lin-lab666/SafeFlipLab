# Architecture

## Two versions, deliberately isolated

```
V01  (safefliplab/)                V02  (v02/v02lab/)
  binary collision endpoint          continuous min-forward-TTC endpoint
  WideExplore vs VerifyFirst         four-condition paired quartets
  smoke=24 / pilot=240 episodes      smoke=24 / pilot=240 episodes
  -> zero-variance endpoint          -> explorative/descriptive study
```

V02 exists because V01 found a **structural** zero-variance endpoint: with the
frozen `boundary` controller and a lead vehicle in free flow, all 264 real
episodes had `ego_collision = 0`, so the collision endpoint could not compare
methods. V02 replaces it with a continuous proxy (min forward TTC) and adds
in-anchor perturbations. The two versions are analysed separately and must
never be pooled (claims register X5).

## V01 module map (text)

```
CLI (cli.py)
 ├─ doctor  -> doctor.py            (read-only environment checks; no episodes)
 ├─ smoke   -> experiments.run_smoke_phase   (cap 24)
 ├─ pilot   -> experiments.run_pilot_phase   (cap 240)
 ├─ formal  -> experiments.run_formal_phase  (refuses before any side effect)
 └─ report  -> report.write_report

experiments.PhaseDriver
 ├─ seeds.py          deterministic seeds / run ids
 ├─ generator.py      anchors from the frozen config
 ├─ domain.py         quadruple conditions (00/10/01/11) and bounds
 ├─ adapter.py        ScenarioAdapter (real)  |  tests/fakes.FakeAdapter
 ├─ runner.py         SimulatorRunner: launch -> run -> outcome
 ├─ ledger.py         EpisodeLedger: atomic reserve, billing, budget scopes, lock
 ├─ methods.py        WideExplore / VerifyFirst nomination logic
 ├─ stats.py          anchor-level paired statistics (cluster bootstrap)
 ├─ margins.py        exploratory continuous margins (non-protocol)
 └─ report.py         markdown/CSV/JSON outputs under reports/
```

## V02 module map (text)

```
v02/v02lab/cli.py
 ├─ doctor  -> phase/budget checks (read-only)
 ├─ smoke / pilot -> phases.run_smoke / run_pilot   (caps 24 / 240)
 └─ report  -> report.write_v02_report

v02/v02lab/phases.py
 ├─ anchors.py        deterministic anchor stream (18 anchors)
 ├─ conditions.py     the four intervention conditions + shared perturbation
 ├─ quartet.py        quartet completeness / PAIR_MISSING
 ├─ schema.py         frozen v02 protocol schema
 ├─ adapter_real.py   RealAdapterV02 (HighwayEnv via cornercaselab)
 ├─ fake_adapter.py   FakeAdapterV02 (tests/demo only)
 ├─ runner.py         launch -> step -> trace -> outcome
 ├─ ledger21.py       21-column ledger (raw_path is the source of truth)
 ├─ methods.py        shared / WideExplore / VerifyFirst nomination
 ├─ stats_anchor.py   anchor-level estimation + descriptive bootstrap
 ├─ power.py          sample-size planning grid (planning only)
 ├─ reporting.py      tables/figures
 └─ report.py         report assembler
```

## Ledger and billing gate

- `EpisodeLedger` is the **single source of truth**. Each episode writes a
  `launch` row **before** the simulator runs and an `outcome` row after; a
  failure still writes an outcome (`error`) and is billed. There are no free
  retries.
- Budget scopes: smoke/pilot share a phase cap; formal uses a tighter
  `formal|method|seed` scope so the 8 seeds × 2 methods cannot collide on the
  phase cap.
- A sidecar `.lock` serialises cross-process access (Windows sharing-violation
  fix, D48).
- Reading rules: derived products must read episodes via the ledger's
  `raw_path` column, never by filename globbing (D43 was exactly that bug).

## Adapters

| Layer | Real | Test / demo |
|---|---|---|
| V01 | `safefliplab/adapter.py::ScenarioAdapter` | `tests/fakes.py::FakeAdapter` |
| V02 | `v02/v02lab/adapter_real.py::RealAdapterV02` | `v02/v02lab/fake_adapter.py::FakeAdapterV02` |

The test suites and `examples/offline_demo.py` use only the fake adapters:
they produce deterministic synthetic trajectories and launch **no** simulator
episodes.

## Report pipeline

`report.write_report(root, phase)` reads the ledger + raw episodes and writes
`reports/<phase>_report.md`, `<phase>_summary.json`, `<phase>_quartets.csv`,
`<phase>_margins.csv` and figures. Re-running at the same location is
byte-idempotent (58/58 artefacts in the closeout audit). V02 has the same
shape under `v02/reports/`.

## Package integrity

- `PUBLICATION_MANIFEST.csv` freezes the **v1.0 research package** (200 rows,
  byte-level SHA-256), including `docs/` and `reports/`.
- `scripts/verify_publication.py` verifies two scopes: v1.0 rows byte-exact
  (minus an explicit `V11_UPDATED` whitelist) and v1.1 additions limited to
  `POST_V1_PATTERNS`. `PUBLICATION_SCOPE.md` explains the split.
- `scripts/build_final_manifest.py` and `scripts/independent_verify_all.py` are
  internal audit tools; they default to the repository root and can be pointed
  elsewhere with `SAFEFLIPLAB_ROOT`. They need the private raw data.

## Safety gates

| Gate | Where | Behaviour |
|---|---|---|
| formal double flag | `cli.cmd_formal` | needs **both** `--confirm` and `--max-episodes 12800`; otherwise EXIT 2 |
| formal refusal (zero side effects) | `experiments._formal_refusal_plan` → `run_formal_phase` | validates and raises before constructing `PhaseDriver`; no `runs/` is created |
| formal scheduler guard | `experiments._require_formal_go` | non-CLI callers must pass `human_go=True` or a test double |
| budget caps | `cli` + `ledger` | smoke > 24 / pilot > 240 refused; ledger rejects over-cap launches |
| V02 budget caps | `v02/v02lab/cli.py` | smoke > 24 / pilot > 240 refused (EXIT 2) |

## Why `docs/` is frozen

`docs/` contains the v1.0 closeout evidence (claims register, ledger
reconciliation, decision log, research audit). Engineering updates in v1.1 do
not rewrite it: the manifest keeps the v1.0 hashes, and any new engineering
document lives at the repository root (this file, `TESTING.md`, etc.). This is
intentional — audit trails must not be edited to fit later conclusions.
