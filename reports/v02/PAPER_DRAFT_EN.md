# Counterfactual Safety-Reversal Testing in a Simplified Highway-Merge Simulator:
# a Protocol-Frozen, Estimation-Only Pilot Study (PAPER DRAFT — NOT SUBMISSION READY)

**Status: closed exploratory/descriptive study — draft for internal review only. NOT SUBMISSION READY.**
This manuscript describes a pilot-scale, estimation-only study. It contains no confirmatory result,
no p-value, and no claim about real-road safety. It is not externally pre-registered. It must not be
submitted or circulated as a finished paper.

**Closure status (2026-10-15).** The owner has fixed the following once and for all: V01's formal
evaluation is **NO-GO**; **V02 is closed as a complete exploratory/descriptive study**;
**M1 (per-episode minimum forward TTC) is the single primary *descriptive* endpoint and M2 (share of
steps below τ_low) is an auxiliary indicator**; **MDE = 0.10 s is a planning example only and
authorises nothing**; **no significance claims are made**; the legacy V01 items D4/D5/D6 remain
**archived and unapproved**; **external peer review is optional future work and does not block this
closure**. Decisions with reasons: `docs/FINAL_CLOSURE_DECISIONS.md`. Claim-to-evidence register:
`docs/CLAIMS_REGISTER.zh-CN.md`. Independent recomputation of every quoted number (141 assertions,
all passing, importing none of the reporting modules): `docs/V12_INDEPENDENT_RECOMPUTE_20261015.txt`.

---

## Abstract

We ask whether two intuitive safety-improving changes to a highway-merge scenario — increasing the
initial front gap by 2 m and reducing the ego initial speed by 1 m/s — can *reduce* the continuous
forward safety margin, and whether their joint effect is non-additive. We study a simplified
merge scenario driven by a frozen, deterministic rule controller inside a fixed simulator
contract (`cornercaselab 0.3.0`, HighwayEnv 1.10.2, 25 s horizon, 15 Hz simulation / 5 Hz policy).
A prior pilot with a binary collision endpoint produced **zero collisions in 264 real episodes**,
so we replaced the endpoint with the per-episode minimum forward time-to-collision (min-TTC), and we
introduced a **within-anchor shared perturbation** that makes repetitions land on genuinely different
initial ego–lead geometries (repetitions are *not* claimed to be statistically independent;
the anchor remains the independent unit). In a pilot of **240 real episodes** (18 anchors ×
3 repetitions × 4 conditions) plus an auxiliary 24-episode audit that proved **less independent than
intended** (Section 4.4), all technical gates
passed: within-anchor variance of the control condition was 0.092 s² (previously 0 by construction),
and min-TTC was no longer bitwise identical across repetitions for any of the 18 anchors.
Anchor-level paired contrasts were `Δ_gap = +0.013 s` [−0.053, +0.077], `Δ_speed = +0.033 s`
[−0.059, +0.124], `Δ_both = +0.003 s` [−0.044, +0.053] and the linear interaction
`I_lin = −0.042 s` [−0.147, +0.061] (anchor-level cluster bootstrap, B = 10,000).
**We found no safety reversal and no decidable non-additivity.** However, the anchor-level signs are
**heterogeneous** (`Δ_both` is negative for 10 of 18 anchors; dropping the three largest positive
anchors moves the mean to −0.033 s), and the observed effect magnitudes (0.003–0.033 s) are at or
below the known systematic error scale of a 1D constant-velocity TTC surrogate (~0.2 s at TTC ≈ 1 s),
so the null cannot be separated from insufficient endpoint resolution. Only two collisions occurred
across 54 complete quartets — and **none in the joint-intervention condition** — so the binary
endpoint supports no rate claim. The contribution of this draft is methodological: a
reproducible-by-construction apparatus for counterfactual, anchor-clustered safety-margin testing with
hard budget accounting, plus an honestly reported, carefully bounded negative result.

## 1. Introduction

Simulation-based safety evaluation frequently rests on *surrogate* safety measures, most commonly
time-to-collision (TTC). Two difficulties are well documented. First, one-dimensional TTC computed
under a constant-velocity assumption can deviate substantially from higher-fidelity measures —
reported deviations of roughly 300% for TTC above 1.5 s and ~20% below 1.5 s (Li et al., 2024).
Second, TTC, post-encroachment time and deceleration-rate measures can be insufficient to
characterise safety when successive vehicles travel at similar speeds, particularly for automated
vehicles in small-gap car-following (Do et al., 2025). Both caveats apply directly to our setting.

