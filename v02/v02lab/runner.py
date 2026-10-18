"""V02 episode runner: reserve-before-launch billing, real execution, raw archive.

Ordering is the protocol's core safety property and is enforced here:

1. the attempt is **persisted and billed** in the 21-column V02 ledger *before*
   the simulator is touched;
2. only then is the episode run;
3. the outcome row is appended and the raw record archived.

A failure or interruption is therefore always billed and never silently retried.
``record_outcome`` requires a 0/1 ``ego_collision`` for a completed episode, so a
missing observation can never be recorded as "safe".
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .conditions import CONDITIONS
from .ledger21 import EpisodeKey21, EpisodeLedger21
from .ttc_state import (EpisodeTTC, TerminationClass, aggregate_episode,
                        termination_from_exit)

from .adapter_real import states_from_raw_steps

#: Equivalence tolerance between the trajectory-derived per-policy-step TTC
#: minimum and the simulator's own ``min_forward_ttc_sampled_s``. Justified in
#: ``docs/AUTONOMOUS_DECISIONS.md`` D38; four orders of magnitude below the
#: smallest effect the protocol reasons about (``delta_eq = 0.05 s``).
TTC_EQUIVALENCE_TOL_S = 1e-4


@dataclass(frozen=True)
class EpisodeRun:
    condition: str
    repetition: int
    anchor_index: int
    anchor_id: str
    sim_seed: int
    exit_status: str
    episode: EpisodeTTC
    ego_collision: int | None
    termination: str
    wall_time_s: float | None
    raw_path: str
    used_cap: bool


def _termination_class(exit_status: str, termination: str) -> TerminationClass:
    return termination_from_exit(exit_status, termination)


class V02Runner:
    def __init__(self, adapter: Any, ledger: EpisodeLedger21, raw_root: str | Path,
                 *, tau_cap_s: float, no_candidate_policy: str, max_episodes: int,
                 budget_scope: str, phase: str, echo: bool = False) -> None:
        if tau_cap_s is None:
            raise ValueError("tau_cap_s must be supplied explicitly (no default)")
        self.adapter = adapter
        self.ledger = ledger
        self.raw_root = Path(raw_root)
        self.tau_cap_s = float(tau_cap_s)
        self.no_candidate_policy = no_candidate_policy
        self.max_episodes = int(max_episodes)
        self.budget_scope = budget_scope
        self.phase = phase
        self.echo = echo
        self.n_upstream_mismatch = 0
        self.max_upstream_delta_s = 0.0

    # -- raw archive ------------------------------------------------------
    def _archive(self, *, run_id: str, payload: dict[str, Any]) -> str:
        out_dir = self.raw_root / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{payload['anchor_id']}_rep{payload['repetition']}_{payload['condition']}.json"
        if path.exists():
            # append-only history: never overwrite an archived real record
            raise FileExistsError(f"refusing to overwrite raw episode record {path}")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1, sort_keys=True)
        return str(path)

    # -- one episode ------------------------------------------------------
    def run_episode(self, *, run_id: str, method: str, master_seed: int,
                    anchor_index: int, anchor_id: str, repetition: int,
                    condition: str, sim_seed: int, stream: str,
                    scenario: dict[str, float], perturbation: dict[str, float],
                    base_scenario: dict[str, float]) -> EpisodeRun:
        if condition not in CONDITIONS:
            raise ValueError(f"unknown condition {condition!r}")
        key = EpisodeKey21(run_id=run_id, anchor_id=anchor_id,
                           repetition=repetition, condition=condition)
        # (1) bill BEFORE touching the simulator
        launch_row = self.ledger.reserve_launch(
            key, method=method, master_seed=master_seed, anchor_id=anchor_id,
            anchor_index=anchor_index, repetition=repetition, condition=condition,
            sim_seed=int(sim_seed), stream=stream, max_episodes=self.max_episodes,
            budget_scope=self.budget_scope, run_id=run_id)

        started = time.perf_counter()
        exit_status = "completed"
        error_type = ""
        termination = ""
        ego_collision: int | None = None
        wall: float | None = None
        raw_path = ""
        raw_steps: list[tuple[Any, ...]] = []
        episode: EpisodeTTC | None = None

        # Every step after the billing is inside the guard: a failure at *any*
        # point (simulator, archive, metric post-processing) must still produce a
        # billed outcome row. An orphan launch row would silently hide a spent
        # episode, which the protocol forbids.
        try:
            result = self.adapter.run_episode(scenario, int(sim_seed))
            termination = str(result.get("termination", ""))
            exit_status = str(result.get("exit_status", "completed"))
            coll = result.get("ego_collision")
            ego_collision = None if coll is None else int(coll)
            if exit_status == "completed" and ego_collision is None:
                raise ValueError("a completed episode must report ego_collision")
            raw_steps = [tuple(s) for s in result.get("steps", [])]
            wall = float(result.get("wall_time_s", time.perf_counter() - started))
            payload = {
                "protocol": "SafeFlipLab-v02",
                "phase": self.phase,
                "method": method,
                "master_seed": master_seed,
                "anchor_id": anchor_id,
                "anchor_index": anchor_index,
                "repetition": repetition,
                "condition": condition,
                "stream": stream,
                "sim_seed": int(sim_seed),
                "run_id": run_id,
                "base_scenario": base_scenario,
                "perturbation": perturbation,
                "conditioned_scenario": scenario,
                "exit_status": exit_status,
                "termination": termination,
                "ego_collision": ego_collision,
                "wall_time_s": wall,
                "adapter_fingerprint": {
                    "cornercaselab_version": "0.3.0",
                    "controller_policy": "boundary",
                    "horizon_s": 25.0, "simulation_hz": 15, "policy_hz": 5,
                },
                "result": {k: v for k, v in result.items() if k != "steps"},
                "raw_steps": [list(s) for s in raw_steps],
            }
            upstream = result.get("min_forward_ttc_upstream_s")
            if upstream is not None:
                finite = [v for _, v in states_from_raw_steps(raw_steps) if v is not None]
                derived = min(finite) if finite else None
                if derived is None:
                    self.n_upstream_mismatch += 1
                    payload["upstream_ttc_mismatch"] = {"derived": None,
                                                        "upstream": upstream}
                else:
                    delta = abs(float(derived) - float(upstream))
                    self.max_upstream_delta_s = max(self.max_upstream_delta_s, delta)
                    # TTC_EQUIVALENCE_TOL_S: the derived per-step minimum is
                    # reconstructed from the returned trajectory, which the
                    # upstream simulator rounds to 9 decimals, and vx is rebuilt
                    # as speed*cos(heading). Both introduce only ~1e-6 s of
                    # numerical noise, four orders of magnitude below the
                    # smallest effect the protocol reasons about (delta_eq =
                    # 0.05 s), so equivalence is asserted at 1e-4 s.
                    if delta > TTC_EQUIVALENCE_TOL_S:
                        self.n_upstream_mismatch += 1
                        payload["upstream_ttc_mismatch"] = {
                            "derived": derived, "upstream": upstream, "delta": delta}
            raw_path = self._archive(run_id=run_id, payload=payload)
            episode = aggregate_episode(
                states_from_raw_steps(raw_steps),
                termination=_termination_class(exit_status, termination),
                tau_cap=self.tau_cap_s, no_candidate_policy=self.no_candidate_policy)
        except Exception as exc:  # billed, never retried automatically
            exit_status = "error"
            error_type = type(exc).__name__
            wall = time.perf_counter() - started
            termination = ""
            episode = aggregate_episode(
                [], termination=TerminationClass.TECHNICAL_FAILURE,
                tau_cap=self.tau_cap_s, no_candidate_policy=self.no_candidate_policy)

        assert episode is not None

        self.ledger.record_outcome(
            key, launch_row=launch_row, exit_status=exit_status,
            ego_collision=ego_collision if exit_status == "completed" else None,
            termination=termination, error_type=error_type,
            wall_time_s=wall, raw_path=raw_path)

        if self.echo:
            print(f"  [{self.phase}] {method} {anchor_id} r{repetition} {condition} "
                  f"-> {exit_status} coll={ego_collision} ttc={episode.value} "
                  f"({episode.category.value})", flush=True)

        from .ttc_state import EpisodeTTCCategory
        return EpisodeRun(
            condition=condition, repetition=repetition, anchor_index=anchor_index,
            anchor_id=anchor_id, sim_seed=int(sim_seed), exit_status=exit_status,
            episode=episode, ego_collision=ego_collision, termination=termination,
            wall_time_s=wall, raw_path=raw_path,
            used_cap=episode.category in (EpisodeTTCCategory.CENSORED,
                                          EpisodeTTCCategory.NO_CANDIDATE))


def episode_tuple_key(*, method: str, anchor_index: int, repetition: int,
                      condition: str, stream: str) -> tuple:
    """Run-id-independent identity of one billable episode.

    Resume is keyed on this tuple (not on the timestamped ``run_id``) so that a
    re-invocation of a phase can never re-run — and therefore never re-bill — an
    attempt that was already launched, whether it succeeded or failed.
    """
    return (method, int(anchor_index), int(repetition), condition, stream)


def billed_tuple_keys(ledger: EpisodeLedger21) -> set[tuple]:
    """Tuple keys already billed in this ledger (authoritative: the CSV)."""
    import csv as _csv
    path = ledger.path
    if not path.exists():
        return set()
    out: set[tuple] = set()
    with open(path, newline="", encoding="utf-8") as fh:
        for row in _csv.DictReader(fh):
            if row.get("row_type") != "launch":
                continue
            try:
                out.add(episode_tuple_key(
                    method=row["method"], anchor_index=int(row["anchor_index"]),
                    repetition=int(row["repetition"]), condition=row["condition"],
                    stream=row["stream"]))
            except (KeyError, TypeError, ValueError):
                continue
    return out


def run_quartet(runner: V02Runner, *, run_id: str, method: str, master_seed: int,
                rep, already_billed: set[tuple] | None = None) -> dict[str, EpisodeRun]:
    """Run the four conditions of one repetition (paired, shared seed).

    Conditions already billed in the ledger are skipped: history is never re-run.
    """
    billed = already_billed if already_billed is not None else set()
    out: dict[str, EpisodeRun] = {}
    for condition in CONDITIONS:
        tkey = episode_tuple_key(method=method, anchor_index=rep.anchor_index,
                                 repetition=rep.repetition, condition=condition,
                                 stream=rep.stream)
        if tkey in billed:
            continue
        run = runner.run_episode(
            run_id=run_id, method=method, master_seed=master_seed,
            anchor_index=rep.anchor_index, anchor_id=rep.anchor_id,
            repetition=rep.repetition, condition=condition, sim_seed=rep.sim_seed,
            stream=rep.stream, scenario=rep.scenarios[condition],
            perturbation=rep.perturbation, base_scenario=rep.base)
        billed.add(tkey)
        out[condition] = run
    return out
