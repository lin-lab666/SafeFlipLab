# SafeFlipLab — 主张登记表与局限审计（CLAIMS REGISTER & LIMITATIONS AUDIT）

**日期**：2026-10-15　│　**零新增真实仿真**
**用途**：把中文报告与英文论文中**每一条可核验的主张**与其**证据来源**一一对应，
并集中登记**不得出现**的表述。任何主张若无法在"证据"列找到落点，即为**过度声称**，必须删除或降级。

配套文件：
`docs/FINAL_RESEARCH_AUDIT.zh-CN.md`（审计正文）、
`docs/LITERATURE_DIFFERENCE_TABLE.zh-CN.md`（创新性核查 + 上游协议比较）、
`docs/CORNERCASELAB_OVERLAP_VERIFIED.md`（上游逐项重叠）、
`docs/V12_INDEPENDENT_RECOMPUTE_20261015.txt`（独立复算证据）。

---

## 1. 允许主张（每一条都有可复算落点）

| # | 主张（唯一允许的措辞） | 证据 | 复算方式 |
|---|---|---|---|
| C1 | **V01**：264 次真实 episode（smoke 24 + pilot 240）**全部零碰撞**，主终点零方差 | `runs/episode_ledger.csv`（528 数据行）；`reports/pilot_summary.json` | `independent_verify_all.py` §V01 |
| C2 | **V01**：pilot 的 60 个完整 quartet 的碰撞型对比 `Δgap/Δspeed/Δboth/I_lin` **全部为 0**，`reverse=rescue=0` | 同上 | 同上（4×(method,stream) 全部核对） |
| C3 | **V01**：探索性连续裕度 **ΔTTC 全为负**（−0.038 ~ −0.216 s），但**是确定性属性**（跨 repetition 逐位相同），**不是**随机碰撞风险 | `reports/pilot_summary.json.exploratory_margins`；`reports/pilot_margins.csv` | 同上（12 个 ΔTTC 逐位核对） |
| C4 | **V02**：240 次 pilot = **216**（主：18 锚×3 重复×4 条件）+ **24**（审计：2 方法×3 提名×1 quartet×4 条件）；孤儿 launch **0** | `v02/runs/pilot/episode_ledger.csv` | §V02（ledger 分解） |
| C5 | **V02**：**54 个主 quartet 全部可用**；注意 `n_primary_quartets`(四条件均已计费) 与 `n_usable_quartets`(四条件均有可恢复值) 是**两个不同定义** | 同上 | §V02（两定义分别核对） |
| C6 | **V02 主终点（M1，描述性）**：`Δgap +0.0127`[−0.0525,+0.0769]、`Δspeed +0.0327`[−0.0589,+0.1243]、`Δboth +0.0030`[−0.0436,+0.0526]、`I_lin −0.0424`[−0.1465,+0.0613]；**四个区间全部跨 0** | `v02/reports/pilot_summary.json` | §V02（点估计与 bootstrap 区间逐位） |
| C7 | **未发现安全反转，也未发现可判定的非可加交互** | 由 C6 直接得出（区间全跨 0） | — |
| C8 | **锚级符号高度异质**：`Δboth` 在 **10/18** 锚为负；剔除最大 3 个正向锚后均值 **+0.0030 → −0.0327** | `v02/reports/pilot_anchors.csv` | §V02/`final_research_audit` §C |
| C9 | **端点分辨率不足**：观测效应 0.003–0.033 s、区间半宽 0.05–0.09 s，而 1D 常速 TTC 的已知系统偏差约 0.2 s（TTC≈1 s 处） | 报告 §4.3b；文献 R-01 (Li et al. 2024) | 算术 + 文献 |
| C10 | **M2（辅助指标）**：条件均值 `00 0.02339 / 10 0.02525 / 01 0.01270 / 11 0.01717`；对比 `Δgap +0.00186`、`Δspeed −0.01069`、`Δboth −0.00623`、`I_lin +0.00261`，区间均跨 0 | `v02/reports/pilot_summary.json.m2_secondary` | §V02（M2 4 对比 + 4 条件均值逐位） |
| C11 | **M1 与 M2 在 `Δgap` 上方向相反**（M1 `+0.0127` 为"更安全"方向；M2 `+0.00186` 为"更不安全"方向，因 M2 越小越安全） | C6 + C10 | 符号约定表（§3） |
| C12 | **技术门槛**：G2 干预合法 0 越界；G3a 控制条件锚内方差 **0.0917 s²**（V01 为 0）；G4 **18/18** 锚的 min-TTC 不再逐位相同；度量等价 240/240，最大差 **8.3e-6 s** | `v02/reports/pilot_summary.json.gates` | §V02（G3a 方差、逐位相同计数） |
| C13 | **二元端点近乎无信息**：54 个 quartet 仅 **2 次碰撞**（条件 `00`、`10` 各 1），**`11` 一次未撞**；`reverse=0`、`rescue=1` | `v02/reports/pilot_summary.json.binary_counts` | §V02（碰撞计数逐条件） |
| C14 | **辅助方法比较**：WideExplore `precision@k = 1/3`、VerifyFirst `3/3`；**但**两者共享锚 `0012`（**不独立**），且该锚的审计是**同一次模拟**（`sim_seed=484391145`，trace 逐位相同）⇒ 6 个名义 quartet **只有 5 次不同模拟**、**4 个 episode 重复计费**；**留一后 WideExplore `1/3→0/2`、VerifyFirst `3/3→2/2`** | `v02/reports/pilot_summary.json.auxiliary_method_comparison`；原始 JSON | §V02（precision@k + 重复模拟检测） |
| C15 | **样本量推导（仅规划）**：α=0.05（Holm 最坏 ⇒ 0.0125/对比，族 4）、power=0.80；n=18 最灵敏对比可检出 **0.0837 s**；MDE=0.10 ⇒ **59 锚/708 eps**；MDE=0.05 ⇒ **235 锚/2820 eps** | `v02/reports/pilot_anchors.csv` → `v02lab/power.py` | §V02（网格逐格 + z 值） |
| C16 | **创新性**：所有**组件**均有先例（上游 CornerCaseLab 与公开文献）；可能的差异仅为**三条组合性**要点，且检索**非穷尽** | `LITERATURE_DIFFERENCE_TABLE.zh-CN.md` §1–§2；`CORNERCASELAB_OVERLAP_VERIFIED.md` §6 | 只读文档核验 |
| C17 | **上游重叠（已全文级核验）**：其 `cornercaselab_v03_eval_v1` 已具备配对等预算、独立审计（10×30，不回填）、Wilson ≥21/30、SNY、SHA-256 种子、**成文不报 p 值** | 同上 | 只读文档核验 |
| C18 | **诚实性可引用**：D37（归档失败 1 个 smoke 预算）、D42（审计种子标签硬编码）、D43（M2 读取错误 episode 集合）、F-06（2 个 run_id 标签）**全部保留并披露，未改写数据** | `AUTONOMOUS_DECISIONS.md` D37/D42/D43；`DECISION_LOG.md` D27 | 决策日志 |

