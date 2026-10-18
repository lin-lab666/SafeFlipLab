# AUTONOMOUS_DECISIONS — 自主执行决策日志（V02，D28–D40）

> 本文件记录 V02 阶段**由项目负责人在授权范围内自主做出的**技术/科研决策，含理由与局限。
> **V01 的 D1–D27 见 `docs/DECISION_LOG.md`，未被本文件修改或追认。**
> V01 未批准的 D4/D5/D6 **不因本文件而获得批准**。
> 结论只依据真实证据；不以是否出现正结果为选择标准。

---

## D28. 总体路线：为 V02 立新协议，而不是追认 V01 的 D4/D5/D6

- **背景**：V01 的独立评审结论为「工程 GO / 协议 CONDITIONAL GO / 科研对 formal **NO-GO**」，
  根因是主指标（二元碰撞）零方差、两方法提名退化、repetition 不重采样 ego–lead 交互。
- **决策**：**不启动 V01 formal（12,800）**；按用户授权，以**全新 protocol id `SafeFlipLab-v02`**
  + 全新决策编号（D28+）设计并冻结一套独立协议。
- **理由**：V01 的缺陷是**设计层**的（终点选错 + 种子语义不足），不是可通过参数调整解决的实现问题；
  在 V01 上跑 12,800 次只会以更高成本复现零信息结果。
- **局限**：这是一次**数据依赖的设计变更**（受 V01 pilot 启发），已在 D36 显式披露并给出控制措施。

## D29. 主终点改为连续「最小前向 TTC」（M1）

- **决策**：V02 唯一主终点 = 每个 episode 的最小前向 TTC（秒），语义完全沿用上游
  `cornercaselab.metrics.longitudinal_ttc`。
- **理由**：
  1. V01 实测 264 个真实 episode **零碰撞** ⇒ 二元终点方差为 0，不可能产出方法或条件结论；
  2. 同一批数据里 TTC/reward/轨迹**都有**条件差异（V01 审计 66/66），说明干预确实改变了过程；
  3. TTC 是上游**冻结**指标，非本项目自造，事后选择风险最低。
- **局限**：TTC 是 **5 Hz 采样、常速假设、仅纵向**的诊断代理量，**不是碰撞概率**。
  报告中不得表述为碰撞风险。

## D30. 二元碰撞降为次要，且**只作描述性计数**

- **决策**：`ego_collision` 保留为次要终点，但**不套用 rule of three**、不给碰撞率上界。
- **理由**：rule of three 要求 iid Bernoulli；本设计中锚由确定性流生成、四条件共享配对种子、
  同锚 repetition 相关 ⇒ 独立性前提不成立。V01 评审 R1 已明确撤回该用法。
- **局限**：若事件数为 0，则二元端点在本次 pilot 中**不提供任何推断**，这本身要如实写进报告。

## D31. 扰动**纯场景层**实现，复用上游 `evaluate()`，不改物理语义

- **决策**：V02 锚内扰动只改**初始场景字段**（`front_gap` / `front_speed` / `ego_speed`），
  仍调用未修改的 `cornercaselab.simulator.evaluate()`；不重写仿真循环、不改控制器、不改策略。
- **理由**：
  1. 「不得改变模拟器物理语义」是硬约束；
  2. 上游 `ParameterisedMerge._make_vehicles` 把 lead 的 `speed` 与 `target_speed` 都设为
     `front_speed`，因此**不可能**通过公开 schema 让 lead「初速 ≠ 目标速」；若强行实现 P1 的
     原始定义，就必须自写环境子类 ⇒ 违反上述约束且显著提高不可比风险；
  3. 场景层扰动同样能达到 V02 的核心目的（让不同 repetition 落在不同 ego–lead 几何上）。
- **局限**：因此 V02 **未实现**提案中的 P3（lead 主动减速事件），也**未**实现「lead 初速 ≠ 目标速」。
  这是相对提案的**范围收窄**，已在 D33 与报告中披露。后果之一是碰撞事件仍然稀少
  （pilot 中仅少数），二元端点依然弱。

## D32. 度量实现采用「轨迹重算 + 与上游对拍」并给出量化容差

- **决策**：逐 policy step 的 `(has_candidate, gap, closing)` 由上游返回的 `trajectory` 重算
  （语义严格镜像 `longitudinal_ttc`：前方 + 横向重叠 ≤ 2.0 m、扣 5 m 车长、`gap/closing`）；
  并与上游自带的 `min_forward_ttc_sampled_s` **逐 episode 对拍**。
- **实测**：smoke 23 个可用 episode **全部在容差内**，**最大绝对差 4.40e-6 s**。
- **容差取 1e-4 s**：比协议关心的最小效应（`δ_eq = 0.05 s`）小 3 个数量级，
  再小 2 个数量级。
- **残差来源**：上游 trajectory 把位置/速度/朝角**四舍五入到 9 位小数**，且 `vx` 由
  `speed·cos(heading)` 重建。这是数值精度，不是语义差异（若是语义差异，误差会是数量级级别）。
- **局限**：该对拍是**等价性证据**，不能证明「TTC 本身是好的安全指标」。

## D33. 锚域收窄到「接近式」区间（ego 明显快于 lead）

- **决策**：V02 锚域 `ego_speed [23,30]`、`front_gap [21,40]`、`front_speed [17,21]`，
  其余三维沿用上游全界；并对扰动极端角点做合法性预检，**永不裁剪**。
- **理由**：V01 的零碰撞部分源于「lead 在自由流、ego 被控制器维持在安全间距」，
  需要把场景放到 **ego 主动接近 lead** 的区间，干预才有可测量的作用面。
- **局限**：这是**有意的域收窄**，结论**只能**在此域内成立，不得外推到上游全界。

