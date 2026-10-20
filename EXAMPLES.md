# Examples

## 1. Offline synthetic demo (default, no simulation)

`examples/offline_demo.py` walks through the four-condition design with a toy
closing-time formula. It imports `cornercaselab.domain` (for the scenario
schema) and `safefliplab.domain` (for the frozen interventions), **never** the
simulator: zero episodes, zero files written.

```bash
python examples/offline_demo.py
```

Expected shape of the output (values are synthetic and arbitrary):

```text
========================================================================
SYNTHETIC OUTPUT - NOT EXPERIMENTAL RESULTS
========================================================================
anchor: ego_speed=27.0 m/s, front_gap=45.0 m, front_speed=25.0 m/s
design: gap +2.0 m, speed -1.0 m/s; shared perturbation -0.80 s
------------------------------------------------------------------------
condition 00  control          toy min-TTC =   21.70 s
condition 10  gap only         toy min-TTC =   22.70 s
condition 01  speed only       toy min-TTC =   44.20 s
condition 11  both             toy min-TTC =   46.20 s
------------------------------------------------------------------------
delta gap   (10-00) = +1.00 s
...
These numbers come from a toy formula, not from a simulator run.
```

> **Synthetic, not experimental results.** The toy formula is
> `front_gap / max(0.1, ego_speed - front_speed) + shared_perturbation`. Its
> sign and magnitude were chosen for readability. The `I_lin` line is a toy
> artefact of that formula. Nothing here estimates an effect, and the demo
> says nothing about the real study (which reports **INCONCLUSIVE**).

## 2. Look at the frozen real results (read-only)

The study's actual outputs already exist in this repository:

| Path | What it is |
|---|---|
| `reports/pilot_report.md`, `reports/pilot_summary.json` | V01 pilot summary (binary endpoint: 264/264 zero collisions) |
| `reports/v02/REPORT.zh-CN.md` | V02 Chinese research report (hypothesis verdicts, limits) |
| `v02/reports/pilot_summary.json` | V02 machine-readable summary (M1/M2 estimates, intervals) |
| `reports/v02/pilot/figure_*.png` | V02 figures |

These are **descriptive/exploratory** artefacts. All four primary intervals
cross zero, M1 and M2 disagree in direction on `Δgap`, and the endpoint
resolution is the same order as the observed effects. See
`docs/CLAIMS_REGISTER.zh-CN.md` (C1–C18 allowed claims, X1–X17 forbidden
readings) before quoting any number.

To get a structured, read-only summary (and a result figure) straight from the
published summaries, run:

```bash
python examples/read_real_results.py            # pilot, writes docs/assets/result_summary.png
python examples/read_real_results.py --phase smoke --no-plot
```

It reads only the public `v02/reports/` summaries (no private `runs/` data),
prints `REAL HISTORICAL RESULTS — READ ONLY` banners, cross-checks recomputed
anchor means against the stored point estimates, and launches **zero** episodes.
See the header docstring for the four content classes (synthetic / real
historical / recomputable / requires-private-data).

## 3. Write your own offline experiment (FakeAdapter)

For a custom offline exercise, use the test doubles instead of the simulator:

- `tests/fakes.py::FakeAdapter` — deterministic V01 results, `is_test_double=True`;
- `v02/v02lab/fake_adapter.py::FakeAdapterV02` — the V02 equivalent.

They are designed to be driven through `PhaseDriver` (V01) or the V02 phases
with a **temporary** project root, so no repository file is touched. Look at
`tests/test_experiments.py` and `v02/tests/` for worked patterns. Do not point
them at the repository root: a `runs/` directory would be created there (and is
gitignored).

## 4. What not to do

- Do not present synthetic demo output as a result.
- Do not run `smoke`/`pilot` to "see what happens": every episode is billed
  before it runs and the released snapshot contains no ledger; read
  `docs/OWNER_GUIDE.zh-CN.md` first.
- `formal` is NO-GO in this release (double-flag gate, then a hard refusal).
