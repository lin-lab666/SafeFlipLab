# Provenance and copyright — SafeFlipLab

## Ownership

- **Owner / copyright holder:** 吴昊霖 (GitHub: lin-lab666)
- **Project:** SafeFlipLab (independent of CornerCaseLab; new research code)
- **Recorded:** 2026-10-12

## What is original here

SafeFlipLab's own code (four-condition quartet protocol, anchor stream with
quartet-legality rejection, paired sim-seed derivation, the two budgeted
methods, the independent audit isolation, the ledger/accounting and the
statistics) was written for this project. AI was used as an assistance tool
for drafting, testing and documentation; it is not an author or copyright
holder.

## What is reused (and how)

- **CornerCaseLab v0.3.0** (Apache-2.0, (c) 吴昊霖 / lin-lab666,
  https://github.com/lin-lab666/CornerCaseLab) is used as an **installed
  dependency**, through its public interface only:
  `cornercaselab.domain` (scenario schema `merge-scenario-v1`, six bounds),
  `cornercaselab.simulator` (HighwayEnv `MergeEnv` adapter, `evaluate`),
  `cornercaselab.policy` (the frozen `boundary` observation-only controller).
  No CornerCaseLab source file is copied or vendored into this repository.
  The pinned commit is the tag `v0.3.0`; the package is not on PyPI.
- **HighwayEnv 1.10.2 / Gymnasium 1.2.2 / NumPy / Pillow / matplotlib /
  pygame** are installed dependencies with their own licences (MIT, Apache-2.0,
  MIT, MIT, HPND, LGPL respectively for the versions pinned). None is bundled.

## Publication status

No remote repository has been created, nothing has been pushed or published,
and nothing in this project does so automatically.

## Licence of this project's own files

Apache-2.0 — see `LICENSE`. That licence covers only SafeFlipLab's own files.