## D34. 两方法提名规则（V02，连续终点版）

- **决策**：
  - **WideExplore**：只用每个锚的**第 0 个 repetition**（广度），按 `delta_both` **升序**
    （最负者优先 = 最像反转），tie-break `(first_seen, anchor_id)`。
  - **VerifyFirst**：用该锚**全部已验证 repetition** 的锚级均值，按 `delta_both` 升序，
    再按**可用 quartet 数降序**，再 `(first_seen, anchor_id)`。
  - 无可用 quartet 的锚：**不计分、不提名**，不给虚拟 0。
- **理由**：V02 的提名目标与主问题一致（找**反转**锚），因此排序方向必须是「越负越好」，
  而不是 V01 的「越大越好」；`valid_n` 降序保留了 VerifyFirst「先验证再复测」的结构含义。
- **局限**：两方法共用同一份 discovery 数据，差异**只在分配规则**；pilot 的审计预算极小
  （每方法 3 个提名 × 1 个 quartet），`precision@k` 只有 3 个自由度，**仅探索性**。

## D35. 统计推断：锚级 cluster bootstrap；**确证性检验保持 PENDING**

- **决策**：独立单元 = anchor；区间 = 锚级 cluster bootstrap（B=10000、α=0.05、固定分析种子
  20261015）。**sign-flip / max-T 一律不产出 p 值**（抽样假设 A/B/C 未被证明）。
- **理由**：
  1. 锚由确定性 SHA-256 拒绝流生成，**不是**从总体随机抽取 ⇒ 条件 B 不成立；
  2. 四条件是结构性分配，**不可随机重排** ⇒ 条件 A 不成立；
  3. P1–P4 扰动的可交换性**未被证明** ⇒ 条件 C 不成立。
  在未证明时产出 p 值就是把统计有效性建立在未验证假设上。**系统无权自行批准。**
- **代价**：本项目因此**没有任何 p 值、任何显著性宣称**。所有结论以「点估计 + 区间 + 描述性计数」
  表述。这是**有意为之的保守**，不是遗漏。
- **局限**：cluster bootstrap 的区间语义是「对观测到的锚集合做重采样」的变异性，
  在非随机抽样的锚集合上是**描述性**的，不严格是抽样分布。

## D36. 事后性披露与七项控制

- **决策**：在 `docs/V02_PROTOCOL_FROZEN.md` §12 与所有报告中**显式声明**：V02 的设计
  （连续主终点、反转假设、锚内扰动）**整体受 V01 pilot 探索结果启发**。
- **控制**：① V01 数据只作管道验证、永不作为 V02 证据、永不合并；② 冻结文件 + SHA-256 指纹；
  ③ 新协议 id、新主种子、新锚流；④ 反转方向由**机制**推导而非 pilot 符号；
  ⑤ 阈值/域/扰动宽度/统计方法**在 V02 任何真实数据前冻结**；
  ⑥ 报告必须声明事后性；⑦ 不做确证性检验（走纯估计路线）。
- **局限**：披露与冻结**削弱但不能消除**事后选择风险；因此 V02 结论只能定位为
  **探索性/估计性**，不能作为确证性发现。

## D37. 首轮 smoke 崩溃：发现并修复 runner/adapter 契约缺陷（含真实预算代价）

- **事实**：V02 首次 smoke 调用在**第 1 个 episode 已计费、且真实仿真器已执行**之后崩溃。
  根因：新写的 `RealAdapterV02.run_episode` 返回的是**已转换的 `(StepTTCState, value)` 二元组**，
  而 runner 期望的是与 `FakeAdapterV02` 一致的 **`(has_candidate, gap, closing)` 三元组**；
  于是 ① 归档时 `json.dump` 因 `StepTTCState` 不可序列化而写出**截断文件**，
  ② 维度转换在 `try` 之外再次抛错并逃逸，留下**孤儿 launch 行**。
- **处置**：
  1. 修复契约：真实 adapter 统一返回**原始三元组**（`raw_steps_from_trajectory`），
     runner 统一转换（`states_from_raw_steps`）；
  2. **加固 runner**：计费之后的**所有**步骤（含归档与度量后处理）都在同一 `try` 内，
     **无论如何都写 outcome 行** ⇒ 结构上不可能再产生孤儿；
  3. **恢复**：用一次性审计脚本（`.workbuddy/tmp_audit/v02_recover_orphan.py`）为该孤儿
     补写 `exit_status="error"`、`error_type="TruncatedArchiveError (D37)"` 的 outcome 行；
     **未重跑该 episode**（协议禁止补跑已发起尝试），**未删除**截断归档（保留为失败证据）；
  4. **新增回归测试** 4 项：后处理失败不得产生孤儿、launch 与 outcome 行数必须相等、
     断点恢复不得重跑已计费 episode、`billed_tuple_keys` 覆盖。
- **预算代价（如实记账）**：V02 smoke **实际消耗 1 个 episode**，可用余额 23。
  该 episode 的真实仿真**已执行**但观测**不可用**，因此按协议记为 error 并计费。
- **后果**：smoke 的 `v02-anchor-0000 / rep 0` 成为**不完整 quartet**（缺条件 00），
  按协议计入 `PAIR_MISSING` 并从打分中剔除 —— 这**恰好**是一次真实的缺失处理演练。
- **局限**：这是**本项目自身新代码**的缺陷，不是上游或仿真器问题；已如实记录，不掩盖。

## D38. TTC 等价性容差取 1e-4 s

- 见 D32。补充：容差由**残差的成因与量级**确定（9 位小数舍入 + `vx` 重建），
  并由 smoke 23/23 实测（最大 4.40e-6 s）支持；不为了「让检查通过」而事后放宽。