---

## 2. 禁止表述（出现即为过度声称，必须删除）

| # | 禁止 | 原因 |
|---|---|---|
| X1 | 任何**真实道路安全**结论（"更安全/更危险"外推到现实） | M1 只是 1D 常速纵向代理量，**不是碰撞概率** |
| X2 | "**显著**"、"**证明**"、"**稳定反转**"、"p < …" | **不产出 p 值**；抽样假设未证 |
| X3 | 把 `rule of three` 用于零/低事件 | iid Bernoulli 前提不成立 |
| X4 | 把 **episode** 或 **repetition** 当独立样本 | 独立单元**只有锚** |
| X5 | 用 **V01 数据**作为 V02 的证据，或两版**合并统计** | 版本隔离不变量 |
| X6 | 声称「**两终点方向一致**」 | **假**：C11 表明 `Δgap` 上方向相反 |
| X7 | 声称「**扰动已使 repetition 相互独立**」 | 只证明**不再逐位相同**；独立单元仍是锚 |
| X8 | 声称「**代码已修 ⇒ 历史数据可独立比较**」 | C14：历史数据**永久**不独立 |
| X9 | 声称「锚级均值代表多数锚」 | C8：`Δboth` 多数为负 |
| X10 | 声称「**未发现效应 = 无效应**」 | C9：分辨率不足无法排除 |
| X11 | 由 `rescue_pairs = 1` 推断"联合干预避免了碰撞" | 单一事件 |
| X12 | 声称**首次/独有/原创** | C16：组件均有先例，检索非穷尽 |
| X13 | 声称已**外部预注册**或**通过外部评审** | 只有配置冻结；外部评审 NOT DONE |
| X14 | 声称 **WideExplore 与 VerifyFirst 孰优** | C14：3 提名 × 1 quartet，且不独立 |
| X15 | 把 **MDE=0.10 s** 说成"已批准"或"目标效应量" | P1：仅规划示例 |
| X16 | 把 V02 说成**确证性**研究 | P2：探索性/描述性 |
| X17 | 声称 D4/D5/D6 已获批准 | P6：归档不追认 |

