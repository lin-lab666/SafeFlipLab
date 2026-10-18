"""V02 phase drivers: smoke (<=24) and pilot (<=240).

Budgets are hard, independent and non-transferable:

* ``v02-smoke`` scope: cap 24
* ``v02-pilot`` scope: cap 240

The ledger is the authority for billing; a phase refuses to start if the frozen
protocol has not been loaded and validated, and every launched attempt is billed
before the simulator runs.
"""
from __future__ import annotations

import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .anchors import anchor_id, anchor_stream
from .conditions import canonical_json
from .ledger21 import EpisodeLedger21
from .methods import (METHOD_VERIFY, METHOD_WIDE, nomination_key, select_top,
                      verify_key, wide_key)
from .quartet import Repetition, build_repetition, repetition_seed_payload
from .runner import V02Runner, billed_tuple_keys, episode_tuple_key, run_quartet
from .ttc_state import EpisodeTTC, EpisodeTTCCategory, PairStatus, quartet_pair_status

PROTOCOL_ID = "SafeFlipLab-v02"
DIMS = ("ego_speed", "front_gap", "front_speed", "ramp_x", "ramp_speed",
        "ramp_target_speed")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def make_run_id(phase: str, method: str, master_seed: int) -> str:
    stamp = utc_now_iso().replace("-", "").replace(":", "").replace(".", "")
    short = hashlib.sha256(
        canonical_json([PROTOCOL_ID, phase, method, master_seed, stamp]).encode()
    ).hexdigest()[:8]
    return f"v02_{phase}_{method}_{master_seed}_{stamp}_{short}"