## D39. 命名与证据隔离

- **决策**：V02 的账本、原始记录、报告、配置全部位于 `D:\SafeFlipLab\v02\` 之下
  （`v02/runs/`、`v02/reports/`、`v02/configs/`），与 V01 的 `runs/`、`reports/`、`configs/`
  **物理分离**；V02 使用 21 列 canonical 账本，V01 的 20 列旧账本**只读不动**。
- **理由**：防跨版本混读、防预算串账、防误改历史。
- **局限**：需要在报告中同时呈现两套账本，读者需注意版本归属。

## D40. V02 预算收窄（相对提案的 TP-1/TP-2）

- **事实**：提案的 TP-1 = 288、TP-2 = 576 个真实 episode，**超出本次授权**（smoke ≤24、pilot ≤240）。
- **决策**：**不申请额外预算、不创建 V03**。把 pilot 设计为
  **主研究 18 锚 × 3 repetition × 4 条件 = 216** + **辅助 2 方法 × 3 提名 × 1 审计 quartet = 24**
  = **240（恰好用满）**，并明确把「正式样本量」列为**尚不能确定**（需技术 pilot 估方差后定）。
- **理由**：授权是硬上限；宁可缩小规模并如实声明局限，也不越界。
- **局限**：18 个锚是**很小的独立单元数**；锚级区间很宽、`precision@k` 只有 3 个自由度。
  因此 V02 结果**只能**定位为 **pilot 级、估计性**。

---

## 附：与 V01 决策的关系（防止误读）

| 项 | 状态 |
|---|---|
| V01 D1–D27 | **未修改、未追认、未重写**；仍在 `docs/DECISION_LOG.md` |
| V01 D4 / D5 / D6 | **仍为 PROPOSED，未获批准**；V02 不使用它们，改用 D34 的 V02 规则 |
| V01 `configs/formal_v01.json` | **未修改**（mtime 2026-10-12 12:13） |
| V01 formal 12,800 | **未启动**，CLI 安全门完好 |

## D41. 独立复核（对抗性）与其发现（2026-10-15，零新 episode）

- **决策**：把 V02 交付物交两位**独立复核员**（代码/统计复核 + 科研方法复核）做**对抗性**审查，
  其指令明确要求"找出问题"而非确认无误。复核为只读，未消耗仿真预算。
- **代码/统计复核发现（已全部处置）**：
  1. **MAJOR-1｜审计种子方法标签被硬编码（已修）**：`v02lab/quartet.py` 把 `sim_seed` 的 method
     标签写死为 `"shared"`，导致两方法对**同一 anchor** 的审计使用**完全相同的 `sim_seed` 与场景**
     （轨迹哈希逐位相同）。名义 6 个审计 quartet（24 episodes）中实际只有 **5 次不同模拟**，
     **4 个 episode（16.7%）为重复模拟且各自计费**。
     **处置**：`method` 现在是 `build_repetition` 的**必填参数**并进入种子派生（主研究传 `"Shared"`，
     保持已记录 primary 的可复现性）；新增 2 项回归测试（`test_method_label_enters_the_seed`、
     `test_method_label_is_required`）。**已记录的 pilot 数据无法重跑**（预算用满），
     故**保留原数字并在报告 §4.6 与论文 §4.4 显式披露**该"独立审计"声称当时不成立。
  2. **MINOR-2｜smoke 度量计数口径矛盾（已修）**：smoke manifest 记录的
     `upstream_ttc_mismatches = 4` 是**旧容差（1e-6 s）**口径下的历史计数；
     按冻结容差（1e-4 s）重算为 **0/23 越界**（最大差 4.395e-6 s）。
     **处置**：报告改为**重新计算**的等价性结果并加口径说明，避免同文件自相矛盾。
  3. **INFO-3**：outcome 行不携带 `budget_scope`（设计如此，仅 launch 行携带）——已在文档说明。
  4. **INFO-4**：`i_lin`（线性）包含一个 TTC=0 的 episode，而 `i_log` 将其判为 `ZERO_TTC` 未定义
     ——这是**定义域差异**，非错误；报告并排展示时需注明。
  5. **INFO-5**：smoke 的 6 个 quartet 跨 2 个 `run_id`（D37 崩溃/续跑痕迹）；计费正确，
     但任何按 `run_id` 聚合 quartet 的下游代码需注意。
  6. **INFO-6（有用旁证）**：pilot 中存在 **4 对 `(sim_seed, scenario)` 完全相同的独立计费 episode，
     其 trace 哈希逐位相同** —— 这是 G1 确定性的**经验旁证**（非全量重放）。
- **科研方法复核发现（已全部处置）**：
  1. **F1（MAJOR）锚级符号异质性未披露**：`Δboth` 有 **10/18 个锚为负**；剔除最大 3 个正向锚后
     均值 **+0.0030 → −0.0327**。
     **处置**：`report.py` 新增 `heterogeneity()`（预指定、描述性），报告 §4.3a 与论文 §4.2.1 披露。
  2. **F2（MAJOR）端点分辨率未与效应尺度对齐**：观测效应 0.003–0.033 s、区间半宽 0.05–0.09 s，
     而 1D 常速 TTC 的已知偏差量级约 0.2 s。**处置**：新增报告 §4.3b 与论文 §4.2.2，
     明确"负结果不能与分辨率不足区分"。
  3. **F3（MAJOR）"重复携带独立信息"过强**：G4 只证明**非逐位相同**。
     **处置**：报告 §4.2 结论文本改为"不再逐位相同（从而**可能**携带额外信息）；但重复**不是**
     独立样本，独立单元仍是锚"。
  4. **F4（MAJOR）"已被真实修复并验证"过强**。**处置**：`FINAL_DELIVERY.md` §1 改为"部分修复"，
     并区分两处缺陷。
  5. **F5/F6（预注册诚信）**：论文标题 `Pre-Registered` 改为
     `Protocol-Frozen, Estimation-Only`；`docs/V02_PROTOCOL_FROZEN.md` 增加**时间戳诚实声明**——
     配置（17:04）早于全部数据，但**叙述文档与决策日志（17:24）晚于数据**，
     因此**不构成预注册的时间证据**；本项目**未**做外部预注册。
  6. **F7**：门槛 `G3b` 由"事件**充分性**"改称"事件**非零（阈值 ≥1）**"。
  7. **F8**：明确"零碰撞"仅在**端点方差**意义上被修复；**二元端点仍近乎退化**，
     且**联合干预条件 `11` 一次未撞**。
  8. **F9**：反转判据（"区间严格不含 0"）注明**仅作描述性稳定性检查，不具覆盖语义**。
  9. **F12**：辅助方法对比**共享 anchor-0012**，两个 `precision@k` 不独立——已披露（并入 MAJOR-1）。
  10. **F13**：补报**已注册的次要终点 M2**（`m2_from_raw()`，由既有原始记录重算，**零新 episode**）；
      `NO_CANDIDATE` 剔除敏感性分析**不适用**（216/216 主 episode 均为 `FINITE`）。
  11. **F14**：说明 `FINITE` 记录可能带 `censored=true` 的含义（存在非闭合步，非整体截断）。
  12. **F15**：G3a 明确为**控制条件（00）**的锚内方差。
- **未处置/无法处置**：`gates.metric_equivalence` 容差（1e-4 s）依据 smoke 实测校准，
  时间上晚于 smoke 数据；该参数是**验证阈值而非研究参数**，已在 L15 披露。
- **边界**：复核全程**零新真实 episode**；未启动 formal；未改历史账本；未修改任何既有数据。

## D42. 审计种子方法标签硬编码缺陷（独立复核 MAJOR-1）

- **现象**：`build_repetition` 调用 `sim_seed_for(master_seed, "shared", …)`，method 标签被写死；
  `conditions.sim_seed_for` 的 method 参数成为**死参数**。
- **后果**：两方法对**同一 anchor**（pilot 中的 `v02-anchor-0012`）的审计得到**相同的 `sim_seed`
  与相同场景**，trace 哈希逐位相同 ⇒ 该 anchor 的"独立审计"声称不成立；
  4 个 episode（16.7%）为冗余模拟且各自计费。
- **影响面**：仅限**辅助/探索性**的方法比较；**不影响**主研究（primary 的 method 恒为 `"Shared"`）
  的任何效应量、区间或门槛。
- **处置**：method 改为**必填参数**且进入种子派生；主研究显式传 `"Shared"`（保持已记录 primary 可复现）；
  审计传真实方法名。新增 2 项回归测试。**数据不重跑、不改写，原样保留并披露。**

## D43. 最终科研审计：M2 读取了错误的 episode 集合（缺陷，已修）（2026-10-15，零新 episode）

- **发现方式**：最终收尾审计中，用**不导入 `v02lab.report`** 的独立脚本从账本 + 原始记录重算 M2，
  发现与已发布值不一致（旧值条件均值 `00=0.0222 / 10=0.0175 / 01=0.0105 / 11=0.0150`，
  独立重算为 `00=0.02339 / 10=0.02525 / 01=0.01270 / 11=0.01717`）。
- **根因**：`m2_from_raw()` 通过 `runs/<phase>/*/*.json` **文件名通配**定位 episode，并以
  `(anchor_id, repetition, condition)` 反查——但**主研究流（`discovery`）与辅助审计流（`audit`）
  写出完全同名的 `<anchor_id>_rep<r>_<cond>.json`**。5 个被提名的锚（0003/0008/0009/0012/0014）
  在 `rep0` 的 4 个条件文件与审计文件**同名同键**，而审计文件在排序中**后读**，于是
  **覆盖**了主研究的 M2 值。
- **量化影响**：解析 **240** 条而非 **216** 条 episode；**20 个主键**被审计 episode 覆盖；
  **5/18 个锚**的 `rep0` M2 被替换。**仅影响 M2**（次要终点）：
  M1、门槛、出入 `_ipcs`、图、预算、账本、以及 `metric_equivalence`（逐文件自洽比较，不按键去重）**均不受影响**。
- **实质后果（重要）**：旧版 M2 结论「**M2 与 M1 方向一致**」**不成立**。按更正后的值，
  M2 的「更安全」方向为**负**：`Δspeed`、`Δboth` 为负（一致），但 **`Δgap` 为 `+0.00186`（正）⇒ 与 M1 不一致**；
  `I_lin` 为 `+0.00261`。两者区间**均跨 0**，故**都不构成证据**；该不一致本身是
  **代理量在分辨率极限处的表现**（见报告 §4.3b），**不是**反转证据。
- **处置**：`m2_from_raw()` 改为**以账本 outcome 行的 `raw_path` 为准**（不再通配文件名），
  并新增回归测试 `TestM2DoesNotReadTheAuditStream`（构造同名主/审计文件，
  且**断言审计文件在通配序中位于最后**，从而确定性地复现旧缺陷；旧算法在该夹具下得 `0.0`，
  新实现得 `0.25`）。报告 §4.3c、论文 §4.2.3 已按更正值重写。
- **为何不改数据**：`runs/` 与账本**一行未改**；修正的是**派生阅读逻辑**，属可再现的重新计算，
  且 `report --phase pilot` 幂等重跑即产出更正结果。
- **新增测试计数**：V02 **142 → 143**；V01 保持 **225**。
- **边界**：**零新真实 episode**；未启动 formal；未发布 GitHub；未改历史账本；未创建 V03。

## D44. 最终科研审计的其余核验结论（2026-10-15，零新 episode）

1. **样本量推导自洽（通过）**：`n = ceil((z_{1-α/2} + z_power)² · sd² / MDE²)`，
   α = 0.05（Holm 最坏情况 ⇒ 每对比 0.0125，族大小 4）、power = 0.80；
   锚级 SD（n=18）`Δgap 0.144281 / Δspeed 0.202794 / Δbof 0.106392 / I_lin 0.229079`。
   **n = 18 时最小可检出 MDE = 0.0837 s（最灵敏对比 `Δboth`）**；
   MDE = 0.05 ⇒ **235 锚 / 2820 eps**，MDE = 0.10 ⇒ **59 锚 / 708 eps**（取四对比最大值）。
   **与已发布网格逐格一致**（独立重算）。注意 0.084 s 是**四个对比中最灵敏者**，
   **不是**「所有对比都能检出 0.084 s」——最迟钝者为 `i_lin` 的 0.180 s。
2. **240 ↔ 54 对应关系（通过）**：240 = **216**（`Shared`/`discovery` = 18 锚 × 3 重复 × 4 条件）
   + **24**（`audit` = 2 方法 × 3 提名 × 1 quartet × 4 条件）；216/4 = **54 个主 quartet，全部可用**；
   每锚恰好 3 个；每条件各 54。孤儿 launch = 0。
3. **审计种子复用（已量化，历史数据不独立）**：6 个名义审计 quartet 中，
   `v02-anchor-0012` 被**两方法同时提名**，且因 method 标签被硬编码，其审计**是同一次模拟**
   （`sim_seed = 484391145`，trace 哈希逐位相同）。⇒ **仅 5 次不同模拟；4 个 episode（16.7%）重复计费**。
   **留一敏感性**：剔除共享锚后 **WideExplore `1/3 → 0/2`、VerifyFirst `3/3 → 2/2`**。
   即两方法比较**不独立**，且 WideExplore 的**唯一命中完全依赖该共享模拟**。
   **即使代码已修，历史数据仍不是独立比较**——不得表述为「已修复 ⇒ 可比较」。

## D45. 最终结题决策（P1–P7 一次性关闭）（2026-10-15，零新 episode）

- **授权依据**：负责人《SafeFlipLab 最终闭环自主执行授权》所定原则。**该附件未随消息附带**
  （Downloads 无新文件）；按负责人明确指示，依据消息正文 + 本地
  `FINAL_RESEARCH_AUDIT.zh-CN.md` / `LATEST_HANDOFF.md` / `DECISION_LOG.md` 继续。
- **决策全文与理由**：`docs/FINAL_CLOSURE_DECISIONS.md`。
- **要点**：P1 **MDE=0.10 s 仅为未来样本量规划示例，不构成授权**；P2 **V02 以完整探索性/描述性
  研究结题**；P3 **外部评审=未来可选工作、不阻塞结题**；P4 **拒绝任何新增真实仿真（含方差加强）**；
  P5 **不批准正式主种子（不适用，无 formal）**；P6 **D4/D5/D6 归档、不追认**；
  P7 **M1 为主要描述性终点、M2 为辅助指标，保留 M1/M2 方向不一致证据**。
- **禁止**：以结题决策追认 D4/D5/D6；以 MDE 示例开放预算；改写历史证据；删除 M1/M2 不一致；
  发表/投稿/发布 GitHub。
- **新增证据**：`docs/V12_INDEPENDENT_RECOMPUTE_20261015.txt`（V01+V02 全量独立复算，
  **141 项断言全部通过**，包括 V01 的 4×3 探索性 ΔTTC 裕度）。

## D46. 最终结题验收与归档（2026-10-15，零新 episode）

- **独立复算**：新写 `.workbuddy/tmp_audit/independent_verify_all.py`（**规范位置已提升至 `scripts/independent_verify_all.py`**），**不导入**
  `safefliplab.report` / `margins` / `v02lab.report` / `stats_anchor`，仅从账本 + 原始记录重算。
  结果 **ALL CHECKS PASS**：V01（smoke/pilot 计数、60 个 quartet、4×(method,stream) 的
  碰撞/反转/救援计数、12 个探索性 ΔTTC 裕度）与 V02（主终点 4 对比的点估计与 bootstrap 区间、
  M2 4 对比与条件均值、辅助审计 precision@k、样本量推导网格）**逐位一致**。
- **口径澄清（防止把两种定义混为一谈）**：**primary quartet**（四条件均有已计费 launch，
  不论状态）与 **usable quartet**（四条件均产出可恢复数值）是**两个不同定义**。
  smoke 的 `6 / 5` 正是这一区分的体现（1 个 quartet 含 D37 错误 episode）。
  二者**均**已独立复算通过。
- **缺陷类别扫描**：对 V01+V02 全代码扫描 D43 同类缺陷（按文件名通配枚举 episode、
  按名而非账本 `raw_path` 取数）。**仅 `m2_from_raw` 一处**曾有问题，已在 D43 修复并加回归测试；
  `metric_equivalence` 的逐文件自洽比较**不受影响**（不按键去重）；V01 全部读取点**均**基于账本。
- **归档**：最终交付清单与哈希见 `docs/FINAL_DELIVERY_MANIFEST.md`；
  复现手册见 `docs/REPRODUCTION_MANUAL.zh-CN.md`。

## D47. 交付清单计数自相矛盾（外部审阅发现，已根治）（2026-10-15，零新 episode）

- **发现方式**：外部审阅者对 `docs/FINAL_DELIVERY_MANIFEST.md` 做文字核对，指出
  **同一文档内出现 186 / 187 / 188 三个互相矛盾的文件总数**，且分类表小计（187）与正文所报（188）不符。
  **该意见成立。**
- **根因**：清单中的**文件数与字节数曾是手工维护的正文文本**；结题轮内文件集合持续增长
  （新增结题决策、主张登记、复现手册、验收/复算证据等），而手工数字只在部分位置同步。
  **缺陷类别同 D43**：把本可由事实源推导的数值固化成了文本。
- **影响面**：**仅交付清单的计数/字节数陈述**；不涉及任何科学数据、统计结果、账本或结论。
- **处置（根治而非改数字）**：
  1. 计数与字节数**改为由 `scripts/build_final_manifest.py` 生成**，
     写入 `FINAL_DELIVERY_MANIFEST.md` 的 `GENERATED-COUNTS` 区块 + 独立的
     `docs/FINAL_ARTIFACT_COUNTS.md`；
  2. 新增 **`--check` 校验模式**（EXIT≠0 即失败），校验**每一处**「N 个文件 / N 字节」声明、
     **分类表算术合计**、以及**关键哈希表**每行（含"幽灵条目"检测）；
  3. 清除 `AUTONOMOUS_PROGRESS.md` / `FINAL_DELIVERY.md` / `LATEST_HANDOFF.md` 中写死的「187 个文件」，
     改为指向 CSV。
- **校验强度**：做了 **4 项注入式反向控制**（改合计、改分类、改哈希、加幽灵文件），
  **全部被正确检出（EXIT 1）**——证明该校验是**会真正失败的闸门**，不是形式化绿灯。
- **写入本决策时的权威值（快照）**：**188 个文件 / 3,173,651 字节 / 14 个类别**；
  `--check` → `PASS (files=188, …, categories=14, key_hash_rows=7)`。
  ⚠️ **该数字是写入时的快照**：本文件（D47）与 `MANIFEST_COUNT_RECONCILIATION.md` 自身也是交付物，
  新增后计数会变（例如随后变为 189）。**判据永远是 `--check` 返回 PASS，不是任何固定字面量。**
- **记录**：`docs/MANIFEST_COUNT_RECONCILIATION.md`。
- **边界**：零新增真实仿真；未改任何历史账本行、原始记录或冻结配置；未启动 formal。

## D48. 结题执行发现并修复：锁文件打开失败逃逸为未捕获异常（2026-10-16，零新 episode）

- **发现方式**：结题轮首次运行 V01 全量测试时出现 **1 项真实失败**：
  `test_cap_one_legacy_ledger` 期望 6 个并发子进程产出 5 个 `REFUSED`，实测只有 **4** 个，
  第 6 个输出为**空字符串**（进程未打印任何内容）。
- **诊断**：worker 只捕获 `BudgetExhausted / DuplicateLaunch / LedgerFormatError / LedgerLockTimeout`；
  空输出意味着**未捕获异常**。定位到 `safefliplab/ledger.py::_exclusive_file_lock`：
  **锁边车文件（`.lock`）的 `os.open` 与父目录 `mkdir` 位于重试/超时机制之外**，
  而 Windows 上另一进程并发创建/删除同一边车文件时会瞬时抛出共享冲突（`PermissionError`）。
- **复现（确定性）**：monkeypatch `os.open` 使前两次对 `.lock` 的调用抛 `PermissionError`
  ⇒ 旧实现**直接把 `PermissionError` 抛出**，进程崩溃、无 stdout。
- **性质判定**：**产品缺陷（跨进程健壮性）**，非测试缺陷。与科学结果无关，
  但会使并发计费场景下的 worker **静默死亡**。
- **修复**：用**单一 deadline** 覆盖「建父目录 + 打开/创建边车 + 取字节范围锁」全过程；
  打开阶段的瞬时 `OSError` **重试**；持续失败则抛 **`LedgerLockTimeout`**（调用方已处理，
  不再逃逸为未捕获异常）。**未改变**任何计费语义、锁定语义或数据格式。
- **回归测试（2 项，已证明可失败）**：`tests/test_ledger_safety.py::TestLockFileOpenIsRetried`
  - `test_transient_open_failure_is_retried_then_succeeds`（瞬时失败 → 重试后成功）
  - `test_persistent_open_failure_raises_lock_timeout_not_permissionerror`（持续失败 → `LedgerLockTimeout`）
  - **反向控制**：将 `ledger.py` 临时回退为旧形态后，两项**均以 `PermissionError` 失败**；
    恢复修复后**均通过**。⇒ 该回归测试**确实能捕获**此缺陷。
- **测试计数**：V01 **225 → 227**（+2）。
- **测试可诊断性增强（不削弱断言）**：`tests/test_ledger_legacy_acceptance.py` 的
  `_run()` 现同时保留每个 worker 的**返回码与 stderr 尾部**，失败信息由 `_explain()` 输出，
  使"空输出"类失败**可被直接诊断**，而非留下一个无法解释的 `""`。
  断言强度**未改变**（仍要求恰好 1 个 OK、5 个 REFUSED）。
- **边界**：零新增真实仿真；未改任何账本行、原始记录或冻结配置；未启动 formal。

## D49. 第六轮：结题验收独立复核（2026-10-17，零新 episode，无缺陷、无修复）

- **执行方式**：工程执行 AI（成员 A）在项目外审计目录 `D:\SafeFlipLab_AUDIT_2026-10-17\round1\`
  独立执行；隔离副本 `isolated_round1/`（`shutil.copytree`，排除 `.venv`/`__pycache__`/`*.pyc`）。
  **所有可能写文件的命令均在隔离副本运行**；项目内仅运行经验证只读的命令
  （两套 doctor、`build_final_manifest.py --check`、账本只读统计）。
- **复算器的运行位置判定**：`scripts/independent_verify_all.py` 尾部会**写**
  `docs/V12_INDEPENDENT_RECOMPUTE_20261015.txt`，且 `ROOT` 硬编码 `D:\SafeFlipLab`；
  若在项目根运行会构成未授权写入。⇒ 在隔离副本内将其 `ROOT` 一行改为副本路径后运行
  （**仅改副本**；项目内脚本一字未动；原始副本留证于 `round1/DIFFS/independent_verify_all.py.orig`）。
- **验收结果（全部一次通过，实际输出）**：
  1. 独立复算：**ALL CHECKS PASS**，**141 项断言**、0 MISMATCH、EXIT 0；
  2. 清单闸门：`--check` → **PASS**（files=200, bytes=3331986, categories=15, key_hash_rows=13），EXIT 0；
  3. doctor：**V01 17/17 GO；V02 7/7 GO**（零 episode），EXIT 0；
  4. 测试：**V01 Ran 227, OK**（45.4 s）；**V02 Ran 143, OK**（1.9 s）；EXIT 0
     （venv 无 pytest，按任务书改用 `unittest discover`；**未修改任何测试**）；
  5. 幂等性：4 条 `report --phase` × 2 轮，**58/58** 产物同位置重跑**逐字节一致**；
  6. 账本复核：V01 活动 528 行（264+264 全 completed）、作废备份 488 行（smoke 24 + pilot 220）、
     V02 smoke 48（23 completed + 1 error=D37）/ pilot 480（240 completed）；
     **有效 528、历史发起 748 = 磁盘 JSON 748**（磁盘数仅取自账本 outcome 行 `raw_path` 列）；
     孤儿 0、重复 key 0、双向 1:1。
- **「无缺陷」判定（决策）**：6 项验收**无一项失败** ⇒ 任务书第四节的诊断/修复流程**未被触发**；
  因此**不新增**任何代码/脚本/文档修复、回归测试或 diff。该判定本身即本轮决策。
- **记录一项非缺陷观察（防止误判）**：8 个报告产物（4×`<phase>_summary.json`、4×`<phase>_report.md`）
  嵌入自身输出路径的**绝对路径**；故**跨目录**的原始字节比对必然出现前缀差异
  （项目 `D:\SafeFlipLab\` vs 副本 `...\isolated_round1\`）。同位置重跑（权威判据）不受影响。
  **不**据此修改报告生成逻辑——历史文档「内容应逐字节相同」的表述以同位置重放为前提，成立。
- **历史计数核验**：V01 227 / V02 143 / 141 断言 / 528 行 / 748 JSON / 作废 220（备份总 launch 244
  的口径差异）/ doctor 17+7 —— **全部与本轮实测一致**。历轮清单文件总数快照（198/199/200）
  随时间增长属预期；**判据永远是 `--check` 返回 PASS**，不是任何固定字面量。
- **边界**：零新增真实仿真；未启动 formal/smoke/pilot；未改历史账本任何一行、原始数据、
  `configs/formal_v01.json`、`v02/configs/v02_frozen_v1.json`；未发布。V01 formal 保持**永久 NO-GO**；
  V02 保持**探索性/描述性研究已结题**；M1/M2 在 `Δgap` 上方向不一致**保留并公开**；
  不产出 p 值、不作显著性声明；MDE=0.10 s 仅为样本量规划示例。

## D50. 返工轮：修复 B-01（终态字节数两处失真）并处理 OBS-1（V01 测试计数陈旧值）（2026-10-17，零新 episode）

- **背景**：成员 B 独立审核（证据 `round2/AUDIT_REPORT.md`）确认 round1 六项验收**全部被独立复现通过**，
  但开具 **B-01（MINOR FAIL）**：两份交付文书中的 manifest 终态字节数与命令实际输出不符
  （`round1/REPORT.md` L15/L44 写 `3351248`，实际 `3351475`，偏差 **227 字节**；
  `docs/LATEST_HANDOFF.md` L17 写终态 `3351355`，偏差 **120 字节**）。
  实际值铁证：A 自己的 `round1/logs/step5_manifest_check_final.txt` 与 `step5_manifest_regenerate.txt`
  （`files=201, bytes=3351475`）——这两个失真数字**从不是任何命令的输出**，属誊写错误。
  B-02 已被 B 以 mtime 实证自行撤销（A 的 49 文件再生分解正确）。
- **B-01 修复**：
  ① `round1/REPORT.md` L15/L44：以**可见更正记录**修正（原值、正确值、出处全部保留，不静默涂改）；
  ② `docs/LATEST_HANDOFF.md` L17：按返工单允许的选项改为**不可过期表述**
     （判据为 `--check` **PASS / EXIT 0**；files/bytes/categories/key_hash_rows 一律以
     `docs/FINAL_ARTIFACT_COUNTS.md` 生成块为准）。
- **根因（与 D47 同类）**：**手工固化派生数值**。对策：交付文档中的派生计数一律脚本生成，
  或改为"以生成块为准"的不可过期表述；终态数字只从事后 `--check` **实际输出**抄录。
- **OBS-1 处理（总控裁定本轮一并处理）**：全库 grep `225` 共 **36 处**命中，逐处判定
  （证据 `rework_r1/logs/grep_225_full.txt`；权威值 `docs/V13_FINAL_V01_TESTS_20261016.txt` = 227）：
  - **授权内修正 4 处**（均为无日期限定的现行主张）：
    `docs/REPRODUCTION_MANUAL.zh-CN.md` L56/L57（→ 227）；
    `docs/FINAL_DELIVERY_MANIFEST.md` L162（§7 自检表 → 227）；
    `docs/FINAL_DELIVERY_MANIFEST.md` L76（描述 V12 证据文件行 → 加"2026-10-15 快照；
    现行权威 227 / 143 见 V13"限定；V12 文件内容如实保留 225，**不篡改历史证据**）。
  - **授权外陈旧现行值 4 处，只记录不修改**（文件不在本轮授权写入清单，待总控裁定，见返工报告 OBS-4）：
    `docs/OWNER_GUIDE.zh-CN.md` L96、`docs/LITERATURE_DIFFERENCE_TABLE.zh-CN.md` L43、
    `docs/FINAL_RESEARCH_AUDIT.zh-CN.md` L207（与同文件 L26 的 227 **自相矛盾**）、
    `docs/FINAL_DELIVERY.md` L50。
  - **历史留痕 / 已正确 28 处一律未改**：带日期或证据引用的历轮记录与原始测试输出
    （ACCEPTANCE_CHECKLIST L155/L163、AUDIT_V01_V02 L16/L29、本文件 L255/L356
    ——L356 正是记录 225→227 变更本身的条目、AUTONOMOUS_PROGRESS 旧轮次 L14/17/111/172/195/215、
    FINAL_CLOSEOUT_20261016 L165、LATEST_HANDOFF L41/L92/L113/L140/L210、PROGRESS.md L14/40/167/171、
    V09/V11/V12_FINAL_V01_TESTS_20261015.txt 原始输出、FINAL_DELIVERY L187【已有"当时口径"限定】
    /L238【已为 227】、FINAL_RESEARCH_AUDIT L26【已为 227】）。
- **另记录一项新发现（不在本轮授权编辑范围，见返工报告 OBS-5）**：
  `docs/REPRODUCTION_MANUAL.zh-CN.md` L78 的 `categories=14` 为陈旧值（现行 **15**；
  `script` 类于第五轮补入清单）。本轮对该文件仅授权 OBS-1 类修正，故未改，待总控裁定。
- **编辑顺序纪律**：先完成全部文档内容编辑 → 重生成 manifest → 从 `--check` **实际输出**
  读取终态数字 → 终态数字只写入审计目录（`round1/REPORT.md` 更正记录），
  **不手写进任何项目文档**（避免再次被 manifest 覆盖/漂移）。
- **边界**：零新增真实仿真；未启动 formal/smoke/pilot；未改历史账本任何一行、原始数据、
  `configs/formal_v01.json`、`v02/configs/v02_frozen_v1.json`；未发布；未创建 V03。
  V01 formal 保持**永久 NO-GO**；V02 保持**探索性/描述性研究已结题**；
  M1/M2 在 `Δgap` 上方向不一致**保留并公开**；不产出 p 值、不作显著性声明；
  MDE=0.10 s 仅为样本量规划示例。

## D51. 返工轮 2：按总控扩展授权修复 OBS-4 与 OBS-5（陈旧派生数值）（2026-10-17，零新 episode）

- **背景**：rework_r1 曾记录 **OBS-4**（授权清单外 4 处陈旧 V01 测试计数"225"）与
  **OBS-5**（`docs/REPRODUCTION_MANUAL.zh-CN.md` L78 `categories=14` 陈旧）待总控裁定；
  总控本轮**扩展授权**修复（B-01 修复方案已裁定合格；成员 B 将在暂停写入后做最终独立复验）。
- **OBS-4 逐处处置**（权威值 227，见 `docs/V13_FINAL_V01_TESTS_20261016.txt`）：
  ① `docs/OWNER_GUIDE.zh-CN.md` L96（§4 目录描述，无日期限定的现行主张）
     → **改数 225→227**；
  ② `docs/LITERATURE_DIFFERENCE_TABLE.zh-CN.md` L43（要素对比表现行描述）
     → **改数 225→227**；
  ③ `docs/FINAL_RESEARCH_AUDIT.zh-CN.md` L207（"测试数变化说明"，该轮历史快照；
     与同文件 §1.7 上表的 227 **自相矛盾**）→ **加限定语**：
     "（该轮当时口径；结题执行后为 **227**，见 §1.7 上表与 D48）"——保留历史事实、消除矛盾；
  ④ `docs/FINAL_DELIVERY.md` L50（§3.2"V01（只读复核，未重跑）"，2026-10-15 交付轮快照，
     文件头已注明交付日期）→ **加限定语**："（当时口径；结题执行后为 **227**，见 D48）"。
- **OBS-5 处置**：`docs/REPRODUCTION_MANUAL.zh-CN.md` L78 `categories=14` → **15**
  （以最后 `--check` 实际输出为准：categories=15；`script` 类于第五轮补入清单）。
- **修正方式判定规则**（总控返工单）：只修现行主张处的陈旧派生数值；历史留痕一律不得改写；
  语境为历史快照描述处**加限定语而非改数**（以实际语境逐处判定，理由见 rework_r2 报告）。
- **未触碰**：`docs/DECISION_LOG.md`、`docs/V12_*.txt`、`docs/V13_*.txt`、`docs/PROGRESS.md`、
  `docs/AUTONOMOUS_MASTER_PLAN.md` 等历史记录，以及一切记载"225→227"变更史的条目。
- **边界**：零新增真实仿真；未启动 formal/smoke/pilot；未改历史账本任何一行、原始数据、
  `configs/formal_v01.json`、`v02/configs/v02_frozen_v1.json`；未改任何代码/测试/
  `scripts/**`/`reports/**`/`v02/reports/**`；未发布；未创建 V03。
  V01 formal 保持**永久 NO-GO**；V02 保持**探索性/描述性研究已结题**；
  M1/M2 在 `Δgap` 上方向不一致**保留并公开**；不产出 p 值、不作显著性声明；
  MDE=0.10 s 仅为样本量规划示例。
