# Installation

SafeFlipLab is a Python package (`safefliplab`, Python 3.11–3.13). Two extras
are defined in `pyproject.toml`:

| Extra | Installs | Use it when |
|---|---|---|
| `test` | `cornercaselab` (git tag), `pytest`, `numpy`, `matplotlib`, `Pillow` | You want to run the unit test suites (V01 + V02). No simulator episodes are launched. |
| `sim` | `cornercaselab`, `highway-env==1.10.2`, `gymnasium==1.2.2`, `numpy`, `Pillow`, `matplotlib` | You intend to run *real* simulation episodes (`smoke`/`pilot`). Read `docs/OWNER_GUIDE.zh-CN.md` and `docs/REPRODUCTION_MANUAL.zh-CN.md` first — every launched episode is billed. |

`cornercaselab` is **not on PyPI**; it is pinned to a GitHub tag
(`git+https://github.com/lin-lab666/CornerCaseLab@v0.3.0`). pip therefore needs
read access to that repository (HTTPS + git). If your environment cannot reach
GitHub, install from a local checkout of the same tag and point pip at it
manually — the API surface used here is limited to the scenario schema and the
adapter types.

## Windows (PowerShell)

```powershell
git clone https://github.com/lin-lab666/SafeFlipLab.git
cd SafeFlipLab
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m safefliplab doctor
```

## Linux / macOS

```bash
git clone https://github.com/lin-lab666/SafeFlipLab.git
cd SafeFlipLab
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e ".[test]"
./.venv/bin/python -m safefliplab doctor
```

## Notes

- The repository snapshot **does not contain** raw episode data or ledgers
  (`runs/`, `v02/runs/`). Tests and the offline example run against synthetic
  data / `FakeAdapter`; nothing is simulated for real.
- `doctor` is strictly read-only: on a checkout without a ledger it reports
  `no ledger in this checkout (0/<cap>)` and creates nothing.
- Running tests twice in a row is safe (since v1.1): neither the tests nor
  `doctor` write into `runs/`.
- A copy of the pinned versions lives in `requirements.txt` (the `sim` stack);
  `pyproject.toml` is authoritative for packaging.
- Offline machines: pre-fetch the wheels/git dependency on a connected machine
  (`pip download`) and install with `--no-index --find-links <dir>`; the
  `cornercaselab` git dependency must be vendored as a local path/wheel.
- See `QUICKSTART.md` for the 5-minute offline path and `TESTING.md` for the
  exact expected test counts.
