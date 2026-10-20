# Quickstart (5 minutes, offline — no simulation)

This path runs the unit tests and the synthetic offline demo. It launches **no
simulator episodes** and needs no ledger.

```powershell
# 1) clone + virtual environment
git clone https://github.com/lin-lab666/SafeFlipLab.git
cd SafeFlipLab
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"

# 2) V01 tests (expected: Ran 242 tests, OK (skipped=1))
.\.venv\Scripts\python.exe -m unittest discover -s tests -q

# 3) V02 tests (expected: Ran 143 tests, OK)
cd v02
..\.venv\Scripts\python.exe -m unittest discover -s tests -q
cd ..

# 4) synthetic offline demo (FakeAdapter; not experimental results)
.\.venv\Scripts\python.exe examples/offline_demo.py

# 5) integrity check of this snapshot
.\.venv\Scripts\python.exe scripts/verify_publication.py
```

Linux/macOS: replace `python`/`.\.venv\Scripts\python.exe` with
`python3`/`./.venv/bin/python` and use `/` in paths.

## What you should see

- V01: `Ran 242 tests, OK (skipped=1)` — the single skip needs the
  project-internal legacy ledger, which the published snapshot does not
  contain (designed skip).
- V02: `Ran 143 tests, OK`.
- `examples/offline_demo.py`: a short report of **synthetic** quartet numbers,
  with a banner saying `SYNTHETIC OUTPUT — NOT EXPERIMENTAL RESULTS`.
- `scripts/verify_publication.py`: `PASS` and a two-scope summary
  (`v1.0 research package` byte-exact + `v1.1 engineering scope` additions).

## How to read the output

- The demo prints condition means and a `Δ` (treatment − control) computed from
  a fixed synthetic trajectory. It exists to show the *shape* of the pipeline,
  not to estimate any effect.
- The real study's numbers live in `reports/` and `v02/reports/` (frozen at
  v1.0). They are **descriptive and exploratory**: all reported intervals cross
  zero, M1 and M2 disagree in direction on `Δgap`, and the endpoint resolution
  is the same order as the observed effects. Do not read them as evidence of
  safety, risk, or method superiority — see `DATA_AVAILABILITY.md` and
  `docs/CLAIMS_REGISTER.zh-CN.md` (X1–X17) for the full list of forbidden
  readings.

## If you actually want to run simulations

Read `INSTALLATION.md` (use the `.[sim]` extra), then
`docs/OWNER_GUIDE.zh-CN.md` and `docs/REPRODUCTION_MANUAL.zh-CN.md`. Every
episode is billed before it runs; `formal` is NO-GO in the released state.