We study a narrower and more basic question for which we did **not** find a directly equivalent
statement in the (non-exhaustive) literature we were able to verify: **under a fixed simulator and
a fixed rule controller, can a change that is intuitively safety-improving counterfactually reduce
the safety margin?** If so, the sign of a parameter's effect is not inferable from intuition, and
parameter sweeps used to build test suites must be evaluated rather than assumed. This is a
combination claim, not a priority claim: every *component* we use has precedent (see below), and
we explicitly do not assert originality.

Two design requirements follow from our earlier negative experience (Section 3.1). (i) The endpoint
must have variance under the controller actually used. (ii) Independent repetitions must genuinely
resample the interaction of interest; otherwise replication adds no information and the effective
sample size collapses to the number of anchors.

## 2. Related work

- **Surrogate measure fidelity.** Li et al. (2024, *Accident Analysis and Prevention* 204:107649,
  doi:10.1016/j.aap.2024.107649) give a generic framework spanning 1D to 3D surrogate measures and
  quantify the error of 1D measures. Our primary endpoint is a 1D, constant-velocity, 5 Hz-sampled
  TTC, so we inherit that limitation explicitly (Section 6).
- **Adequacy of conventional indicators.** Do et al. (2025, *Transportation Research Record*
  2679(2):1118–1133, doi:10.1177/03611981241265849) evaluate eight surrogate indicators for
  connected and automated vehicles and find TTC/PET/DRAC insufficient when successive vehicles run
  at similar speeds. This matches our diagnosis of a deterministic controller that maintains
  headway, driving collision events towards zero.
- **Counterfactual and metamorphic testing.** The counterfactual-quartet design here is close in
  spirit to metamorphic testing of simulators; we treat the four conditions of a quartet as a
  controlled 2² factorial *within* an anchor rather than as independent samples.
- **Pre-registration and post hoc risk.** Because our design was motivated by an earlier pilot, we
  adopt a firewall (earlier data used only for pipeline validation), a full parameter freeze with a
  SHA-256 fingerprint, a new protocol id and master seed, and an estimation-only analysis with
  confirmatory tests explicitly gated off.

We do not claim novelty for the method-comparison component, the independent-audit machinery, or
equal-budget pairing: these overlap substantially with existing exploration-vs-confirmation
benchmarking and are treated as auxiliary here. The upstream package we build on
(CornerCaseLab v0.3.0, Apache-2.0) states the same research question — how to split a fixed budget
between exploring new scenarios and confirming whether an observed failure survives local
perturbation — and already implements paired equal-budget methods, an independent Final Audit with
fresh draws, a SHA-256 seed derivation, percentile bootstrap intervals, and an explicit decision
**not** to report p-values. Its public evaluation protocol (`cornercaselab_v03_eval_v1`) freezes 20
paired seeds × 3 methods × 1000 slots = 60,000 episodes and scores a six-dimensional spatial-dedup
metric (SNY) with a Wilson ≥ 21/30 stability rule. **The absence of p-values in our study is
therefore convergence with an existing methodological position, not a contribution.** A full
item-by-item difference table (with what is shared, what differs, and what remains unverified)
is in `docs/LITERATURE_DIFFERENCE_TABLE.zh-CN.md`; the read-only overlap check is in
`docs/CORNERCASELAB_OVERLAP_VERIFIED.md`.

## 3. Method

### 3.1 Motivation from a prior pilot (V01)

An earlier protocol in the same simulator used a binary ego-collision endpoint with 264 real
episodes (24 smoke + 240 pilot). All 264 episodes were collision-free. Two mechanism-level findings
explain this. First, the frozen `boundary` rule controller brakes when the forward gap falls below
`6.0 + 0.30·v_x` metres (≈14.4 m at 28 m/s) or when `gap/closing < 0.90 s`, so it actively maintains
separation. Second, the simulator's `sim_seed` only randomises the IDM exponent `Δ` of the two
NPC vehicles, while the lead vehicle starts at `speed = target_speed` in free flow; the IDM
free-flow term `a_max·(1 − (v/v₀)^Δ)` is then identically zero regardless of `Δ`. Consequently the
lead trajectory is seed-independent, min-TTC is decided by the lead, and **min-TTC was bitwise
identical across repetitions in all 36 multi-repetition groups**. Replication therefore carried no
information, and a model-based comparison of two anchor-allocation strategies collapsed to a
tie-break on anchor order.

