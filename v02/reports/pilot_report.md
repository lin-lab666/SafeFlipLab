# SafeFlipLab V02 — pilot 阶段报告（真实数据）

- 协议：SafeFlipLab-v02（hash `d175ec90eecf4e80…`，FROZEN）
- 已发起 episodes（全部计费）：**240** / cap 240
- 完成：**240**；错误：**0**；中断：**0**
- 墙钟：262.48 s
- 主研究 quartet：54（可用 54）；anchor 数：18
- 度量等价性（重新计算）：越界 0/240，最大绝对差 0.000008291 s（容差 0.0001 s）

## 1. 主终点与锚级效应量（anchor 为独立单元）

M1 = 每个 episode 的最小前向 TTC（秒）。Δ 为锚级配对差均值；
区间为锚级 cluster bootstrap（重采样单位为 anchor）。
**负值 = 干预降低了安全裕度（反转方向）**。

| 对比 | 含义 | 点估计 (s) | 95% 区间 (s) | 锚数 |
|---|---|---:|---|---:|
| delta_gap | 10-00 (gap) | 0.0127 | [-0.0525, 0.0769] | 18 |
| delta_speed | 01-00 (speed) | 0.0327 | [-0.0589, 0.1243] | 18 |
| delta_both | 11-00 (both) | 0.0030 | [-0.0436, 0.0526] | 18 |
| i_lin | interaction | -0.0424 | [-0.1465, 0.0613] | 18 |

- 确证性检验状态：**PENDING**（抽样假设 A/B/C 未成立，**不产出任何 p 值**）

## 1b. 锚级异质性与敏感性（必须与均值一同阅读）

> 只看聚合均值会掩盖**多数锚指向另一方向**这一事实。

| 对比 | 锚数 | 负向锚数 | 正向锚数 | 0 | 均值 (s) | 剔除最大 3 个正向锚后的均值 (s) | min | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| delta_gap | 18 | 8 | 10 | 0 | 0.0127 | -0.0307 | -0.2968 | 0.2929 |
| delta_speed | 18 | 10 | 8 | 0 | 0.0327 | -0.0313 | -0.4352 | 0.3945 |
| delta_both | 18 | 10 | 8 | 0 | 0.0030 | -0.0327 | -0.1980 | 0.2154 |
| i_lin | 18 | 10 | 8 | 0 | -0.0424 | -0.1088 | -0.5631 | 0.5228 |

- 该敏感性检查在本报告中**预先指定**，属描述性，不具推断意义。

## 1c. 次要终点 M2（前向 TTC 低于阈值的步占比）

> ⚠️ **方向警告（D43）**：M2 的数值**越小越安全**，故负 Δ = 更安全 —— 与 M1（min-TTC，正 Δ = 更安全）**方向相反**。请勿跨终点直接比较符号。

- τ_low = 1.0 s；解析原始记录 216 个；完整 quartet 54 个
- 各条件均值占比：00=0.0234，10=0.0252，01=0.0127，11=0.0172

| 对比 | 点估计 | 95% 锚级区间 | 锚数 |
|---|---:|---|---:|
| delta_gap | 0.0019 | [-0.0225, 0.0262] | 18 |
| delta_speed | -0.0107 | [-0.0328, 0.0051] | 18 |
| delta_both | -0.0062 | [-0.0245, 0.0064] | 18 |
| i_lin | 0.0026 | [-0.0235, 0.0303] | 18 |

- M2 (registered secondary): share of policy steps with forward TTC below tau_low; descriptive, same anchor clustering as M1

- **NO_CANDIDATE 剔除敏感性分析**：本阶段 Layer-2 组成见门槛表；若不存在 `NO_CANDIDATE`/`CENSORED` episode，则该项**不适用**（无截断可剔除）。

## 2. 二元碰撞端点（仅描述）

- 完整 quartet 数：54
- 四条件事件计数：{'00': 1, '10': 1, '01': 0, '11': 0}
- reverse_pairs（Y00=0,Y11=1）：0；rescue_pairs（Y00=1,Y11=0）：1
- 说明：descriptive only; 0 events means no rate claim is made

## 3. I_log（纯对数交互，无地板）