---

## 3. 符号约定表（唯一权威口径）

| 终点 | 定义 | "更安全"方向 | 观测 |
|---|---|---|---|
| **M1** | 每 episode **最小前向 TTC** | **Δ > 0**（裕度更大） | `Δgap +0.0127`、`Δspeed +0.0327`、`Δboth +0.0030`、`I_lin −0.0424` |
| **M2** | 前向 TTC < 1.0 s 的 **step 占比** | **Δ < 0**（占比更小） | `Δgap +0.00186`、`Δspeed −0.01069`、`Δboth −0.00623`、`I_lin +0.00261` |
| **二元** | `Y = ego_collision ∈ {0,1}` | `reverse = 1{Y00=0, Y11=1}`（联合干预撞了而对照没撞 = 反转） | `reverse 0`、`rescue 1` |
| **辅助审计反转** | `R_a = 1{Δboth_audit < −δ_eq}`，`δ_eq = 0.05 s` | 负 Δ = 裕度被压低 = 反转 | VF `3/3`、WE `1/3` |

统一公式：`Δ = X(处理) − X(对照)`；`Δgap = 10−00`、`Δspeed = 01−00`、`Δboth = 11−00`、
`I_lin = 11−10−01+00`。
**M1 与 M2 的"安全方向"数值符号相反**，**禁止**跨终点直接比较符号。

---

## 4. 局限登记（结题后仍然成立，不得削弱）

见 `docs/FINAL_RESEARCH_AUDIT.zh-CN.md` §2（L1–L18）与
`docs/FINAL_CLOSURE_DECISIONS.md` §2（10 条）。摘要：

**设计**：事后性、无外部预注册｜单一 dev 主种子｜18 个非随机锚｜锚域收窄｜
端点分辨率与效应同量级｜未实现 lead 减速等提案要素｜无 p 值/无 FWER。
**数据**：辅助方法比较永久不独立｜D37 归档事故（1 个 smoke 预算）｜D43 派生阅读缺陷（已修）｜
容差在 smoke 后校准。
**主张**：TTC 非碰撞概率｜仅描述性估计｜检索非穷尽｜未与上游 60,000 ep 正式数据比较。

---

## 5. 结论

> 本登记表所列 **C1–C18** 全部可由**账本 + 原始记录**独立复算
> （`docs/V12_INDEPENDENT_RECOMPUTE_20261015.txt`，**141 项断言全部通过**）。
> **X1–X17** 在任何交付文本中**不得出现**。
> 若未来修订报告或论文，**必须**先回到本表核对新增主张的落点。