### 3.2 Design

**Anchor.** A nominal six-dimensional scenario
`(ego_speed, front_gap, front_speed, ramp_x, ramp_speed, ramp_target_speed)`, drawn from a
deterministic SHA-256 rejection stream inside a narrowed domain: `ego_speed ∈ [23, 30]`,
`front_gap ∈ [21, 40]`, `front_speed ∈ [17, 21]`, remaining three dimensions at the upstream bounds.
The domain is deliberately narrowed to a closing regime so the ego–lead interaction dominates.

**Repetition and conditions.** One repetition draws a single perturbation
`(Δgap, Δspeed_lead, Δspeed_ego) ~ U(±3 m), U(±1.5 m/s), U(±0.5 m/s)` around the anchor nominal.
The four conditions apply the frozen structural intervention on top of the *same* perturbed base:

| condition | change |
|---|---|
| `00` | none |
| `10` | `front_gap += 2.0 m` |
| `01` | `ego_speed −= 1.0 m/s` |
| `11` | both |

All four conditions of a repetition share one perturbation draw and one `sim_seed`; `condition` is
never a seed label. Repetitions differ in both. Legality is enforced by rejection sampling with an
extreme-corner pre-check; **no value is ever clipped**.

**Simulator.** Perturbation is purely scenario-level: the frozen upstream
`cornercaselab.simulator.evaluate(scenario, sim_seed, policy="boundary", SimSettings(25, 15, 5))`
is called unmodified. No physics, controller or environment construction is re-implemented.

**Endpoint.** `M1` = per-episode minimum forward TTC, with three-layer handling:
Layer 1 per step (`NORMAL_CLOSING` / `NO_CLOSING` / `NO_CANDIDATE`; `None ≠ safe`);
Layer 2 episode (`FINITE` / `CENSORED` at `τ_cap = 10 s` / `NO_CANDIDATE` / `MISSING`);
Layer 3 termination (horizon / terminal event / technical failure).
Missing conditions make the whole repetition's contrasts undefined; no imputation is performed.

**Effect sizes.** Anchor-level paired differences, pairing within repetition then averaging:
`Δ_gap = M(10) − M(00)`, `Δ_speed = M(01) − M(00)`, `Δ_both = M(11) − M(00)`,
`I_lin = M(11) − M(10) − M(01) + M(00)`.

**Budget.** Smoke 24 = 3 anchors × 2 repetitions × 4. Pilot 240 = 18 anchors × 3 repetitions × 4
(216) + 2 allocation strategies × 3 nominees × 1 fresh audit quartet (24). All launched attempts,
including failures, are billed; there is no free retry and budgets are not transferable.

**Statistics.** The independent unit is the anchor. Intervals are anchor-level cluster bootstrap
percentile intervals (B = 10,000, α = 0.05, fixed analysis seed 20261015). Confirmatory sign-flip /
max-T tests are **gated**: they return `PENDING` unless an exchangeability basis (A/B/C) is formally
established. None is, so **no p-value is produced anywhere in this study**.

## 4. Results

### 4.1 Execution and gate checks

| Item | Smoke | Pilot |
|---|---:|---:|
| Launched / cap | 24 / 24 | 240 / 240 |
| Completed | 23 | 240 |
| Errors / interrupted | 1 / 0 | 0 / 0 |
| Complete quartets (usable) | 6 (5) | 54 (54) |
| Wall clock (s) | 26.0 | 262.5 |

All gates passed. Anchor-level within-anchor variance of the control condition (G3a) was
**0.0917 s²** against 0 previously. Perturbation effectiveness (G4): **18 of 18** anchors had
non-identical min-TTC across repetitions, against 36/36 identical previously. Intervention legality
(G2): zero out-of-bounds cases, zero application mismatches. Metric equivalence: the reconstructed
per-step minimum matched the simulator's own `min_forward_ttc_sampled_s` for all 240 pilot episodes
with a **maximum absolute discrepancy of 8.3 × 10⁻⁶ s** (tolerance 10⁻⁴ s), the residual being
9-decimal trajectory rounding plus the `vx = speed·cos(heading)` reconstruction.

The single smoke error was an archive-serialisation defect in this study's own newly written runner;
the episode's real simulation had executed but its record was unusable. It was billed once, recorded
as an error, and **not re-run**.

