"""Phase drivers: smoke, pilot and the prepared-but-not-run formal phase.

Budget rules enforced here:

* every launched episode is billed in the global ``EpisodeLedger`` (the
  runner records the launch before execution);
* a phase never exceeds its cap (``BudgetExhausted`` otherwise);
* re-invoking a phase is safe: quartets already completed in that phase are
  loaded from the ledger instead of being re-launched (evidence-based
  resume; no free retries, no fabricated continuity);
* the formal driver refuses to run unless it receives BOTH ``--confirm``
  and ``--max-episodes 12800``.

Audit isolation: nomination/selection functions only ever receive
discovery-stream records, and audit quartets are created only after the
nominee list is frozen.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from cornercaselab.domain import Scenario

from .adapter import ScenarioAdapter, fingerprint
from .domain import Anchor
from .generator import ScenarioGenerator
from .ledger import BudgetExhausted, EpisodeLedger
from .methods import (
    AUDIT_QUARTETS_PER_NOMINEE,
    FORMAL_AUDIT_BUDGET,
    FORMAL_BUDGET,
    FORMAL_DISCOVERY_BUDGET,
    METHOD_VERIFY,
    METHOD_WIDE,
    METHODS,
    VERIFY_EXTRA_QUARTETS,
    VERIFY_SELECTED,
    VERIFY_STAGE1_ANCHORS,
    WIDE_DISCOVERY_ANCHORS,
    WIDE_NOMINEES,
    AnchorRecord,
    QuartetJob,
    add_quartet,
    audit_jobs,
    budget_check,
    select_top,
    verify_final_key,
    verify_select_key,
    verify_stage1_jobs,
    verify_stage2_jobs,
    wide_discovery_jobs,
    wide_nomination_key,
)
from .protocol import (
    FormalConfigError,
    frozen_protocol_fingerprint,
    validate_formal_config,
)
from .runner import QuartetResult, SimulatorRunner
from . import methods as _methods
from .seeds import (
    CONDITIONS,
    DEV_SEED,
    FORMAL_EPISODES_PER_METHOD_SEED,
    FORMAL_MASTER_SEED_COUNT,
    FORMAL_TOTAL_EPISODES,
    STREAM_AUDIT,
    STREAM_DISCOVERY,
    run_id as make_run_id,
)

RUNS_DIRNAME = "runs"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def code_fingerprint() -> str:
    """SHA-256 over the sorted package sources (reproducibility record)."""
    root = Path(__file__).resolve().parent
    h = hashlib.sha256()
    for path in sorted(root.glob("*.py")):
        h.update(path.name.encode("utf-8"))
        h.update(b"\0")
        h.update(path.read_bytes())
    return h.hexdigest()


@dataclass
class PhaseReport:
    phase: str
    method: str
    master_seed: int
    run_ids: list[str] = field(default_factory=list)
    # Quartet resume key = (master_seed, method, anchor_index, repetition, stream).
    # Including master_seed keeps formal's 8 seeds mutually independent.
    quartets: dict[tuple[int, str, int, int, str], dict[str, int]] = field(default_factory=dict)
    nominations: dict[str, list[str]] = field(default_factory=dict)
    audit_results: dict[str, list[dict[str, int]]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "method": self.method,
            "master_seed": self.master_seed,
            "run_ids": self.run_ids,
            "n_quartets": len(self.quartets),
            "quartets": {
                f"{ms}|{m}|a{ai}|r{rep}|{stream}": y
                for (ms, m, ai, rep, stream), y in self.quartets.items()
            },
            "nominations": self.nominations,
            "audit_nominees": {k: len(v) for k, v in self.audit_results.items()},
            "audit_results": self.audit_results,
            "notes": self.notes,
        }


class PhaseDriver:
    """Executes one method's plan inside one phase, with resume support."""

    def __init__(self, *, phase: str, method: str, master_seed: int, max_episodes: int,
                 project_root: str | Path, adapter: Any | None = None) -> None:
        if phase not in ("smoke", "pilot", "formal"):
            raise ValueError(f"unknown phase {phase!r}")
        self.phase = phase
        self.method = method
        self.master_seed = master_seed
        self.max_episodes = max_episodes
        # Budget scope for the ledger. smoke/pilot share the phase-total cap
        # (the two methods together fill it exactly by protocol), so their scope
        # is simply the phase. Formal uses a tighter per-(method, seed) scope so
        # all 8 seeds x 2 methods are bounded independently instead of colliding
        # on the phase-total cap.
        self._budget_scope = (
            None if phase in ("smoke", "pilot")
            else f"{phase}|{method}|{master_seed}"
        )
        self.root = Path(project_root)
        self.runs_root = self.root / RUNS_DIRNAME
        self.runs_root.mkdir(parents=True, exist_ok=True)
        self.ledger = EpisodeLedger(self.runs_root / "episode_ledger.csv")
        self._launch_rows: dict[str, dict[str, str]] = {}
        self._outcome_rows: dict[str, dict[str, str]] = {}
        self._completed: dict[tuple[str, int, int, str], dict[str, dict[str, int]]] = {}
        self.ledger.add_listener(self._note_outcome)
        self._load_ledger_view()
        self.adapter = adapter if adapter is not None else ScenarioAdapter()
        self.runner = SimulatorRunner(self.adapter, self.ledger, self.runs_root)
        self.generator = ScenarioGenerator(master_seed)
        self.report = PhaseReport(phase=phase, method=method, master_seed=master_seed)

    # -- resume support ---------------------------------------------------
    def _load_ledger_view(self) -> None:
        """One-pass load of the ledger into in-memory views (O(n))."""
        self._launch_rows: dict[str, dict[str, str]] = {}
        self._outcome_rows: dict[str, dict[str, str]] = {}
        self._completed: dict[tuple[str, int, int, str], dict[str, dict[str, int]]] = {}
        for row in self._ledger_rows():
            if row["row_type"] == "launch":
                self._launch_rows[row["episode_key"]] = row
            elif row["row_type"] == "outcome":
                self._outcome_rows[row["episode_key"]] = row
                self._index_completed(row)

    def _index_completed(self, outcome_row: dict[str, str]) -> None:
        if outcome_row["exit_status"] != "completed":
            return
        if str(outcome_row["ego_collision"]) not in ("0", "1"):
            return
        launch = self._launch_rows.get(outcome_row["episode_key"])
        if launch is None:
            return
        # Isolation: a completed quartet in another phase (e.g. smoke) or
        # another master seed (e.g. a different formal seed) must never be
        # mistaken for evidence in this driver's (phase, master_seed) scope.
        # Without the master_seed check, formal's 8 seeds would share one
        # ledger + one phase="formal" and seed B would silently reuse seed A's
        # completed quartets without launching its own observations.
        if launch.get("phase") != self.phase:
            return
        if int(launch.get("master_seed")) != self.master_seed:
            return
        key = (self.master_seed, launch["method"], int(launch["anchor_index"]),
               int(launch["repetition"]), launch["stream"])
        per_run = self._completed.setdefault(key, {})
        run_bucket = per_run.setdefault(launch["run_id"], {})
        run_bucket[launch["condition"]] = int(outcome_row["ego_collision"])

    def _note_outcome(self, launch_row: dict[str, str], outcome_row: dict[str, str]) -> None:
        # Only index rows that belong to this driver's (phase, master_seed).
        # Cross-phase or cross-seed launches are ignored so the resume logic
        # can never reuse another phase/seed's completed quartets.
        if launch_row.get("phase") != self.phase:
            return
        if int(launch_row.get("master_seed")) != self.master_seed:
            return
        self._launch_rows[launch_row["episode_key"]] = launch_row
        self._outcome_rows[outcome_row["episode_key"]] = outcome_row
        self._index_completed(outcome_row)

    def _ledger_rows(self) -> list[dict[str, str]]:
        import csv

        path = self.runs_root / "episode_ledger.csv"
        if not path.exists():
            return []
        with open(path, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def _phase_launches(self) -> list[dict[str, str]]:
        return [r for r in self._launch_rows.values() if r["phase"] == self.phase]

    def completed_quartets(self) -> dict[tuple[int, str, int, int, str], dict[str, int]]:
        """Complete quartets of this (phase, master_seed) scope, keyed by
        (master_seed, method, anchor_index, repetition, stream). Values are the
        real Y mappings (earliest run). Cross-phase AND cross-seed rows are
        excluded by the indexing filters, so a driver only ever sees its own
        completed quartets."""
        done: dict[tuple[str, int, int, str], dict[str, int]] = {}
        for key, per_run in self._completed.items():
            for run_id in sorted(per_run):
                conds = per_run[run_id]
                if set(conds) == set(CONDITIONS):
                    done[key] = dict(conds)
                    break
        return done

    def runs_completing_key(self, key: tuple[str, int, int, str]) -> list[str]:
        """Distinct run_ids that completed ALL four conditions of this key."""
        per_run = self._completed.get(key, {})
        return sorted(run for run, conds in per_run.items() if set(conds) == set(CONDITIONS))

    # -- job execution ----------------------------------------------------
    def _new_run_id(self, method: str | None = None) -> str:
        """New run id for the method that will actually be recorded.

        ``run_smoke`` drives BOTH methods through a single driver, so the run
        id must take the *job's* method. Deriving it from ``self.method`` would
        stamp the first-stage VerifyFirst quartets of the smoke phase with a
        ``WideExplore`` label (see DECISION_LOG D27) even though every ledger
        row, ``sim_seed`` and raw record carries ``VerifyFirst``.
        """
        rid = make_run_id(self.phase, method or self.method, self.master_seed, _utc_now_iso())
        self.report.run_ids.append(rid)
        return rid

    def execute_job(self, job: QuartetJob, *, force: bool = False) -> dict[str, int] | None:
        """Run or resume one quartet job. Returns the Y mapping (or None)."""
        anchor = self.generator.anchor(job.anchor_index)
        key = (self.master_seed, job.method, job.anchor_index, job.repetition, job.stream)
        done = self.completed_quartets()
        if not force and key in done:
            self.report.quartets[key] = done[key]
            return done[key]
        run_id = self._new_run_id(job.method)
        result: QuartetResult = self.runner.run_quartet(
            run_id=run_id, phase=self.phase, method=job.method,
            master_seed=self.master_seed, anchor=anchor, repetition=job.repetition,
            stream=job.stream, max_episodes=self.max_episodes,
            budget_scope=self._budget_scope,
        )
        y = result.y
        if y is not None:
            self.report.quartets[key] = y
        return y

    def _records_for(self, keys, stream: str = STREAM_DISCOVERY) -> dict[str, AnchorRecord]:
        """Build AnchorRecords for the given (anchor_index) keys from completed
        quartets of *this* (phase, method, seed) that belong to ``stream``.

        The ``stream`` filter is essential: nomination/selection must only ever
        read DISCOVERY observations, and ``audit_results`` must only ever read
        AUDIT observations. Without it, ``audit_results`` would silently mix the
        discovery quartet of a nominee into its own audit aggregate (the bug
        fixed here).
        """
        wanted = set(keys)
        records: dict[int, AnchorRecord] = {}
        for (ms, method, anchor_index, repetition, qstream), y in self.completed_quartets().items():
            if ms != self.master_seed:
                continue
            if method != self.method or qstream != stream or anchor_index not in wanted:
                continue
            rec = records.setdefault(anchor_index, AnchorRecord(
                anchor_id=self.generator.anchor(anchor_index).anchor_id, index=anchor_index))
            add_quartet(rec, y)
        return {self.generator.anchor(i).anchor_id: rec for i, rec in records.items()}

    # -- manifests --------------------------------------------------------
    def write_manifest(self, extra: dict[str, Any] | None = None) -> Path:
        manifest = {
            "protocol": "SafeFlipLab-v01",
            "phase": self.phase,
            "method": self.method,
            "master_seed": self.master_seed,
            "max_episodes": self.max_episodes,
            "episodes_launched_phase_total": self.ledger.launched_count(self.phase),
            "episodes_completed_phase_total": self.ledger.outcome_count(self.phase, "completed"),
            "episodes_errored_phase_total": self.ledger.outcome_count(self.phase, "error"),
            "adapter_fingerprint": fingerprint().to_dict(),
            "code_fingerprint": code_fingerprint(),
            "written_utc": _utc_now_iso(),
            "report": self.report.to_dict(),
        }
        if extra:
            manifest.update(extra)
        # One manifest per (phase, method) invocation set; run-specific
        # manifests live under runs/<run_id>/.
        path = self.runs_root / f"manifest_{self.phase}_{self.method}.json"
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return path

    # -- WideExplore ------------------------------------------------------
    def run_wide_explore(self, *, discovery_anchors: int, nominees: int,
                         audit_quartets: int) -> PhaseReport:
        jobs = wide_discovery_jobs(discovery_anchors)
        for job in jobs:
            self.execute_job(job)
        records = self._records_for(range(discovery_anchors))
        pool = list(records.values())
        if not pool:
            raise RuntimeError("WideExplore: no complete discovery quartet to nominate from")
        nominated = select_top(pool, wide_nomination_key, nominees)
        self.report.nominations["discovery"] = [r.anchor_id for r in nominated]
        nominee_indices = [r.index for r in nominated]
        for job in audit_jobs(METHOD_WIDE, nominee_indices, audit_quartets):
            self.execute_job(job)
        # Audit results read the AUDIT stream only -- never the discovery quartet
        # of the same nominee (that would conflate discovery and audit evidence).
        audit_records = self._records_for(nominee_indices, stream=STREAM_AUDIT)
        self.report.audit_results["audit"] = [
            {"anchor_id": aid, **rec.to_dict()} for aid, rec in audit_records.items()
        ]
        return self.report

    # -- VerifyFirst ------------------------------------------------------
    def run_verify_first(self, *, stage1_anchors: int, selected: int, extra: int,
                         nominees: int, audit_quartets: int) -> PhaseReport:
        for job in verify_stage1_jobs(stage1_anchors):
            self.execute_job(job)
        stage1 = self._records_for(range(stage1_anchors))
        pool = list(stage1.values())
        if len(pool) < selected:
            raise RuntimeError(
                f"VerifyFirst: only {len(pool)} complete stage-1 anchors, need {selected}")
        chosen = select_top(pool, verify_select_key, selected)
        self.report.nominations["selected_20_scaled"] = [r.anchor_id for r in chosen]
        for job in verify_stage2_jobs([r.index for r in chosen], extra):
            self.execute_job(job)
        # Final nomination pool: ALL stage-1 anchors (with their extra quartets).
        final_records = self._records_for(range(stage1_anchors))
        nominated = select_top(list(final_records.values()), verify_final_key, nominees)
        self.report.nominations["final"] = [r.anchor_id for r in nominated]
        nominee_indices = [r.index for r in nominated]
        for job in audit_jobs(METHOD_VERIFY, nominee_indices, audit_quartets):
            self.execute_job(job)
        # Audit results read the AUDIT stream only (see run_wide_explore).
        audit_records = self._records_for(nominee_indices, stream=STREAM_AUDIT)
        self.report.audit_results["audit"] = [
            {"anchor_id": aid, **rec.to_dict()} for aid, rec in audit_records.items()
        ]
        return self.report

    # -- phases -----------------------------------------------------------
    def run_smoke(self, *, wide_discovery_anchors: int, verify_stage1_anchors: int,
                  determinism_replay: bool = True) -> PhaseReport:
        started = time.perf_counter()
        # 1. WideExplore discovery quartets.
        for job in wide_discovery_jobs(wide_discovery_anchors):
            self.execute_job(job)
        # 2. VerifyFirst stage-1 quartets (same shared anchor stream).
        for job in verify_stage1_jobs(verify_stage1_anchors):
            self.execute_job(job)
        # 3. Same-seed replay determinism check (always a fresh launch).
        determinism: dict[str, Any] = {"performed": False}
        if determinism_replay:
            anchor = self.generator.anchor(0)
            key = (self.master_seed, METHOD_WIDE, 0, 0, STREAM_DISCOVERY)
            prior_runs = self.runs_completing_key(key)
            if len(prior_runs) >= 2:
                determinism = self._compare_replays(prior_runs[0], prior_runs[1])
            elif len(prior_runs) == 1:
                replay_run = self._new_run_id(METHOD_WIDE)
                self.runner.run_quartet(
                    run_id=replay_run, phase=self.phase, method=METHOD_WIDE,
                    master_seed=self.master_seed, anchor=anchor, repetition=0,
                    stream=STREAM_DISCOVERY, max_episodes=self.max_episodes,
                )
                determinism = self._compare_replays(prior_runs[0], replay_run)
            else:
                determinism = {"performed": False,
                               "note": "no completed base quartet to replay"}
        elapsed = time.perf_counter() - started
        self.report.notes.append(f"smoke wall_time_s={elapsed:.2f}")
        self.write_manifest({"determinism_check": determinism,
                             "budget": {"max_episodes": self.max_episodes,
                                        "launched": self.ledger.launched_count(self.phase)}})
        return self.report

    def _compare_replays(self, run_a: str, run_b: str) -> dict[str, Any]:
        """Compare per-condition trace hashes of two completed runs of the
        same quartet key (same anchor, repetition, stream, sim_seed)."""
        rows = [r for r in self._ledger_rows()
                if r["row_type"] == "outcome" and r["run_id"] in (run_a, run_b)
                and r["phase"] == self.phase]
        per_condition: dict[str, Any] = {}
        all_match = True
        for cond in CONDITIONS:
            recs = {}
            for run in (run_a, run_b):
                for row in rows:
                    if row["run_id"] == run and row["condition"] == cond and row["raw_path"]:
                        recs[run] = row["raw_path"]
            if len(recs) != 2:
                per_condition[cond] = {"match": False, "reason": "missing raw record"}
                all_match = False
                continue
            hashes = {}
            for run, path in recs.items():
                payload = json.loads(Path(path).read_text(encoding="utf-8"))
                hashes[run] = payload["result"]["trace_sha256_rounded_9dp"]
            match = len(set(hashes.values())) == 1
            all_match = all_match and match
            per_condition[cond] = {"match": match, "trace_sha256": hashes}
        return {"performed": True, "run_a": run_a, "run_b": run_b,
                "all_conditions_match": all_match, "per_condition": per_condition}

    def run_pilot(self, *, wide_discovery_anchors: int, wide_nominees: int,
                  audit_quartets: int, verify_stage1_anchors: int, verify_selected: int,
                  verify_extra: int, adapter: Any | None = None) -> dict[str, PhaseReport]:
        # Exact-budget plan check: the pilot must close at the cap, no more,
        # no less (protocol: budgets are used exactly).
        planned_quartets = (
            wide_discovery_anchors
            + wide_nominees * audit_quartets
            + verify_stage1_anchors
            + verify_selected * verify_extra
            + wide_nominees * audit_quartets
        )
        planned_episodes = 4 * planned_quartets
        if planned_episodes != self.max_episodes:
            raise RuntimeError(
                f"pilot plan needs {planned_episodes} episodes but cap is "
                f"{self.max_episodes}; refusing to run a partial/over plan")
        started = time.perf_counter()
        wide = PhaseDriver(phase="pilot", method=METHOD_WIDE, master_seed=self.master_seed,
                           max_episodes=self.max_episodes, project_root=self.root,
                           adapter=adapter)
        wide_report = wide.run_wide_explore(
            discovery_anchors=wide_discovery_anchors, nominees=wide_nominees,
            audit_quartets=audit_quartets)
        verify = PhaseDriver(phase="pilot", method=METHOD_VERIFY, master_seed=self.master_seed,
                             max_episodes=self.max_episodes, project_root=self.root,
                             adapter=adapter)
        verify_report = verify.run_verify_first(
            stage1_anchors=verify_stage1_anchors, selected=verify_selected, extra=verify_extra,
            nominees=wide_nominees, audit_quartets=audit_quartets)
        elapsed = time.perf_counter() - started
        # The summary MUST read the durable ledger, not this (pilot) driver's
        # in-memory view: that view was built before the wide/verify sub-drivers
        # ran and would otherwise report a stale (under-)count. A fresh ledger
        # reader reflects every row the sub-drivers appended.
        summary_ledger = EpisodeLedger(self.runs_root / "episode_ledger.csv")
        combined = {
            "pilot_wall_time_s": round(elapsed, 2),
            "episodes_launched": summary_ledger.launched_count("pilot"),
            "episodes_completed": summary_ledger.outcome_count("pilot", "completed"),
            "episodes_errored": summary_ledger.outcome_count("pilot", "error"),
        }
        (self.runs_root / "manifest_pilot_summary.json").write_text(
            json.dumps(combined, indent=2, sort_keys=True), encoding="utf-8")
        return {METHOD_WIDE: wide_report, METHOD_VERIFY: verify_report}

    def run_formal(self, *, confirm: bool, max_episodes: int) -> dict[str, Any]:
        """Prepared formal driver. Refuses without explicit confirmation.

        This method is the hard safety lock: it validates the human-GO flags and
        then raises ``RuntimeError`` without running anything. The real scheduling
        logic lives in :func:`_execute_formal_phase` (reachable only by code that
        explicitly calls it, never by the CLI, which funnels through here).
        """
        _formal_refusal_plan(confirm=confirm, max_episodes=max_episodes)

    def write_formal_manifest(self, *, master_seed: int, batch: str | None = None) -> Path:
        """Per-(seed, method) manifest. Unlike ``write_manifest`` (which writes
        ``manifest_formal_{method}.json`` and would be overwritten by the next
        seed), this writes a seed-specific path so all 8 seeds x 2 methods keep
        their own manifest and never clobber each other."""
        manifest = {
            "protocol": "SafeFlipLab-v01",
            "phase": self.phase,
            "method": self.method,
            "master_seed": master_seed,
            "max_episodes": self.max_episodes,
            "budget_scope": self._budget_scope,
            "episodes_launched_scope": self.ledger.launched_count_scope(self._budget_scope)
            if self._budget_scope else self.ledger.launched_count(self.phase),
            "episodes_launched_phase_total": self.ledger.launched_count(self.phase),
            "episodes_completed_phase_total": self.ledger.outcome_count(self.phase, "completed"),
            "episodes_errored_phase_total": self.ledger.outcome_count(self.phase, "error"),
            "adapter_fingerprint": fingerprint().to_dict(),
            "code_fingerprint": code_fingerprint(),
            "written_utc": _utc_now_iso(),
            "report": self.report.to_dict(),
        }
        suffix = f"_seed{master_seed}" + (f"_{batch}" if batch else "")
        path = self.runs_root / f"manifest_formal_{self.method}{suffix}.json"
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return path


# -- phase entry points ------------------------------------------------------
def load_json_config(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_smoke_phase(project_root: str | Path, config_path: str | Path,
                    max_episodes: int | None = None,
                    adapter: Any | None = None) -> PhaseReport:
    cfg = load_json_config(config_path)
    smoke = cfg["smoke"]
    cap = max_episodes if max_episodes is not None else smoke["max_episodes"]
    if cap > smoke["max_episodes"]:
        raise ValueError(f"smoke cap {cap} exceeds protocol maximum {smoke['max_episodes']}")
    driver = PhaseDriver(phase="smoke", method=METHOD_WIDE, master_seed=cfg["dev_seed"],
                         max_episodes=cap, project_root=project_root, adapter=adapter)
    return driver.run_smoke(
        wide_discovery_anchors=smoke["wide_discovery_anchors"],
        verify_stage1_anchors=smoke["verify_stage1_anchors"],
        determinism_replay=smoke.get("determinism_replay", True),
    )


def run_pilot_phase(project_root: str | Path, config_path: str | Path,
                    max_episodes: int | None = None,
                    adapter: Any | None = None) -> dict[str, PhaseReport]:
    cfg = load_json_config(config_path)
    pilot = cfg["pilot"]
    cap = max_episodes if max_episodes is not None else pilot["max_episodes"]
    if cap > pilot["max_episodes"]:
        raise ValueError(f"pilot cap {cap} exceeds protocol maximum {pilot['max_episodes']}")
    driver = PhaseDriver(phase="pilot", method=METHOD_WIDE, master_seed=cfg["dev_seed"],
                         max_episodes=cap, project_root=project_root, adapter=adapter)
    return driver.run_pilot(
        wide_discovery_anchors=pilot["wide_discovery_anchors"],
        wide_nominees=pilot["wide_nominees"],
        audit_quartets=pilot["audit_quartets_per_nominee"],
        verify_stage1_anchors=pilot["verify_stage1_anchors"],
        verify_selected=pilot["verify_selected"],
        verify_extra=pilot["verify_extra_quartets"],
        adapter=adapter,
    )


def _formal_refusal_plan(*, confirm: bool, max_episodes: int) -> None:
    """Validate the formal human-GO flags and raise the standard refusal.

    Factored out of :meth:`PhaseDriver.run_formal` so that
    :func:`run_formal_phase` can refuse **before** constructing a
    ``PhaseDriver``. Driver construction creates ``runs/`` and an empty ledger
    (``PhaseDriver.__init__`` -> ``mkdir`` + header write), so the refusal path
    must have **zero filesystem side effects** (GH-2 fix; the pre-fix order let
    the CLI tests leave a ``runs/`` residue and broke repeat test runs).

    Always raises; never returns.
    """
    if not confirm:
        raise PermissionError(
            "formal phase requires explicit human GO: pass --confirm")
    if max_episodes != FORMAL_TOTAL_EPISODES:
        raise PermissionError(
            f"formal phase requires --max-episodes {FORMAL_TOTAL_EPISODES}, got {max_episodes}")
    plan = {
        "status": "authorised-by-flags",
        "methods": [METHOD_WIDE, METHOD_VERIFY],
        "master_seeds": FORMAL_MASTER_SEED_COUNT,
        "episodes_per_method_seed": FORMAL_EPISODES_PER_METHOD_SEED,
        "total": FORMAL_TOTAL_EPISODES,
    }
    raise RuntimeError(
        "formal driver is implemented but NOT executed by this build; "
        "run it only after human review of pilot results. The real "
        "scheduler is _execute_formal_phase. Plan: " + json.dumps(plan))


def run_formal_phase(project_root: str | Path, config_path: str | Path, *,
                     confirm: bool, max_episodes: int) -> dict[str, Any]:
    cfg = load_json_config(config_path)
    # GH-2: refuse before any filesystem side effect. This build never executes
    # formal; the driver construction below is retained only as the structural
    # entry point for a future, explicitly authorised scheduler and is
    # unreachable while _formal_refusal_plan always raises.
    _formal_refusal_plan(confirm=confirm, max_episodes=max_episodes)
    driver = PhaseDriver(phase="formal", method=METHOD_WIDE,
                         master_seed=cfg["formal_master_seeds"][0],
                         max_episodes=max_episodes, project_root=project_root)
    return driver.run_formal(confirm=confirm, max_episodes=max_episodes)


# -- real formal scheduler (gated behind the RuntimeError lock in run_formal) --
def _require_formal_go(adapter: Any, human_go: bool) -> None:
    """Independent safety guard for every formal *execution* entry point.

    The CLI lock lives in :meth:`PhaseDriver.run_formal` (it always raises
    ``RuntimeError``). But :func:`_execute_formal_phase` and
    :func:`_run_formal_method` are module-level functions that can be reached by
    code that bypasses the CLI, and with ``adapter=None`` they would otherwise
    construct the *real* ``ScenarioAdapter``. This guard closes that hole:

    * an explicit human GO (``human_go=True``) always passes;
    * otherwise the adapter must be an explicit test double
      (``is_test_double=True``), which lets the FakeAdapter integration tests
      exercise the scheduler with zero real episodes;
    * anything else (``adapter=None``, or a non-test adapter) is refused *before*
      any simulator is constructed or any episode is launched.
    """
    if human_go:
        return
    if getattr(adapter, "is_test_double", False):
        return
    raise PermissionError(
        "formal execution is locked: requires human_go=True (an explicit human GO) "
        "or an explicit test double (is_test_double=True). Refusing to start real "
        "episodes from a non-CLI entry point.")


def _run_formal_method(driver: PhaseDriver, method: str, *,
                       human_go: bool = False) -> PhaseReport:
    """Run one (method, master_seed)'s full 400 discovery + 400 audit plan.

    Reuses the already-audited nomination/audit logic in ``run_wide_explore`` /
    ``run_verify_first``. Returns the method's PhaseReport. The exact 800-episode
    closure is asserted below against the frozen plan sizes.

    Plan sizes are read from the ``methods`` module at call time (not the frozen
    imported names) so the unit tests can scale the plan down for a fast,
    episode-free-of-real-sim integration check.
    """
    # Defense in depth: this function is directly callable, so it re-checks the
    # formal safety guard (a real adapter without a human GO must never run).
    _require_formal_go(driver.adapter, human_go)
    if method == METHOD_WIDE:
        disc_jobs = wide_discovery_jobs(_methods.WIDE_DISCOVERY_ANCHORS)
        budget_check("WideExplore formal discovery", disc_jobs,
                     _methods.WIDE_DISCOVERY_ANCHORS * 4)
        report = driver.run_wide_explore(
            discovery_anchors=_methods.WIDE_DISCOVERY_ANCHORS,
            nominees=_methods.WIDE_NOMINEES,
            audit_quartets=_methods.AUDIT_QUARTETS_PER_NOMINEE)
        audit_jobs_plan = audit_jobs(METHOD_WIDE, list(range(_methods.WIDE_NOMINEES)),
                                    _methods.AUDIT_QUARTETS_PER_NOMINEE)
        budget_check("WideExplore formal audit", audit_jobs_plan,
                     _methods.WIDE_NOMINEES * _methods.AUDIT_QUARTETS_PER_NOMINEE * 4)
    elif method == METHOD_VERIFY:
        s1_jobs = verify_stage1_jobs(_methods.VERIFY_STAGE1_ANCHORS)
        budget_check("VerifyFirst formal stage1", s1_jobs,
                     _methods.VERIFY_STAGE1_ANCHORS * 4)
        report = driver.run_verify_first(
            stage1_anchors=_methods.VERIFY_STAGE1_ANCHORS,
            selected=_methods.VERIFY_SELECTED,
            extra=_methods.VERIFY_EXTRA_QUARTETS, nominees=_methods.WIDE_NOMINEES,
            audit_quartets=_methods.AUDIT_QUARTETS_PER_NOMINEE)
        s2_jobs = verify_stage2_jobs(list(range(_methods.VERIFY_SELECTED)),
                                    _methods.VERIFY_EXTRA_QUARTETS)
        budget_check("VerifyFirst formal stage2", s2_jobs,
                     _methods.VERIFY_SELECTED * _methods.VERIFY_EXTRA_QUARTETS * 4)
        audit_jobs_plan = audit_jobs(METHOD_VERIFY, list(range(_methods.WIDE_NOMINEES)),
                                    _methods.AUDIT_QUARTETS_PER_NOMINEE)
        budget_check("VerifyFirst formal audit", audit_jobs_plan,
                     _methods.WIDE_NOMINEES * _methods.AUDIT_QUARTETS_PER_NOMINEE * 4)
    else:
        raise ValueError(f"unknown method {method!r}")
    # Guard: this (method, seed) must have spent exactly FORMAL_BUDGET episodes.
    spent = driver.ledger.launched_count_scope(driver._budget_scope)
    if spent != _methods.FORMAL_BUDGET:
        raise RuntimeError(
            f"formal {method} seed {driver.master_seed} spent {spent} episodes, "
            f"expected exactly {_methods.FORMAL_BUDGET}")
    return report


def _execute_formal_phase(project_root: str | Path, config_path: str | Path, *,
                          adapter: Any | None = None, human_go: bool = False,
                          strict_design: bool = True) -> dict[str, Any]:
    """Full formal scheduler: 8 master seeds x 2 methods x 800 episodes.

    The real, complete scheduling implementation. The CLI can never reach it
    (:func:`run_formal` / :func:`run_formal_phase` always raise the
    ``RuntimeError`` lock). To reach it directly you must pass either
    ``human_go=True`` (an explicit human GO) or an explicit test double
    (``is_test_double=True``) — see :func:`_require_formal_go`. With the default
    ``adapter=None`` and no GO it refuses *before* constructing any simulator.

    ``strict_design=False`` is used ONLY by the scaled FakeAdapter integration
    tests: it relaxes the frozen-design comparison (the plan is intentionally
    scaled down) while still enforcing seed count / uniqueness / integer type.

    Guarantees enforced here (all verifiable offline with FakeAdapter):
      * per (method, seed): **cumulative** 400 discovery + 400 audit = 800
        episodes (verified against the durable ledger, so a legal half-way
        resume does NOT false-alarm and cannot over-spend);
      * the increment billed by *this* call is recorded separately;
      * nomination is frozen before any audit launch (audit uses stream="audit");
      * each of the 8 master seeds is isolated (its own budget scope + ledger key);
      * every (seed, method) gets its own manifest (no cross-seed overwrite);
      * re-invocation resumes completed quartets (no double billing).
    """
    # Safety guard FIRST: no human GO and no test double -> refuse before any
    # simulator can be constructed or any episode launched.
    _require_formal_go(adapter, human_go)
    # ``strict_design=False`` relaxes the frozen-design comparison; it is only
    # ever legitimate for an explicit test double (the scaled FakeAdapter
    # integration tests). A non-test adapter must never be driven with the
    # design guard relaxed, so refuse it here.
    if not strict_design and not getattr(adapter, "is_test_double", False):
        raise PermissionError(
            "strict_design=False is reserved for explicit test doubles "
            "(is_test_double=True); refusing to run a non-test formal execution "
            "with relaxed design validation.")
    cfg = load_json_config(config_path)
    # Config drift guard: seed count/uniqueness always; frozen values, order and
    # protocol fingerprint when running the real (non-scaled) design.
    validation = validate_formal_config(
        cfg, strict_design=strict_design,
        expected_master_seed_count=FORMAL_MASTER_SEED_COUNT)
    seeds = list(validation["seeds"])
    root = Path(project_root)
    runs_root = root / RUNS_DIRNAME
    runs_root.mkdir(parents=True, exist_ok=True)
    ledger_path = runs_root / "episode_ledger.csv"

    per_seed_method: list[dict[str, Any]] = []
    for seed in seeds:
        for method in METHODS:
            # Cumulative budget for THIS (method, master_seed) scope, read from
            # the durable ledger before the run.
            scope_before = EpisodeLedger(ledger_path).launched_count_scope(
                f"formal|{method}|{seed}")
            driver = PhaseDriver(phase="formal", method=method, master_seed=seed,
                                max_episodes=FORMAL_BUDGET, project_root=root,
                                adapter=adapter)
            scope = driver._budget_scope
            report = _run_formal_method(driver, method, human_go=human_go)
            scope_after = EpisodeLedger(ledger_path).launched_count_scope(scope)
            new_this_call = scope_after - scope_before
            # Verify the CUMULATIVE budget, not the increment: on a legal resume
            # (part or all of this slice already complete) the increment is < 800
            # but the cumulative total must still be exactly 800. Verifying the
            # increment would false-alarm; verifying only the increment would also
            # miss an over-spend, so we assert the cumulative total here.
            if scope_after != FORMAL_BUDGET:
                raise RuntimeError(
                    f"formal {method} seed {seed}: cumulative scope budget "
                    f"{scope_after} != {FORMAL_BUDGET} (new this call: {new_this_call})")
            if new_this_call < 0 or scope_before + new_this_call != scope_after:
                raise RuntimeError(
                    f"formal {method} seed {seed}: inconsistent billing "
                    f"{scope_before} + {new_this_call} != {scope_after}")
            # Per-(seed, method) manifest -- unique path, never overwritten.
            manifest_path = driver.write_formal_manifest(master_seed=seed)
            per_seed_method.append({
                "master_seed": seed, "method": method,
                "cumulative_episodes": scope_after,
                "new_episodes_this_call": new_this_call,
                "n_quartets": len(report.quartets),
                "nominations": {k: len(v) for k, v in report.nominations.items()},
                "manifest": str(manifest_path),
            })

    ledger = EpisodeLedger(ledger_path)
    combined = {
        "protocol": "SafeFlipLab-v01",
        "phase": "formal",
        "status": "scheduled-complete",
        "master_seed_count": len(seeds),
        "methods": list(METHODS),
        "episodes_per_method_seed": FORMAL_BUDGET,
        "planned_total_episodes": FORMAL_TOTAL_EPISODES,
        "episodes_launched": ledger.launched_count("formal"),
        "episodes_completed": ledger.outcome_count("formal", "completed"),
        "episodes_errored": ledger.outcome_count("formal", "error"),
        "per_seed_method": per_seed_method,
        "protocol_fingerprint": frozen_protocol_fingerprint(),
        "config_fingerprint": validation["fingerprint"],
        "config_strict_design": bool(strict_design),
        "code_fingerprint": code_fingerprint(),
        "adapter_fingerprint": fingerprint().to_dict(),
    }
    if combined["episodes_launched"] != FORMAL_TOTAL_EPISODES:
        raise RuntimeError(
            f"formal launched {combined['episodes_launched']} episodes, expected "
            f"exactly {FORMAL_TOTAL_EPISODES}")
    (runs_root / "manifest_formal_combined.json").write_text(
        json.dumps(combined, indent=2, sort_keys=True), encoding="utf-8")
    return combined
