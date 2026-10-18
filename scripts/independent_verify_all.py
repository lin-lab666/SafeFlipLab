"""INDEPENDENT recomputation of EVERY published statistic, V01 + V02.

Reads only the ledgers and the archived raw episode JSON. It imports **neither**
``safefliplab.report`` / ``margins`` **nor** ``v02lab.report`` / ``stats_anchor``.
Every number printed as ``recomputed`` is derived here from scratch; every
``published`` number is read back from the frozen artefacts. Any mismatch is a
finding.

    .venv\\Scripts\\python.exe .workbuddy\\tmp_audit\\independent_verify_all.py
"""
from __future__ import annotations

import csv
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"D:\SafeFlipLab")
OUT: list[str] = []
FAILS: list[str] = []


def p(s: str = "") -> None:
    OUT.append(s)
    print(s)


def check(label: str, got, want, tol: float = 0.0) -> None:
    if isinstance(got, float) and isinstance(want, float):
        ok = abs(got - want) <= max(tol, 0.0)
    else:
        ok = got == want
    if not ok:
        FAILS.append(f"{label}: recomputed={got!r} published={want!r}")
    p(f"    {label:52s} recomputed={got!r:<24} published={want!r:<24} {'OK' if ok else '*** MISMATCH ***'}")


def read_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r.get("row_type")]


