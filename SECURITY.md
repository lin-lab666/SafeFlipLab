# Security policy

## Supported versions

| Version | Support |
|---|---|
| v1.1 (current engineering branch) | security fixes accepted |
| v1.0 research package (`baee8bec…`) | frozen; no changes (byte-level manifest) |

## Reporting a vulnerability

This repository is **private**. Please report vulnerabilities by **opening a
private security advisory on GitHub** (`Security` tab → `Report a
vulnerability`) or by contacting the maintainer through the repository's
existing private channel. **Do not open a public issue** and do not include
exploit details in a PR description.

No email address is published in this repository on purpose. A placeholder
address would invite reports to a mailbox nobody reads.

We aim to acknowledge within a few working days. Please include: affected
version/commit, reproduction steps, impact, and whether raw data or credentials
could be exposed.

## Secrets policy

- The repository contains **no credentials, tokens, keys or personal paths**
  (verified with pattern scans across the working tree and the full git
  history at v1.1: 16 pattern classes, zero hits).
- `.gitignore` excludes virtual environments, caches, `runs/` and ledgers.
- CI (`.github/workflows/ci.yml`) uses **no secrets**, runs with
  `permissions: contents: read`, and is **manual-only** (`workflow_dispatch`).
  It only installs the `test` extra and runs offline unit tests.
- Contributors must not commit real ledgers, episode JSON, environment dumps,
  or anything under `runs/` / `v02/runs/`.

## Safety gates (product behaviour)

| Gate | Effect |
|---|---|
| `formal` double flag | requires both `--confirm` and `--max-episodes 12800`; otherwise EXIT 2 |
| zero-side-effect refusal | validation/refusal happens before any `runs/` directory or ledger is created |
| `_require_formal_go` | non-CLI callers must pass `human_go=True` or an explicit test double |
| budget caps | smoke ≤ 24, pilot ≤ 240; the ledger rejects over-cap launches (no free retries) |
| read-only `doctor` | never creates a ledger; reports `no ledger in this checkout` instead |

If you find a way to bypass any of these gates (e.g. an entry point that
constructs a real adapter and starts episodes without a human GO), treat it as
a **security issue** and report it privately.

## CI does not touch credentials

The workflow checks out the repository with the default read-only token, sets
up Python, installs `.[test]`, runs the two suites, runs
`scripts/verify_publication.py` and the static offline guard. It never exports
secrets and never calls the simulator.