### 4.2 Primary (descriptive) endpoint M1

M1 is the single primary endpoint; M2 (Section 4.2.3) is auxiliary and carries no primary inference.
The two endpoints use **opposite** raw sign conventions for "protective" (M1: larger is safer;
M2: smaller is safer), so their signs must never be compared directly.

n = 18 anchors, 3 usable repetitions each.

| Contrast | Point estimate (s) | 95% cluster bootstrap CI (s) | CI excludes 0 |
|---|---:|---|---|
| `Δ_gap` | +0.0127 | [−0.0525, +0.0769] | no |
| `Δ_speed` | +0.0327 | [−0.0589, +0.1243] | no |
| `Δ_both` | +0.0030 | [−0.0436, +0.0526] | no |
| `I_lin` | −0.0424 | [−0.1465, +0.0613] | no |

Point estimates of all three directional contrasts lie in the intuitive (protective) direction, but
no interval strictly excludes zero. **No safety reversal is supported, and no non-additive
interaction is decidable.** An independent re-implementation that reads only the ledger and archived
raw records reproduced every point estimate and interval exactly (differences < 10⁻¹²).

#### 4.2.1 Anchor-level sign heterogeneity (must be read with the means)

| Contrast | n | negative | positive | mean (s) | mean dropping 3 largest positive (s) | min | max |
|---|---:|---:|---:|---:|---:|---:|---:|
| `Δ_gap` | 18 | 8 | 10 | +0.0127 | −0.0307 | −0.297 | +0.293 |
| `Δ_speed` | 18 | 10 | 8 | +0.0327 | −0.0313 | −0.435 | +0.394 |
| `Δ_both` | 18 | **10** | 8 | +0.0030 | **−0.0327** | −0.198 | +0.215 |
| `I_lin` | 18 | 10 | 8 | −0.0424 | −0.1088 | −0.563 | +0.523 |

The near-zero aggregate means are **not** evidence that no anchor shows an effect; they arise from
cancellation of opposite-signed anchor effects. `Δ_both` is negative — the reversal direction — for
10 of 18 anchors, and removing the three largest positive anchors flips the mean to −0.033 s.
The accurate statement of our result is therefore: *the aggregate effect is indistinguishable from
zero on 18 anchors, but the anchor-level signs are strongly heterogeneous, with a majority pointing
in the reversal direction.* This is a descriptive, pre-specified sensitivity check, not an inference.

#### 4.2.2 Endpoint resolution versus effect size (the leading alternative explanation)

Observed effects are 0.003–0.033 s and interval half-widths are 0.05–0.09 s. The known systematic
deviation of a 1D constant-velocity surrogate from higher-fidelity measures is of order 20% for TTC
below 1.5 s (Li et al., 2024) — at TTC ≈ 1 s that is ≈ 0.2 s. **The observed effects and the
interval widths are therefore at or below the endpoint's own systematic error scale.** A null result
here cannot be separated from insufficient endpoint resolution, and we do not claim the interventions
are ineffective. Distinguishing the two would require a higher-fidelity endpoint or a much larger
anchor sample, both outside the present budget.

#### 4.2.3 Registered secondary endpoint M2

M2 is the share of policy steps with forward TTC below τ_low = 1.0 s, recomputed from the archived
per-step records (no extra simulation). Smaller is safer.

> **Corrected in the final research audit (D43).** The earlier version of this table was produced by
> a reader that located episodes via a `runs/<phase>/*/*.json` filename glob. Because the primary
> (`discovery`) and auxiliary (`audit`) streams both write `<anchor_id>_rep<r>_<cond>.json`, the
> audit episodes overwrote the primary M2 values for the five nominee anchors at repetition 0, so
> M2 silently mixed in 20 auxiliary episodes (240 parsed instead of 216). The reader now takes the
> episode set from the **ledger's own `raw_path`**; a regression test reproduces the failure mode.
> The numbers below are the corrected ones.

| Condition | mean share |
|---|---:|
| `00` | 0.02339 |
| `10` | 0.02525 |
| `01` | 0.01270 |
| `11` | 0.01717 |

Anchor-level contrasts: `Δ_gap = +0.00186` [−0.02246, +0.02618], `Δ_speed = −0.01069`
[−0.03283, +0.00506], `Δ_both = −0.00623` [−0.02453, +0.00639], `I_lin = +0.00261`
[−0.02350, +0.03035] (n = 18).

