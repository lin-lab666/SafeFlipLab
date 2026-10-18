# SafeFlipLab｜pilot 阶段中文报告（真实数据）

> 本文件描述 **真实发生**的 smoke 与 pilot：实际命令、真实账本计数、真实结果、负结果、
> 错误与局限，以及下一步建议。
> 权威数据源：`runs/episode_ledger.csv`、`runs/<run_id>/*.json`、`reports/*`。
> **本报告中的一切数字均来自真实 HighwayEnv 仿真，dev_seed 结果不是正式证据，不得外推。**
>
> 生成日期：2026-10-15（GMT+8）。本轮**零新真实 episode**，仅重新聚合既有真实记录。

---

## 1. 实际运行过的命令

| 阶段 | 命令 | 退出码 | 说明 |
|---|---|---|---|
| smoke | `python -m safefliplab smoke --max-episodes 24` | 0 | 24 次真实 episode，用满上限 |
| pilot | `python -m safefliplab pilot --max-episodes 240` | 0 | 240 次真实 episode，用满上限（阶段隔离 bug 修复后重跑） |
| 报告 | `python -m safefliplab report --phase smoke` / `--phase pilot` | 0 | 仅读取账本，**零 episode** |

仿真契约（冻结）：`policy=boundary`、25 s 时域、15 Hz 仿真 / 5 Hz 策略、`merge-scenario-v1` 六维场景。

---

## 2. 真实预算账

| 阶段 | 上限 | 已发起 | 完成 | 错误 | 中断 | UNKNOWN | 未用 slots |
|---|---:|---:|---:|---:|---:|---:|---:|
| smoke | 24 | **24** | 24 | 0 | 0 | 0 | 0 |
| pilot | 240 | **240** | 240 | 0 | 0 | 0 | 0 |
| formal | 12800 | **0** | 0 | 0 | 0 | 0 | 12800（未授权） |

- 已发起 = 已计费；**失败/中断/未知同样计费**，无免费重试。
- 首次 pilot 曾因**阶段隔离 bug**（D11）只发起 220 个 episode，该次运行已作废，
  隔离保存于 `runs/_buggy_pilot_run1/` 与 `runs/episode_ledger.csv.buggy_pilot_run1`，**不计入有效证据**。
- 累计视角（含已披露作废运行）：smoke 24 + pilot 一次 220 + pilot 一次 240 = 484 次真实已发起尝试。

---

## 3. 真实结果

### 3.1 smoke（24 episodes / 5 个完整 quartet + 1 个重放）

| 项 | 值 |
|---|---|
| 完整主 quartet | 5（WideExplore discovery 3 + VerifyFirst discovery 2） |
| 重放 quartet（非独立证据） | 1 |
| 不完整 quartet | 0 |
| 确定性重放 | `all_conditions_match = true`（四条件 trace SHA-256 完全一致） |
| 碰撞 | 全部 `ego_collision = 0`，`termination = goal` |

### 3.2 pilot（240 episodes / 60 个完整 quartet）

| method / stream | quartets | mean delta_both | mean delta_gap | mean delta_speed | mean interaction | reverse | rescue |
|---|---:|---:|---:|---:|---:|---:|---:|
| WideExplore / discovery | 15 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 |
| WideExplore / audit | 15 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 |
| VerifyFirst / discovery | 15 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 |
| VerifyFirst / audit | 15 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 |

- 四种条件碰撞计数：**全为 0**（分母 60）；`reverse_pairs = 0`、`rescue_pairs = 0`。
- 提名（真实）：两方法均提名 `anchor-0000/0001/0002`（pilot 缩小版为 3 个提名而非正式 5 个）。
- 方法对比（`reports/pilot_comparisons.csv`）：`contrast_verify_minus_wide = 0.0`，
  且 `meets_formal_anchor_requirement = 0`（3 个审计锚 < 正式要求的 5 个）。

---

## 4. 负结果与不理想情况（如实报告）

1. **零碰撞**：264 个真实 episode **无一发生本车碰撞**。因此二元主指标 `delta_both` 及其分解
   在本次样本下**全部为 0**，`interaction` 为 0，`reverse` / `rescue` 均为 0。
   → **未观察到任何方向的风险反转**，也**未观察到 rescue**。这是明确写入的负结果，不做任何美化。
2. **两方法不可区分**：由于主指标恒为 0，WideExplore 与 VerifyFirst 的提名完全退化为 tie-break，
   `VerifyFirst − WideExplore` 对比为 0。**该样本无法回答“谁更强”**。
3. **首次 pilot 作废**：220 个 episode 因阶段隔离 bug 无效，属于真实发生的事故，已披露并保留证据。
4. **无错误、无中断**：两次有效运行均 0 error / 0 interrupted / 0 unknown。这是好的工程结果，
   但**不代表**正式规模下不会出现（正式规模的失败处理已单测覆盖）。

