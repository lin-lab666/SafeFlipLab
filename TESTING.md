# Testing

## Commands and expected results

| Suite | Command | Expected |
|---|---|---|
| V01 | `python -m unittest discover -s tests -q` | **Ran 234 tests, OK (skipped=1)**, EXIT 0 |
| V02 | `cd v02 && python -m unittest discover -s tests -q` (interpreter from the parent `.venv`) | **Ran 143 tests, OK**, EXIT 0 |

V01 = 227 original tests + 7 side-effect regression tests added in v1.1
(`tests/test_formal_no_side_effects.py`: 5, `tests/test_doctor_readonly.py`: 2).

## Why one test is skipped

`tests/test_ledger_safety.py::test_legacy_activity_ledger_reads_compat` reads
the project-internal legacy ledger `runs/episode_ledger.csv`. The published
snapshot intentionally ships **without** `runs/` (raw data stays with the
project owner), so the test skips itself. This is a **designed skip**, not a
failure.

## Repeat-run stability (fixed in v1.1)

Earlier versions had two side effects that made the second consecutive run
fail (`test_ledger_safety` saw an empty ledger → `0 != 24`):

- the CLI formal-guard test called the real `run_formal_phase`, which
  constructed a `PhaseDriver` (creating `runs/` + an empty ledger) before
  refusing;
- `safefliplab doctor` constructed `EpisodeLedger` on a missing path, which
  also created `runs/`.

Both are fixed (v1.1): the refusal happens **before** any filesystem side
effect, and `doctor` is strictly read-only. Running the suite twice in a row
now yields `OK (skipped=1)` both times and leaves **no `runs/`**. Regression
coverage: `tests/test_formal_no_side_effects.py`,
`tests/test_doctor_readonly.py`.

## Isolation advice

- Run from a clean checkout; do not point the tests at a working directory that
  contains your own `runs/` unless you mean to exercise the legacy-ledger test.
- Real simulations write to `runs/` and are **not** part of the unit suites.
  If you have run `smoke`/`pilot` locally, `runs/` will exist (gitignored) and
  the legacy test will stop skipping — that is expected behaviour, not a bug.
- Never run tests with the `.[sim]` extras expecting episodes: every test uses
  `FakeAdapter` / synthetic data.

## CI

`.github/workflows/ci.yml` is **manual-only** (`workflow_dispatch`). It runs
the two suites on a Python 3.11/3.12/3.13 matrix, then
`scripts/verify_publication.py`. It uses no secrets and has a read-only token
(`permissions: contents: read`). Push/PR triggers are intentionally not
enabled: this is a private repository and automatic runs consume Actions
minutes — enable them only with explicit owner approval.

The workflow contains an offline guard: a step fails the build if any test
invokes `smoke` / `pilot` / `formal --confirm` (i.e. if a future change would
launch real episodes from the test suite).