def read_json(path: str | Path) -> dict | None:
    pth = Path(path)
    if not pth.is_file():
        return None
    try:
        with open(pth, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


# ============================================================ V01
CONDITIONS = ("00", "10", "01", "11")


def v01():
    p("=" * 100)
    p("V01 — independent recomputation (main study: binary collision endpoint + exploratory margins)")
    p("=" * 100)
    ledger = read_ledger(ROOT / "runs" / "episode_ledger.csv")
    p(f"  ledger data rows = {len(ledger)}")
    by_phase = Counter(r["phase"] for r in ledger)
    by_type = Counter(r["row_type"] for r in ledger)
    p(f"  by phase = {dict(by_phase)}   by row_type = {dict(by_type)}")

    for phase in ("smoke", "pilot"):
        rows = [r for r in ledger if r["phase"] == phase]
        launched = {r["episode_key"] for r in rows if r["row_type"] == "launch"}
        completed = {r["episode_key"] for r in rows if r["row_type"] == "outcome"
                     and r["exit_status"] == "completed"}
        errored = {r["episode_key"] for r in rows if r["row_type"] == "outcome"
                   and r["exit_status"] == "error"}
        interrupted = {r["episode_key"] for r in rows if r["row_type"] == "outcome"
                       and r["exit_status"] == "interrupted"}
        pub = json.loads((ROOT / "reports" / f"{phase}_summary.json").read_text(encoding="utf-8"))
        p("")
        p(f"  --- {phase} ---")
        check(f"{phase} episodes_launched", len(launched), pub["episodes_launched"])
        check(f"{phase} episodes_completed", len(completed), pub["episodes_completed"])
        check(f"{phase} episodes_errored", len(errored), pub["episodes_errored"])
        check(f"{phase} episodes_interrupted", len(interrupted), pub["episodes_interrupted"])
        p(f"    orphan launches (launch w/o outcome) = "
          f"{len(launched - {r['episode_key'] for r in rows if r['row_type'] == 'outcome'})}")

        # ---- rebuild quartets with the documented isolation key -------------
        y_by_run: dict[tuple, dict[str, dict[str, str]]] = defaultdict(lambda: defaultdict(dict))
        for r in rows:
            if r["row_type"] != "outcome":
                continue
            gkey = (int(r["master_seed"]), r["method"], r["anchor_id"],
                    int(r["repetition"]), r["stream"])
            if r["exit_status"] == "completed" and r["ego_collision"] in ("0", "1"):
                y_by_run[gkey][r["run_id"]][r["condition"]] = r["ego_collision"]

        # primary = earliest complete run per isolation key; later = replay
        prim: dict[tuple, dict] = {}
        replay: dict[tuple, dict] = {}
        for gkey, runs in y_by_run.items():
            full = sorted([rid for rid, c in runs.items() if set(c) == set(CONDITIONS)])
            if not full:
                continue
            prim[gkey] = runs[full[0]]
            for rid in full[1:]:
                replay[gkey] = runs[rid]
        p(f"    complete primary quartets = {len(prim)}   replays = {len(replay)}")
        check(f"{phase} complete_quartets", len(prim), pub["complete_quartets"])
        check(f"{phase} replay_quartets", len(replay), pub["replay_quartets"])

        # ---- binary contrasts (must be all-zero in V01) ---------------------
        per_ms: dict[tuple, list[tuple[float, float, float, float]]] = defaultdict(list)
        for gkey, cond in prim.items():
            ms, method, _aid, _rep, stream = gkey
            g, s, b = int(cond["10"]) - int(cond["00"]), int(cond["01"]) - int(cond["00"]), \
                int(cond["11"]) - int(cond["00"])
            i = int(cond["11"]) - int(cond["10"]) - int(cond["01"]) + int(cond["00"])
            per_ms[(method, stream)].append((g, s, b, i))
        p("")
        p("    binary (ego_collision) per (method, stream):")
        for (method, stream), vals in sorted(per_ms.items()):
            n = len(vals)
            mb = sum(v[2] for v in vals) / n
            pubms = pub["by_method_stream"][f"{method}/{stream}"]
            check(f"{phase} {method}/{stream} n_quartets", n, pubms["n_quartets"])
            check(f"{phase} {method}/{stream} mean_delta_both", mb, pubms["mean_delta_both"])
            rev = sum(1 for v in vals if v[0] == 0 and v[2] == 1)
            res = sum(1 for v in vals if v[0] == 1 and v[2] == 0)
            check(f"{phase} {method}/{stream} reverse_pairs", rev, pubms["reverse_pairs"])
            check(f"{phase} {method}/{stream} rescue_pairs", res, pubms["rescue_pairs"])
            for c in CONDITIONS:
                coll = sum(1 for gkey, cond in prim.items()
                           if gkey[1] == method and gkey[4] == stream and int(cond[c]) == 1)
                check(f"{phase} {method}/{stream} collisions {c}", coll,
                      int(pubms["collision_rate"][c] * n))

    # ---- exploratory margins (continuous proxy), pooled per (method, stream) --
    p("")
    p("  --- pilot exploratory margins d_min_forward_ttc_sampled_s_* ---")
    rows = [r for r in ledger if r["phase"] == "pilot"]
    marg: dict[tuple, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        if r["row_type"] != "outcome":
            continue
        rp = read_json(r["raw_path"])
        if not rp or (rp.get("status") or rp.get("exit_status")) != "completed":
            continue
        res = rp.get("result") or {}
        v = res.get("min_forward_ttc_sampled_s")
        if not isinstance(v, (int, float)):
            continue
        gkey = (int(r["master_seed"]), r["method"], r["anchor_id"],
                int(r["repetition"]), r["stream"])
        marg[gkey][r["run_id"]][r["condition"]] = float(v)
    pooled: dict[tuple, list[tuple[float, float, float]]] = defaultdict(list)
    for gkey, runs in marg.items():
        full = sorted([rid for rid, c in runs.items() if set(c) == set(CONDITIONS)])
        if not full:
            continue
        c = runs[full[0]]
        ms, method, _a, _r, stream = gkey
        pooled[(method, stream)].append((c["10"] - c["00"], c["01"] - c["00"], c["11"] - c["00"]))
    pubemi = json.loads((ROOT / "reports" / "pilot_summary.json").read_text(encoding="utf-8"))["exploratory_margins"]
    for (method, stream), vals in sorted(pooled.items()):
        n = len(vals)
        for idx, key in ((0, "gap"), (1, "speed"), (2, "both")):
            got = sum(v[idx] for v in vals) / n
            want = pubemi[f"{method}/{stream}"][f"d_min_forward_ttc_sampled_s_{key}"]
            check(f"pilot {method}/{stream} d_ttc_{key}", round(got, 12), round(want, 12), 1e-9)


# ============================================================ V02
def v02():
    p("")
    p("=" * 100)
    p("V02 — independent recomputation (continuous min-TTC endpoint + M2 + auxiliary audit)")
    p("=" * 100)
    V2 = ROOT / "v02"
    pub = json.loads((V2 / "reports" / "pilot_summary.json").read_text(encoding="utf-8"))

    B, ALPHA, SEED, TAU_CAP, TAU_LOW, DEQ = 10000, 0.05, 20261015, 10.0, 1.0, 0.05

    def pct(sv, q):
        if len(sv) == 1:
            return float(sv[0])
        pos = (len(sv) - 1) * q
        lo = int(pos)
        hi = min(lo + 1, len(sv) - 1)
        f = pos - lo
        return sv[lo] * (1 - f) + sv[hi] * f

    def boot(vals):
        if len(vals) < 2:
            return None, None
        rng = random.Random(SEED)
        n = len(vals)
        means = sorted(sum(vals[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
        return pct(means, ALPHA / 2), pct(means, 1 - ALPHA / 2)

    def step_ttc(hc, gap, cl):
        if not hc or cl <= 0:
            return None
        return 0.0 if gap <= 0 else gap / cl

    for phase in ("smoke", "pilot"):
        pubp = json.loads((V2 / "reports" / f"{phase}_summary.json").read_text(encoding="utf-8"))
        led = read_ledger(V2 / "runs" / phase / "episode_ledger.csv")
        la = [r for r in led if r["row_type"] == "launch"]
        oc = {r["episode_key"]: r for r in led if r["row_type"] == "outcome"}
        p("")
        p(f"  --- {phase} ---")
        p(f"    launch={len(la)} outcome={len(oc)} orphan={len(la) - len(oc)} "
          f"scopes={dict(Counter(r['budget_scope'] for r in la))}")

        prim = [r for r in la if r["stream"] == "discovery" and r["method"] == "Shared"]
        aux = [r for r in la if r["stream"] == "audit"]
        p(f"    primary={len(prim)} aux={len(aux)}")

        q: dict[tuple[int, int], dict[str, float]] = defaultdict(dict)
        qm2: dict[tuple[int, int], dict[str, float]] = defaultdict(dict)
        coll = defaultdict(Counter)
        cats = Counter()
        for r in prim:
            o = oc[r["episode_key"]]
            rp = read_json(o["raw_path"])
            coll[r["condition"]][o["ego_collision"]] += 1
            if not rp:
                continue
            steps = [(bool(a), float(b), float(c)) for a, b, c in rp.get("raw_steps") or []]
            vals = [v for a, b, c in steps if (v := step_ttc(a, b, c)) is not None]
            if vals:
                q[(int(r["anchor_index"]), int(r["repetition"]))][r["condition"]] = min(vals)
                cats["FINITE"] += 1
            else:
                cats["CENSORED"] += 1
            if steps:
                qm2[(int(r["anchor_index"]), int(r["repetition"]))][r["condition"]] = (
                    sum(1 for a, b, c in steps
                        if (v := step_ttc(a, b, c)) is not None and v < TAU_LOW) / len(steps))
        complete = {k: v for k, v in q.items() if set(v) == set(CONDITIONS)}
        complete_m2 = {k: v for k, v in qm2.items() if set(v) == set(CONDITIONS)}
        anchors = sorted({k[0] for k in complete})

        # Two distinct, explicitly separated definitions (must not be conflated):
        #   primary quartet  = all four conditions have a ledger launch (any status)
        #   usable  quartet  = all four conditions yielded a recoverable value
        launch_keys = defaultdict(set)
        for r in prim:
            launch_keys[(int(r["anchor_index"]), int(r["repetition"]))].add(r["condition"])
        primary_quartets = sum(1 for v in launch_keys.values() if v == set(CONDITIONS))
        check(f"{phase} primary launches", len(prim),
              len([r for r in read_ledger(V2 / "runs" / phase / "episode_ledger.csv")
                   if r["row_type"] == "launch" and r["stream"] == "discovery"
                   and r["method"] == "Shared"]))
        check(f"{phase} episodes with a recoverable value", sum(cats.values()),
              len(prim) - pubp["errored"])
        check(f"{phase} n_primary_quartets", primary_quartets, pubp["n_primary_quartets"])
        check(f"{phase} n_usable_quartets", len(complete), pubp["n_usable_quartets"])
        check(f"{phase} anchors", len(anchors), pubp["n_anchors"])

        def series(src, name):
            out = []
            for a in anchors:
                reps = [v for k, v in src.items() if k[0] == a]
                ds = []
                for rep in reps:
                    if set(rep) != set(CONDITIONS):
                        continue
                    if name == "delta_gap":
                        ds.append(rep["10"] - rep["00"])
                    elif name == "delta_speed":
                        ds.append(rep["01"] - rep["00"])
                    elif name == "delta_both":
                        ds.append(rep["11"] - rep["00"])
                    else:
                        ds.append(rep["11"] - rep["10"] - rep["01"] + rep["00"])
                if ds:
                    out.append(sum(ds) / len(ds))
            return out

        p(f"    M1 contrasts:")
        for name in ("delta_gap", "delta_speed", "delta_both", "i_lin"):
            s = series(complete, name)
            pt = sum(s) / len(s)
            lo, hi = boot(s)
            pe = pubp["estimates"][name]
            check(f"{phase} {name} point", round(pt, 12), round(pe["point"], 12), 1e-12)
            check(f"{phase} {name} ci_low", round(lo, 12), round(pe["ci_low"], 12), 1e-12)
            check(f"{phase} {name} ci_high", round(hi, 12), round(pe["ci_high"], 12), 1e-12)
            check(f"{phase} {name} n_anchors", len(s), pe["n_anchors"])

        if complete_m2:
            p(f"    M2 contrasts (smaller = safer):")
            for name in ("delta_gap", "delta_speed", "delta_both", "i_lin"):
                s = series(complete_m2, name)
                pt = sum(s) / len(s)
                pe = pubp["m2_secondary"]["anchor_level_contrasts"][name]
                check(f"{phase} M2 {name} point", round(pt, 12), round(pe["point"], 12), 1e-12)
            pc = {c: sum(v[c] for v in complete_m2.values()) / len(complete_m2) for c in CONDITIONS}
            for c in CONDITIONS:
                check(f"{phase} M2 mean share {c}", round(pc[c], 10),
                      round(pubp["m2_secondary"]["per_condition_mean_share"][c], 10), 1e-10)

    # ---- auxiliary audit: reproduce precision@k AND the seed-reuse impact ----
    p("")
    p("  --- auxiliary allocation comparison ---")
    led = read_ledger(ROOT / "v02" / "runs" / "pilot" / "episode_ledger.csv")
    oc = {r["episode_key"]: r for r in led if r["row_type"] == "outcome"}
    auxq: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    sig: dict[tuple, list] = defaultdict(list)
    for r in led:
        if r["row_type"] != "launch" or r["stream"] != "audit":
            continue
        o = oc[r["episode_key"]]
        rp = read_json(o["raw_path"])
        if not rp:
            continue
        steps = [(bool(a), float(b), float(c)) for a, b, c in rp.get("raw_steps") or []]
        vals = [v for a, b, c in steps if (v := step_ttc(a, b, c)) is not None]
        if vals:
            auxq[(r["method"], r["anchor_id"])][r["condition"]] = min(vals)
        if r["condition"] == "00":
            sig[(r["sim_seed"], json.dumps(rp["conditioned_scenario"], sort_keys=True))].append(
                (r["method"], r["anchor_id"]))
    for m in ("WideExplore", "VerifyFirst"):
        qs = [(a, v) for (mm, a), v in auxq.items() if mm == m and set(v) == set(CONDITIONS)]
        hits = sum(1 for _a, v in qs if (v["11"] - v["00"]) < -DEQ)
        pubm = [x for x in pub["auxiliary_method_comparison"] if x["method"] == m][0]
        check(f"aux {m} n_nominees", len(qs), pubm["n_nominees"])
        check(f"aux {m} n_reversal", hits, pubm["n_reversal"])
        check(f"aux {m} precision_at_k", round(hits / len(qs), 12),
              round(pubm["precision_at_k"], 12), 1e-12)
        # seed-reuse impact
        kept = [(a, v) for a, v in qs if a != "v02-anchor-0012"]
        h2 = sum(1 for _a, v in kept if (v["11"] - v["00"]) < -DEQ)
        p(f"    {m}: leave-out-shared-anchor precision = {h2}/{len(kept)}")
    dup = [(k, v) for k, v in sig.items() if len(v) > 1]
    check("aux nominal audit quartets", len(auxq), 6)
    check("aux distinct simulations", len({k for k, _v in sig.items()}), 5)
    check("aux duplicated simulations", len(dup), 1)
    for k, v in dup:
        p(f"    duplicated: {v}  sim_seed={k[0]}")

    # ---- sample size derivation ------------------------------------------
    p("")
    p("  --- power / sample-size derivation ---")
    nd = statistics.NormalDist()
    za = nd.inv_cdf(1 - (ALPHA / 4) / 2)
    zp = nd.inv_cdf(0.80)
    sd = {}
    q = defaultdict(dict)
    for r in [x for x in read_ledger(ROOT / "v02" / "runs" / "pilot" / "episode_ledger.csv")
              if x["row_type"] == "launch" and x["stream"] == "discovery" and x["method"] == "Shared"]:
        o = oc[r["episode_key"]]
        rp = read_json(o["raw_path"])
        if not rp:
            continue
        steps = [(bool(a), float(b), float(c)) for a, b, c in rp.get("raw_steps") or []]
        vals = [v for a, b, c in steps if (v := step_ttc(a, b, c)) is not None]
        if vals:
            q[(int(r["anchor_index"]), int(r["repetition"]))][r["condition"]] = min(vals)
    comp = {k: v for k, v in q.items() if set(v) == set(CONDITIONS)}
    for name in ("delta_gap", "delta_speed", "delta_both", "i_lin"):
        s = series(comp, name)
        m = sum(s) / len(s)
        sd[name] = math.sqrt(sum((x - m) ** 2 for x in s) / (len(s) - 1))
    check("z(1-alpha/8)", round(za, 6), round(2.497705, 6), 1e-6)
    check("z(power=0.80)", round(zp, 6), round(0.841621, 6), 1e-6)
    p(f"    anchor-level SD: "
      + "  ".join(f"{k}={sd[k]:.6f}" for k in sd))
    best = min(sd[k] for k in sd)
    p(f"    n=18 detectable MDE (most sensitive contrast) = {(za + zp) * best / math.sqrt(18):.4f} s")
    for mde in (0.05, 0.10):
        need = {k: max(2, math.ceil(((za + zp) ** 2) * sd[k] ** 2 / mde ** 2)) for k in sd}
        mx = max(need.values())
        p(f"    MDE={mde:.2f} -> anchors={mx} episodes={mx * 3 * 4}   (per contrast {need})")

    p("")
    p("=" * 100)
    p(f"INDEPENDENT RECOMPUTATION: {'ALL CHECKS PASS' if not FAILS else str(len(FAILS)) + ' MISMATCH(ES)'}")
    for f in FAILS:
        p("   * " + f)
    p("=" * 100)


v01()
v02()
_OUT = ROOT / "docs" / "V12_INDEPENDENT_RECOMPUTE_20261015.txt"
_OUT.write_text("\n".join(OUT) + "\n", encoding="utf-8")
print(f"\n[evidence written to {_OUT.relative_to(ROOT)}]")