Because smaller is safer for M2, the protective direction is **negative**. `Δ_speed` and `Δ_both`
are negative and therefore agree with M1; **`Δ_gap` is positive and therefore does *not* agree with
M1**; `I_lin` is positive. No interval excludes zero. Contrary to the earlier text, the two
endpoints **do not agree uniformly**: on `Δ_gap` they point in opposite directions (neither
significantly). That disagreement is a symptom of operating at the surrogate's resolution limit
(Section 4.2.2) and is **not** evidence of reversal. The registered `NO_CANDIDATE` exclusion
sensitivity does not apply: all 216 primary episodes were Layer-2 `FINITE`.

### 4.3 Secondary endpoints

Collision events over 54 complete quartets: condition `00` 1, `10` 1, `01` 0, `11` 0.
Reverse pairs (`Y00=0, Y11=1`) = 0; rescue pairs (`Y00=1, Y11=0`) = 1.
With two events the binary endpoint supports **no rate claim**; the so-called rule of three is not
applied because its i.i.d. Bernoulli premise fails here (anchors are deterministically generated and
the four conditions share a paired seed).
`I_log` was definable for 53/54 quartets (98.1%), mean −0.081, with one `ZERO_TTC` reason code; no
floor was applied.

### 4.4 Auxiliary allocation comparison

Both strategies nominated from the same discovery quartets; only the allocation rule differed.

| Strategy | Nominees | Usable audit quartets | Reversal hits | precision@k |
|---|---|---:|---:|---:|
| WideExplore (one quartet per anchor) | 0008, 0003, 0012 | 3 | 1 | 0.333 |
| VerifyFirst (anchor-level mean, re-verified first) | 0014, 0012, 0009 | 3 | 3 | 1.000 |

Unlike the earlier protocol, the two strategies now nominate *different* anchors, because the
continuous endpoint no longer degenerates. However, with three nominees and one audit quartet each,
and with the audited anchors being a selected subset, this is **exploratory only** and supports no
conclusion about the strategies. Two further defects must be disclosed. First, **the two nomination
sets overlap** (anchor 0012 is nominated by both), so the two `precision@k` values are not
independent. Second, and more seriously, the audit seed derivation **hardcoded the method label** as
`"shared"`, so for the overlapping anchor the two strategies ran an *identical* simulation with an
identical `sim_seed` and an identical trace hash. Of the nominal six audit quartets (24 episodes),
only **five distinct simulations** occurred; **four episodes (16.7 %) were duplicated runs, each
billed**. The claim of a "fresh, independent audit" therefore did **not** hold for the overlapping
anchor at the time the data were collected. The defect is fixed in the code (the method label is now
a required seed input, with two regression tests), but the recorded pilot data cannot be re-run
because the protocol budget is exhausted, so the numbers above are retained unchanged and disclosed
here.

### 4.5 Hypothesis verdicts (stated explicitly, not left implicit)