- 可用 quartet：54；可定义：53（占比 0.9815）
- 原因码计数：{'DEFINED': 53, 'ZERO_TTC': 1}
- 均值 I_log：-0.0813
- pure I_log; undefined on TTC=0 / censored(+inf) / missing; no floor applied

## 4. 技术门槛（G-gates，真实数据测量）

| 门槛 | 状态 | 关键量 |
|---|---|---|
| G1_determinism | PASS_BY_COMPOSITION | `{"evidence": "V01 real same-seed replay matched bitwise; V02 scenarios and seeds are SHA-256 derived (unit-tested). No extra episodes spent on a replay."}` |
| G2_intervention | PASS | `{"n_bounds_violations": 0, "bounds_violations": [], "n_intervention_mismatches": 0, "intervention_mismatches": [], "note": "declared dimensions changed exactly as specified; no clipping anywhere"}` |
| G3a_within_anchor_variance | PASS | `{"mean_within_anchor_variance_s2": 0.09166663250698943, "n_anchors_with_reps": 18}` |
| G4_perturbation_effective | PASS | `{"varying_groups": 18, "bitwise_identical_groups": 0}` |
| G6_simulator_stability | PASS | `{"errored": 0, "interrupted": 0, "errors_by_type": {}, "n_unexplained": 0, "note": "the only error was the D37 archive-serialisation defect in the newly written V02 runner, which was fixed and regression-tested before the pilot; it is not simulator instability and no episode was re-run"}` |
| G3b_binary_events | PASS | `{"events": {"00": 1, "10": 1, "01": 0, "11": 0}, "note": "0 events => the binary endpoint supports no rate claim (rule of three not applied: its iid assumption does not hold here)"}` |
| G10_missingness | PASS | `{"n_quartets": 54, "n_unusable": 0, "unusable_share": 0.0}` |
| metric_equivalence | PASS | `{"n_episodes_checked": 240, "n_over_tolerance": 0, "tolerance_s": 0.0001, "max_abs_delta_s": 8.290877133346323e-06, "worst_case": {"file": "v02-anchor-0012_rep0_10.json", "derived": 0.0, "upstream": 8.290877133346323e-06, "abs_delta_s": 8.290877133346323e-06}, "note": "derived per-step minimum reproduces the simulator's own min_forward_ttc_sampled_s; residual is 9-dp trajectory rounding + vx=speed*cos(heading) reconstruction, far below the 0.05 s effect scale"}` |

## 5. 辅助：两方法提名质量（独立审计，探索性）

| method | 提名数 | 提名 anchor | 可用审计 quartet | 反转命中 | precision@k |
|---|---:|---|---:|---:|---:|
| WideExplore | 3 | v02-anchor-0008;v02-anchor-0003;v02-anchor-0012 | 3 | 1 | 0.3333 |
| VerifyFirst | 3 | v02-anchor-0014;v02-anchor-0012;v02-anchor-0009 | 3 | 3 | 1.0000 |

- 该对比为**辅助/探索性**：预算极小（每方法 3 个提名、各 1 个全新审计 quartet），
  且**不作为主结论**；`precision@k` 只在已审计的提名集内定义。
- 预算等量：两方法从**同一份 discovery 数据**提名，差异只在分配规则。

## 6. 图表

- figure_1_condition_ttc：`D:\SafeFlipLab\v02\reports\pilot\figure_1_condition_ttc.png`
- figure_2_anchor_contrast_forest：`D:\SafeFlipLab\v02\reports\pilot\figure_2_anchor_contrast_forest.png`
- figure_3_within_anchor_variation：`D:\SafeFlipLab\v02\reports\pilot\figure_3_within_anchor_variation.png`
- figure_4_per_anchor_delta_both：`D:\SafeFlipLab\v02\reports\pilot\figure_4_per_anchor_delta_both.png`

## 7. 边界声明

- 全部数字来自真实 HighwayEnv 记录；V02 为 **dev 主种子**，不是正式评估。
- 独立单元是 **anchor**，不是 episode；不得把 4 条件 episode 当独立样本。
- 无 p 值、无显著性宣称：抽样假设未证明，确证性检验保持 PENDING。
- 0 次碰撞不构成碰撞率上界（rule of three 的 iid 前提不成立）。
- 本设计受 V01 pilot 探索结果启发（事后性），已在 DECISION_LOG 显式披露。
