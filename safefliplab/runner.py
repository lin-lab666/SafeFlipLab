"""SimulatorRunner: executes real quartets under strict budget accounting.

One quartet = four *separate real* HighwayEnv episodes (conditions 00/10/01/11),
all sharing one paired ``sim_seed``. Every episode is:

1. checked against the phase budget,
2. recorded as ``launch`` in the EpisodeLedger **before** it starts,
3. executed for real (no mocks anywhere in this path),
4. persisted as a raw JSON record,
5. closed with an ``outcome`` row (completed / error / interrupted).

A launch without an outcome (hard kill) still consumes budget; its Y value
remains missing and is never assumed to be 0 or 1.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cornercaselab.domain import Scenario

from .adapter import ScenarioAdapter, fingerprint
from .domain import Anchor, condition_scenario, quartet_scenarios
from .ledger import BudgetExhausted, EpisodeKey, EpisodeLedger
from .seeds import CONDITIONS, STREAM_AUDIT, STREAM_DISCOVERY, sim_seed_for


@dataclass(frozen=True)
class EpisodeOutcome:
    episode_key: str
    condition: str
    sim_seed: int
    exit_status: str
    ego_collision: int | None
    termination: str
    wall_time_s: float
    raw_path: str
    error_type: str = ""


@dataclass(frozen=True)
class QuartetResult:
    anchor_id: str
    anchor_index: int
    repetition: int
    sim_seed: int
    method: str
    stream: str
    outcomes: dict[str, EpisodeOutcome]

    @property
    def complete(self) -> bool:
        return all(
            self.outcomes[c].exit_status == "completed" and self.outcomes[c].ego_collision is not None
            for c in CONDITIONS
        )

    @property
    def y(self) -> dict[str, int] | None:
        """Y00/Y10/Y01/Y11 as ints, or None when the quartet is incomplete."""
        if not self.complete:
            return None
        return {c: int(self.outcomes[c].ego_collision) for c in CONDITIONS}  # type: ignore[arg-type]


class SimulatorRunner:
    def __init__(self, adapter: ScenarioAdapter, ledger: EpisodeLedger, raw_root: str | Path) -> None:
        self.adapter = adapter
        self.ledger = ledger
        self.raw_root = Path(raw_root)

    # -- single episode ---------------------------------------------------
    def _run_one(self, *, run_id: str, phase: str, method: str, master_seed: int,
                 anchor: Anchor, condition: str, sim_seed: int, repetition: int,
                 stream: str, max_episodes: int, raw_dir: Path,
                 budget_scope: str | None = None) -> EpisodeOutcome:
        key = EpisodeKey(run_id=run_id, anchor_id=anchor.anchor_id,
                         repetition=repetition, condition=condition)
        # Atomic reserve: budget check + duplicate guard + launch billing happen
        # under one lock, so a second concurrent/duplicate trigger cannot slip
        # past the cap or bill the same episode twice.
        launch_row = self.ledger.reserve_launch(
            key,
            run_id=run_id,
            phase=phase,
            method=method,
            master_seed=master_seed,
            anchor_id=anchor.anchor_id,
            anchor_index=anchor.index,
            repetition=repetition,
            condition=condition,
            sim_seed=sim_seed,
            stream=stream,
            max_episodes=max_episodes,
            budget_scope=budget_scope,
        )
        scenario: Scenario = quartet_scenarios(anchor.scenario)[condition]
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / f"{anchor.anchor_id}_rep{repetition}_{condition}.json"
        started = time.perf_counter()
        try:
            result = self.adapter.run_episode(scenario, sim_seed)
        except KeyboardInterrupt:
            self.ledger.record_outcome(key, launch_row=launch_row,
                                       exit_status="interrupted", ego_collision=None,
                                       error_type="KeyboardInterrupt",
                                       wall_time_s=time.perf_counter() - started)
            raise
        except Exception as exc:  # billed, then surfaced: no free retry
            wall = time.perf_counter() - started
            self.ledger.record_outcome(key, launch_row=launch_row, exit_status="error",
                                       ego_collision=None, error_type=type(exc).__name__,
                                       wall_time_s=wall, raw_path=str(raw_path))
            self._write_raw(raw_path, run_id=run_id, phase=phase, method=method,
                            master_seed=master_seed, anchor=anchor, condition=condition,
                            sim_seed=sim_seed, repetition=repetition,
                            status="error", error=f"{type(exc).__name__}: {exc}", result=None,
                            wall_time_s=wall)
            raise
        wall = time.perf_counter() - started
        record = self._write_raw(raw_path, run_id=run_id, phase=phase, method=method,
                                 master_seed=master_seed, anchor=anchor, condition=condition,
                                 sim_seed=sim_seed, repetition=repetition,
                                 status="completed", error="", result=result,
                                 wall_time_s=wall)
        collision = 1 if result["ego_collision"] else 0
        self.ledger.record_outcome(key, launch_row=launch_row, exit_status="completed",
                                   ego_collision=collision,
                                   termination=result["termination"], wall_time_s=wall,
                                   raw_path=str(raw_path))
        return EpisodeOutcome(episode_key=str(key), condition=condition, sim_seed=sim_seed,
                              exit_status="completed", ego_collision=collision,
                              termination=result["termination"], wall_time_s=wall,
                              raw_path=str(raw_path))

    def _write_raw(self, path: Path, *, run_id: str, phase: str, method: str, master_seed: int,
                   anchor: Anchor, condition: str, sim_seed: int, repetition: int,
                   status: str, error: str, result: dict[str, Any] | None,
                   wall_time_s: float) -> dict[str, Any]:
        record = {
            "protocol": "SafeFlipLab-v01",
            "run_id": run_id,
            "phase": phase,
            "method": method,
            "master_seed": master_seed,
            "anchor": anchor.to_dict(),
            "condition": condition,
            "repetition": repetition,
            "sim_seed": sim_seed,
            "conditioned_scenario": condition_scenario(anchor.scenario, condition).to_dict(),
            "adapter_fingerprint": fingerprint().to_dict(),
            "status": status,
            "error": error,
            "wall_time_s": round(wall_time_s, 6),
            "result": result,
        }
        path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        return record

    # -- quartet ----------------------------------------------------------
    def run_quartet(self, *, run_id: str, phase: str, method: str, master_seed: int,
                    anchor: Anchor, repetition: int, stream: str, max_episodes: int,
                    raw_dir: Path | None = None, budget_scope: str | None = None) -> QuartetResult:
        """Run the four-condition quartet of one anchor-repetition.

        Fails fast on the first episode error (the failed attempt stays
        billed); the caller decides whether to spend remaining budget.
        """
        if stream not in (STREAM_DISCOVERY, STREAM_AUDIT):
            raise ValueError(f"stream must be discovery/audit, got {stream!r}")
        sim_seed = sim_seed_for(master_seed, method, stream, anchor.anchor_id, repetition)
        raw_dir = raw_dir or (self.raw_root / run_id)
        outcomes: dict[str, EpisodeOutcome] = {}
        for condition in CONDITIONS:
            outcomes[condition] = self._run_one(
                run_id=run_id, phase=phase, method=method, master_seed=master_seed,
                anchor=anchor, condition=condition, sim_seed=sim_seed,
                repetition=repetition, stream=stream, max_episodes=max_episodes,
                raw_dir=raw_dir, budget_scope=budget_scope,
            )
        return QuartetResult(anchor_id=anchor.anchor_id, anchor_index=anchor.index,
                             repetition=repetition, sim_seed=sim_seed, method=method,
                             stream=stream, outcomes=outcomes)

    # -- replay check -----------------------------------------------------
    def replay_quartet(self, *, run_id: str, phase: str, method: str, master_seed: int,
                       anchor: Anchor, repetition: int, stream: str, max_episodes: int,
                       raw_dir: Path | None = None, budget_scope: str | None = None) -> QuartetResult:
        """Re-run a quartet with identical seeds (costs a full 4 episodes).

        Used only inside the smoke budget to verify that identical
        (scenario, sim_seed) inputs reproduce identical traces.
        """
        return self.run_quartet(run_id=run_id, phase=phase, method=method,
                                master_seed=master_seed, anchor=anchor,
                                repetition=repetition, stream=stream,
                                max_episodes=max_episodes, raw_dir=raw_dir,
                                budget_scope=budget_scope)