The criterion is **descriptive** (does the interval strictly exclude zero, and does the effect exceed
the endpoint's resolution?). **No p-value is produced**, so no hypothesis can be reported as
"supported" or "proven".

| Hypothesis | Expected direction | Observed (point / 95% anchor CI, s) | **Verdict** | Why it is undecidable |
|---|---|---|---|---|
| **H-R1a** (`Δ_gap` reversal) | reversal = point < 0 with CI strictly left of 0 | +0.0127 / [−0.0525, +0.0769] | **INCONCLUSIVE** | CI spans 0; effect (0.01 s) far below the surrogate's systematic error (~0.2 s); M2 even points the other way for `Δ_gap` |
| **H-R1b** (`Δ_speed` reversal) | as above | +0.0327 / [−0.0589, +0.1243] | **INCONCLUSIVE** | CI spans 0; insufficient resolution |
| **H-R1c** (`Δ_both` reversal) | as above | +0.0030 / [−0.0436, +0.0526] | **INCONCLUSIVE** | CI spans 0; anchor signs strongly heterogeneous (10/18 negative), so the pooled mean is not representative |
| **H-I-lin** (non-additivity) | CI excludes 0 | −0.0424 / [−0.1465, +0.0613] | **INCONCLUSIVE** | CI spans 0; insufficient resolution |
| **H2** (nomination-quality difference) | — | WideExplore 1/3 vs VerifyFirst 3/3 | **NOT ESTABLISHED** | 3 nominees × 1 audit quartet per method (3 degrees of freedom); the two nominee sets **share one anchor** whose two audits were the **same simulation**; audited anchors are a selected subset |

Methodological statements, likewise labelled:

| Claim | Verdict | Basis |
|---|---|---|
| "endpoint variance has been restored from zero" | **ESTABLISHED (descriptive fact)** | G3a: control-condition within-anchor variance 0.0917 s² (0 in V01) |
| "the perturbation makes min-TTC non-identical across repetitions" | **ESTABLISHED (descriptive fact)** | G4: 18/18 anchors |
| "repetitions are now mutually **independent** samples" | **NOT ESTABLISHED** | only non-identity is shown; the independent unit remains the anchor |
| "the metric implementation matches upstream" | **ESTABLISHED (verification fact)** | 240/240 within 8.3e-6 s (tolerance 1e-4) |
| "one strategy is better than the other" | **NOT ESTABLISHED** | see H2 |

**Overall**: every scientific hypothesis in this study is **INCONCLUSIVE** or **NOT ESTABLISHED**.
No directional claim is proven. This is the honest result and must not be restated more strongly.

## 5. Discussion

The central methodological claim of this draft is *negative-result-preserving*: a continuous
endpoint plus within-anchor perturbations can restore resolution where a binary endpoint and
seed-only replication had none, and doing so can still yield a null result, which we report as such.
Concretely, three checks establish that the apparatus is working (G2, G3a, G4 and metric
equivalence), and yet the intervention effects are indistinguishable from zero at this scale.

Two interpretations are consistent with the data. Either the interventions genuinely have small
effects in this scenario and controller regime, or the pilot is underpowered relative to the true
effect size. We cannot distinguish these. A sample-size derivation is now available from the
18-anchor pilot (`v02lab/power.py`, `docs/V02_SAMPLE_SIZE_DERIVATION.md`): with a two-sided
α = 0.05 spread over a pre-registered family of four contrasts (Holm worst case, i.e. 0.0125 per
contrast) and 80% power, n = 18 anchors can detect only ≈ 0.084 s or larger. Detecting 0.10 s
would require ≈ 59 anchors (708 episodes at 3 repetitions × 4 conditions); 0.05 s would require
≈ 235 anchors (2,820 episodes). The formal sample size nevertheless remains **unfrozen**, because
the derivation needs (i) an owner-declared minimum detectable effect and (ii) a stronger variance
estimate than 18 anchors can provide. The derivation authorises nothing and no formal run exists.

We also note that the earlier pilot's exploratory negative `ΔTTC` was not confirmed. That signal was
deterministic (identical across repetitions) and therefore never carried independent information; its
non-replication here is consistent with it having been a property of the closed-loop geometry rather
than a stochastic risk effect.

## 6. Limitations

1. **Post hoc design.** The design was motivated by an earlier pilot in the same simulator. The
   *configuration* was frozen before the data reported here (config timestamp 17:04, first episode
   launch 17:10), and the earlier data are kept strictly out of this analysis — but the narrative
   freeze record and the decision log were written after the data, so the written evidence of
   pre-registration is weak, and post hoc risk is mitigated, not removed. This study is
   **not** externally pre-registered.
2. **Proxy endpoint.** min-TTC is 1D, constant-velocity, sampled at 5 Hz and longitudinal only. It is
   not a collision probability. The observed effect magnitudes and interval widths are at or below
   the surrogate's own systematic error scale (~0.2 s), so the null result cannot be separated from
   insufficient endpoint resolution.
3. **Strong anchor-level heterogeneity.** `Δ_both` is negative for 10 of 18 anchors; the aggregate
   mean does not represent the typical anchor.
4. **Small, non-random anchor sample.** 18 anchors from a deterministic stream; intervals are
   descriptive and do not represent sampling from a real-world scenario population.
5. **Narrowed domain.** Conclusions are conditional on the closing regime studied.
6. **No confirmatory inference.** No p-values, no FWER control: estimation only.
7. **Binary endpoint uninformative.** Two events, none in the joint-intervention condition.
8. **Reduced scope versus the originating proposal.** A lead-vehicle braking event and a
   lead-speed-vs-target-speed decoupling were not implemented, because the former needs a custom
   environment loop and the latter is not expressible through the upstream scenario schema without
   changing simulator semantics. Collision events therefore remain rare.
9. **Auxiliary comparison is compromised** by a shared nominee and by a now-fixed seed-label defect
   that duplicated four audited episodes (Section 4.4). Because the two nomination sets share
   `anchor-0012`, the two `precision@k` values are positively dependent: dropping that shared anchor
   moves WideExplore from 1/3 to 0/2 and VerifyFirst from 3/3 to 2/2. The historical audit is
   therefore **not** an independent comparison, even though the code defect is fixed.
10. **A secondary endpoint was initially computed over the wrong episode set.**
    `m2_from_raw` located episodes by filename glob, so auxiliary audit episodes overwrote primary
    M2 values for five anchors at repetition 0 (Section 4.2.3). Corrected; the correction changes the
    sign of `Δ_gap` for M2 and removes the claim that the two endpoints agree uniformly. No M1
    quantity was affected.
11. **Determinism of the pipeline** is established by construction plus four pairs of duplicated
    episodes with identical trace hashes; no full same-seed replay was executed for this protocol.
12. **Reporting errors.** Every quoted number is reproduced from the ledger and archived raw records
    by two independent scripts; see the reproduction section. Two independent adversarial reviews
    (code/statistics and research method) were run against these materials, and their findings are
    recorded in `docs/REVIEW_RESPONSE.md`.

## 7. Reproduction

```
# environment: Python 3.13, project venv, cornercaselab 0.3.0, highway-env 1.10.2, gymnasium 1.2.2
cd SafeFlipLab/v02
python -m v02lab doctor                     # 7/7 PASS, launches nothing
python -m unittest discover -s tests        # 143 tests, no real episodes
python -m v02lab report --phase smoke
python -m v02lab report --phase pilot
# independent recomputation of EVERY quoted number (V01 + V02, imports no reporting module)
python ../scripts/independent_verify_all.py                  # -> ALL CHECKS PASS (141 assertions)
```
Frozen protocol: `v02/configs/v02_frozen_v1.json` (SHA-256
`d175ec90eecf4e8080d33cc43aab1e2f1c469b73588c6a682bfdfd30c8dd9925`).
Ledgers: `v02/runs/smoke/episode_ledger.csv`, `v02/runs/pilot/episode_ledger.csv` (21 columns each).
Both budgets are exhausted; re-invocation is refused by the ledger.

## 8. Ethics, data and provenance

No real vehicles, no human subjects and no personal data were involved. The simulator and scenario
family are third-party open components used unmodified and attributed; no upstream frozen evaluation
data were copied. The authors make no claim of novelty priority for the allocation-comparison,
audit or equal-budget components.

## References (verified records)

1. Li, S., Anis, M., Lord, D., Zhang, H., Zhou, Y., Ye, X. (2024). Beyond 1D and oversimplified
   kinematics: A generic analytical framework for surrogate safety measures. *Accident Analysis and
   Prevention*, 204, 107649. doi:10.1016/j.aap.2024.107649 (preprint arXiv:2312.07019).
2. Do, W., Saunier, N., Miranda-Moreno, L. (2025). Evaluation of Conventional Surrogate Indicators
   of Safety for Connected and Automated Vehicles in Car Following at Signalized Intersections.
   *Transportation Research Record*, 2679(2), 1118–1133. doi:10.1177/03611981241265849.
3. Additional related work verified for the companion protocol is listed in
   `docs/RELATED_WORK.md` and `docs/RELATED_WORK_V02.md`; entries marked NOT VERIFIED there are not
   cited here.

## Statement on readiness and closure

This is a **closed exploratory/descriptive study**, not a submittable manuscript. It reports a
pilot-scale, estimation-only study with a negative primary result, an underpowered and
non-independent auxiliary comparison, a proxy endpoint, and a post hoc design origin.

The exploratory phase is **closed** as of 2026-10-15 (see `docs/FINAL_CLOSURE_DECISIONS.md`):
V01 formal is permanently NO-GO; M1 is the primary descriptive endpoint and M2 auxiliary, with the
M1/M2 sign disagreement on `Δ_gap` retained and disclosed; the MDE = 0.10 s derivation is a planning
example only and authorises nothing; and no significance claim of any kind is made.

Any future formal study would require, in order: (i) an owner-declared minimum detectable effect,
(ii) a stronger anchor-level variance estimate from a newly authorised dataset, (iii) a freshly
pre-registered confirmatory protocol with its own budget, and (iv) either a justified exchangeability
basis for confirmatory tests or an explicit decision to remain estimation-only. None of these is
available under the present authorisation, and this closure does not create them.