class FrozenProtocol:
    """Validated view over ``configs/v02_frozen_v1.json`` (FROZEN parameters only)."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.raw = config
        if config.get("status") != "FROZEN":
            raise RuntimeError("V02 protocol config is not FROZEN; refusing to run episodes")
        self.params = config["parameters"]
        for name, node in self.params.items():
            if node.get("status") != "FROZEN":
                raise RuntimeError(
                    f"V02 parameter {name!r} is {node.get('status')!r}, not FROZEN")

    def value(self, name: str) -> Any:
        return self.params[name]["value"]

    @property
    def domain(self) -> dict[str, list[float]]:
        return self.value("anchor_domain")

    @property
    def bounds(self) -> dict[str, tuple[float, float]]:
        return {k: (float(v[0]), float(v[1])) for k, v in self.value("upstream_bounds").items()}

    @property
    def halfwidths(self) -> dict[str, float]:
        return {
            "front_gap": float(self.value("perturbation_front_gap_halfwidth_m")),
            "front_speed": float(self.value("perturbation_front_speed_halfwidth_mps")),
            "ego_speed": float(self.value("perturbation_ego_speed_halfwidth_mps")),
        }

    @property
    def perturbation_spec(self) -> dict[str, dict[str, float]]:
        return {d: {"halfwidth": hw} for d, hw in self.halfwidths.items()}

    @property
    def gap_m(self) -> float:
        return float(self.value("gap_intervention_m"))

    @property
    def speed_mps(self) -> float:
        return float(self.value("speed_intervention_mps"))

    @property
    def master_seed(self) -> int:
        return int(self.value("v02_master_seed"))

    @property
    def protocol_hash(self) -> str:
        return hashlib.sha256(canonical_json(self.raw).encode()).hexdigest()


def load_frozen_protocol(path: str | Path) -> FrozenProtocol:
    with open(path, "r", encoding="utf-8") as fh:
        return FrozenProtocol(json.load(fh))


class PhaseOutcome:
    """Result of one phase run, with everything needed for reporting/audit."""

    def __init__(self, phase: str, budget_scope: str, cap: int) -> None:
        self.phase = phase
        self.budget_scope = budget_scope
        self.cap = cap
        self.runs: list[dict[str, Any]] = []
        self.started = utc_now_iso()
        self.wall_time_s = 0.0
        self.launched = 0
        self.completed = 0
        self.errored = 0
        self.upstream_mismatch = 0


def _build_anchors(proto: FrozenProtocol, n: int) -> list[dict[str, float]]:
    return anchor_stream(proto.master_seed, proto.domain, bounds=proto.bounds, n=n,
                         gap_m=proto.gap_m, speed_mps=proto.speed_mps,
                         perturbation_halfwidths=proto.halfwidths)


def _summarise(ledger: EpisodeLedger21, phase: str, scope: str, cap: int,
               wall: float) -> dict[str, Any]:
    return {
        "phase": phase,
        "budget_scope": scope,
        "cap": cap,
        "launched": ledger.launched_count_scope(scope),
        "completed": ledger.outcome_count("completed"),
        "errored": ledger.outcome_count("error"),
        "interrupted": ledger.outcome_count("interrupted"),
        "wall_time_s": round(wall, 2),
        "diagnose": ledger.diagnose(),
    }


# --------------------------------------------------------------------------
# smoke
# --------------------------------------------------------------------------
def run_smoke(root: str | Path, proto: FrozenProtocol, *, adapter: Any,
              cap: int = 24) -> dict[str, Any]:
    plan = proto.value("smoke_plan")
    n_anchors, reps = int(plan["anchors"]), int(plan["repetitions"])
    planned = n_anchors * reps * 4
    if planned > cap:
        raise RuntimeError(f"smoke plan needs {planned} episodes but cap is {cap}")
    scope = "v02-smoke"
    runs_root = Path(root) / "runs" / "smoke"
    runs_root.mkdir(parents=True, exist_ok=True)
    ledger = EpisodeLedger21(runs_root / "episode_ledger.csv", phase="smoke")
    if ledger.launched_count_scope(scope) >= cap:
        raise RuntimeError(f"V02 smoke budget already exhausted ({cap}); not re-running")
    runner = V02Runner(adapter, ledger, runs_root, tau_cap_s=float(proto.value("tau_cap_s")),
                       no_candidate_policy=str(proto.value("no_candidate_policy")),
                       max_episodes=cap, budget_scope=scope, phase="smoke", echo=True)
    anchors = _build_anchors(proto, n_anchors)
    started = time.perf_counter()
    billed = billed_tuple_keys(ledger)
    records: list[dict[str, Any]] = []
    for ai, anchor in enumerate(anchors):
        aid = anchor_id(ai)
        for rep_idx in range(reps):
            rep = build_repetition(master_seed=proto.master_seed, stream="discovery",
                                   anchor_index=ai, anchor_id=aid, repetition=rep_idx,
                                   anchor_values=anchor,
                                   perturbation_spec=proto.perturbation_spec,
                                   gap_m=proto.gap_m, speed_mps=proto.speed_mps,
                                   method="Shared")
            run_id = make_run_id("smoke", "Shared", proto.master_seed)
            quartet = run_quartet(runner, run_id=run_id, method="Shared",
                                  master_seed=proto.master_seed, rep=rep,
                                  already_billed=billed)
            records.append(_quartet_record(rep, quartet))
    wall = time.perf_counter() - started
    summary = _summarise(ledger, "smoke", scope, cap, wall)
    summary.update({"planned_episodes": planned, "anchors": n_anchors, "repetitions": reps,
                    "upstream_ttc_mismatches": runner.n_upstream_mismatch,
                    "max_upstream_ttc_delta_s": runner.max_upstream_delta_s,
                    "protocol_hash": proto.protocol_hash,
                    "quartets": records})
    _write_manifest(runs_root / "manifest_smoke.json", summary)
    return summary


def _write_manifest(path: Path, payload: dict[str, Any]) -> None:
    """Write the phase manifest, never clobbering a richer one with an empty resume.

    A re-invocation that finds every episode already billed would otherwise
    overwrite a complete manifest with an empty record list.
    """
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as fh:
                old = json.load(fh)
        except (OSError, ValueError):
            old = {}
        new_records = payload.get("primary_quartets", payload.get("quartets", []))
        old_records = old.get("primary_quartets", old.get("quartets", []))
        if old_records and not new_records:
            return  # keep the complete historical manifest
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
                    encoding="utf-8")


# --------------------------------------------------------------------------
# pilot
# --------------------------------------------------------------------------
def run_pilot(root: str | Path, proto: FrozenProtocol, *, adapter: Any,
              cap: int = 240) -> dict[str, Any]:
    plan = proto.value("pilot_plan")
    n_anchors, reps = int(plan["anchors"]), int(plan["repetitions"])
    n_methods = len(plan["methods"])
    k = int(plan["nominees_per_method"])
    audit_q = int(plan["audit_quartets_per_nominee"])
    primary = n_anchors * reps * 4
    aux = n_methods * k * audit_q * 4
    planned = primary + aux
    if planned > cap:
        raise RuntimeError(f"pilot plan needs {planned} episodes but cap is {cap}")
    scope = "v02-pilot"
    runs_root = Path(root) / "runs" / "pilot"
    runs_root.mkdir(parents=True, exist_ok=True)
    ledger = EpisodeLedger21(runs_root / "episode_ledger.csv", phase="pilot")
    already = ledger.launched_count_scope(scope)
    if already >= cap:
        raise RuntimeError(f"V02 pilot budget already exhausted ({cap}); not re-running")
    runner = V02Runner(adapter, ledger, runs_root, tau_cap_s=float(proto.value("tau_cap_s")),
                       no_candidate_policy=str(proto.value("no_candidate_policy")),
                       max_episodes=cap, budget_scope=scope, phase="pilot", echo=False)
    anchors = _build_anchors(proto, n_anchors)
    started = time.perf_counter()
    billed = billed_tuple_keys(ledger)

    # ---- 1. primary reversal/interaction study (18 x 3 x 4 = 216) ---------
    primary_records: list[dict[str, Any]] = []
    per_anchor_quartets: dict[int, list[dict[str, Any]]] = {}
    for ai, anchor in enumerate(anchors):
        aid = anchor_id(ai)
        reps_out = []
        for rep_idx in range(reps):
            rep = build_repetition(master_seed=proto.master_seed, stream="discovery",
                                   anchor_index=ai, anchor_id=aid, repetition=rep_idx,
                                   anchor_values=anchor,
                                   perturbation_spec=proto.perturbation_spec,
                                   gap_m=proto.gap_m, speed_mps=proto.speed_mps,
                                   method="Shared")
            run_id = make_run_id("pilot", "Shared", proto.master_seed)
            quartet = run_quartet(runner, run_id=run_id, method="Shared",
                                  master_seed=proto.master_seed, rep=rep,
                                  already_billed=billed)
            rec = _quartet_record(rep, quartet)
            primary_records.append(rec)
            reps_out.append(rec)
        per_anchor_quartets[ai] = reps_out
        print(f"[pilot] primary anchor {ai + 1}/{n_anchors} done "
              f"(launched={ledger.launched_count_scope(scope)})", flush=True)

    # ---- 2. auxiliary method comparison on an independent audit -----------
    aux_records = _run_auxiliary_method_comparison(
        proto, runner, ledger, anchors, per_anchor_quartets, scope, k, audit_q,
        already_billed=billed)

    wall = time.perf_counter() - started
    summary = _summarise(ledger, "pilot", scope, cap, wall)
    summary.update({
        "planned_episodes": planned, "primary_episodes": primary, "aux_episodes": aux,
        "anchors": n_anchors, "repetitions": reps,
        "upstream_ttc_mismatches": runner.n_upstream_mismatch,
        "max_upstream_ttc_delta_s": runner.max_upstream_delta_s,
        "protocol_hash": proto.protocol_hash,
        "primary_quartets": primary_records,
        "aux": aux_records,
    })
    _write_manifest(runs_root / "manifest_pilot.json", summary)
    return summary


def _quartet_record(rep: Repetition, quartet: Mapping[str, Any]) -> dict[str, Any]:
    episodes: dict[str, EpisodeTTC] = {c: quartet[c].episode for c in quartet}
    status = quartet_pair_status(episodes)
    out: dict[str, Any] = {
        "anchor_id": rep.anchor_id, "anchor_index": rep.anchor_index,
        "repetition": rep.repetition, "stream": rep.stream, "sim_seed": rep.sim_seed,
        "perturbation": rep.perturbation, "base_scenario": rep.base,
        "pair_status": status.value,
    }
    for c, run in quartet.items():
        out[c] = {
            "value": run.episode.value,
            "category": run.episode.category.value,
            "censored": run.episode.censored,
            "ego_collision": run.ego_collision,
            "exit_status": run.exit_status,
            "termination": run.termination,
            "raw_path": run.raw_path,
            "n_steps": run.episode.n_steps_observed,
            "n_normal": run.episode.n_normal,
            "n_no_closing": run.episode.n_no_closing,
            "n_no_candidate": run.episode.n_no_candidate,
            "conditioned_scenario": rep.scenarios[c],
        }
    usable = status is PairStatus.OK
    out["usable"] = usable
    if usable:
        v = {c: float(out[c]["value"]) for c in ("00", "10", "01", "11")}
        out["delta_gap"] = v["10"] - v["00"]
        out["delta_speed"] = v["01"] - v["00"]
        out["delta_both"] = v["11"] - v["00"]
        out["i_lin"] = v["11"] - v["10"] - v["01"] + v["00"]
    return out


def _run_auxiliary_method_comparison(proto: FrozenProtocol, runner: V02Runner,
                                     ledger: EpisodeLedger21,
                                     anchors: list[dict[str, float]],
                                     per_anchor_quartets: dict[int, list[dict[str, Any]]],
                                     scope: str, k: int, audit_quartets: int,
                                     *, already_billed: set[tuple] | None = None
                                     ) -> dict[str, Any]:
    """Two methods nominate from the SAME discovery quartets but under different
    allocation rules; the winner is judged only on a fresh, independent audit."""
    # discovery view: WideExplore sees only repetition 0 (breadth: one quartet
    # per anchor); VerifyFirst sees every repetition the protocol collected
    # (depth: it re-verified its anchors).
    wide_pool = {ai: [per_anchor_quartets[ai][0]] for ai in per_anchor_quartets}
    verify_pool = {ai: list(per_anchor_quartets[ai]) for ai in per_anchor_quartets}

    out: dict[str, Any] = {"nomination": {}, "audit": {}, "delta_eq_s": proto.value("delta_eq_s")}
    nominees: dict[str, list[int]] = {}
    for method, pool in ((METHOD_WIDE, wide_pool), (METHOD_VERIFY, verify_pool)):
        key_fn = wide_key if method == METHOD_WIDE else verify_key
        ranked = select_top(pool, key_fn, k)
        nominees[method] = ranked
        out["nomination"][method] = [anchor_id(ai) for ai in ranked]

    for method, ranked in nominees.items():
        entries = []
        for ai in ranked:
            aid = anchor_id(ai)
            for j in range(audit_quartets):
                rep = build_repetition(master_seed=proto.master_seed, stream="audit",
                                       anchor_index=ai, anchor_id=aid, repetition=j,
                                       anchor_values=anchors[ai],
                                       perturbation_spec=proto.perturbation_spec,
                                       gap_m=proto.gap_m, speed_mps=proto.speed_mps,
                                       method=method)
                run_id = make_run_id("pilot", method, proto.master_seed)
                quartet = run_quartet(runner, run_id=run_id, method=method,
                                      master_seed=proto.master_seed, rep=rep,
                                      already_billed=already_billed)
                rec = _quartet_record(rep, quartet)
                entries.append(rec)
        out["audit"][method] = entries
        print(f"[pilot] aux audit {method}: {len(entries)} quartets "
              f"(launched={ledger.launched_count_scope(scope)})", flush=True)
    return out