---

## 5. 探索性连续安全裕度分析（**非协议指标**）

零新 episode，仅重读已付费产生的原始记录，提取 `min_forward_ttc_sampled_s` 的配对差：

| method / stream | quartets | mean ΔTTC(both) | mean ΔTTC(gap) | mean ΔTTC(speed) |
|---|---:|---:|---:|---:|
| WideExplore / discovery | 15 | −0.0383 | −0.0441 | +0.0857 |
| WideExplore / audit | 15 | −0.2158 | −0.0805 | −0.0483 |
| VerifyFirst / discovery | 15 | −0.1799 | −0.1003 | −0.0095 |
| VerifyFirst / audit | 15 | −0.2158 | −0.0805 | −0.0483 |

- 四组 `ΔTTC(both)` **均为负**：组合干预（同时增加前车间距、降低自车初速）在连续裕度上一致地
  **降低最小前向 TTC**（更接近碰撞，但未碰撞）。
- **严重限制**：单 `dev_seed`、样本小；且本场景 `sim_seed` 仅随机化 ramp 车的 IDM 指数，
  最小前向 TTC 恒由 lead 车决定且发生在与种子无关的时间窗内 ——
  **同一 (anchor, condition) 的 ΔTTC 在不同 repetition 间逐位相同**，
  即重复种子**不构成**对 TTC 指标的独立重采样。
- ⇒ 该结果**不得**作为正式证据、**不得**称为“稳定反转”、**不得**外推为真实道路安全结论。
  仅作为“二元碰撞指标在此场景下分辨率不足”的**线索**，交由人工裁决是否改用连续终点（见 V02 提案）。

---

## 6. 局限

| # | 局限 |
|---|---|
| 6.1 | 仅 `dev_seed = 20261011`，非正式 8 主种子；结论不得外推 |
| 6.2 | pilot 结构性缩小（15 个 discovery 锚 vs 正式 100；审计锚 3 vs 正式 5；每锚审计 5 vs 正式 20），**不冒充正式统计** |
| 6.3 | 仿真为简化高速汇入 + 规则控制器；**不构成真实道路安全结论**，不声称根因已证明 |
| 6.4 | 二元碰撞指标在本场景分辨率不足（零事件 → 零方差） |
| 6.5 | 连续裕度指标为**确定性闭环属性**，非随机碰撞风险的独立重采样 |
| 6.6 | `sim_seed` 作用域有限（只随机化 ramp nuisance 车） |
| 6.7 | 审计证据强度远低于正式设计（5 个 audit quartet/提名 vs 正式 20） |

---

## 7. 产物清单

```
reports/
  smoke_report.md / pilot_report.md            中文阶段报告（含预算账附录）
  smoke_episodes.csv|jsonl / pilot_episodes.csv|jsonl   每 episode 一行（240 行）
  smoke_anchors.csv / pilot_anchors.csv         每锚 Y 计数/分母/比率/4 差值
  smoke_budget_summary.csv / pilot_budget_summary.csv   预算 cap/launched/unused
  smoke_comparisons.csv / pilot_comparisons.csv 每 master_seed 方法对比（不可计算时留空）
  smoke_quartets.csv / pilot_quartets.csv       完整主 quartet 明细
  smoke_margins.csv / pilot_margins.csv         探索性连续裕度（非协议）
  smoke_summary.json / pilot_summary.json
  smoke/figure_*.png (3)  pilot/figure_*.png (4)
runs/
  episode_ledger.csv                            权威账本（528 数据行）
  <run_id>/*.json                               原始 episode 记录
  _buggy_pilot_run1/                            首次无效 pilot 审计留痕
```

---

## 8. 下一步建议

1. **不建议**在现有 V01 二元主指标下直接启动 formal（零事件 → 零方差，两方法不可区分）。
   详见 `docs/INDEPENDENT_SCIENTIFIC_REVIEW.md` 与 `docs/ACCEPTANCE_CHECKLIST.md` §9.2。
2. 若希望解决分辨率问题，可按 `docs/V02_RESEARCH_PROPOSAL.md` 走**连续主终点 + 锚内扰动**的
   独立设计，但该提案全部为 **PROPOSED**，且其自身有 **B-01…B-12** 阻塞项，需先人工裁决。
3. 若坚持 V01，需先逐项批准 D4/D5/D6 并对 BLOCKER-3 作出裁决，再书面 `GO FORMAL`。
4. 无论哪条路线，正式运行前都应重跑 `doctor`（须 17/17 GO）并确认
   `configs/formal_v01.json` 未被修改。
