# INDEPENDENT_SCIENTIFIC_REVIEW — SafeFlipLab 正式实验前独立科研评审

> 评审时间：2026-10-13（GMT+8）。评审性质：**独立科研审计**（正式实验前）。
> 本轮约束（用户指定）：禁止启动任何新真实 episode；不运行 smoke / pilot / formal；
> 不修改冻结配置；不清除历史记录。实际执行：**零新 episode**（证据见 §8）。
> 本报告严格区分三类结论：**代码正确性**、**实验协议合规性**、**科研结论有效性**。
> 未经用户书面批准的事项一律标记为待批准，不得视为已决断。

---

## 0.0 复审修订记录（2026-10-13 第二轮，外部复核后）

本轮仅做**统计解释修订**（零新 episode、零代码行为变更），针对外部复核指出的三处问题：

| # | 位置 | 问题 | 修订 |
|---|---|---|---|
| R1 | §2.3 | rule of three 把重复 anchor 的零碰撞观测当作独立 Bernoulli 样本 | 显式否定独立性假设，改按锚层级/分层计数，撤回"<5%"表述 |
| R2 | §2.1–2.2 | VerifyFirst 的 tie-break 与 `valid_n` 排序解释不准（误称 `valid_n` "从未被触发"） | 逐键分解，明确 stage-1 仅 (first_seen, anchor_id) 生效、最终提名首枚有效键为 `valid_n` |
| R3 | §3.3–3.4 | TTC 跨种子确定性结论被过度推广到所有未来 anchor 与碰撞事件 | 限定适用范围，明确不适用于 lead 非自由流、ramp 更早并入、及碰撞事件 |

修订依据为本轮只读复核脚本 `.workbuddy/tmp_audit/rev_data.py`（输出留存
`docs/REVISION_ANALYSIS_20261013.txt`）。修订不改变任何代码、冻结配置、账本或历史数据。

---

## 0. 评审范围与方法

- 只读核验：`runs/episode_ledger.csv`（主账本）、`runs/episode_ledger.csv.buggy_pilot_run1`
  （历史备份）、`runs/_buggy_pilot_run1/`（55 个 run 目录）、484 个原始 episode JSON、
  `runs/manifest_*.json`、`reports/`、`docs/`、`configs/`。
- 源码审计：`safefliplab/` 全包 + 上游公开依赖 `cornercaselab 0.3.0` 与 `highway-env 1.10.2`
  的仿真/指标/策略实现（TTC 语义、IDM 随机化、boundary 控制器）。
- 数据复核：从原始轨迹**重算** TTC 序列，定位最小值时刻/前车/相对速度；跨 repetition
  逐位比对轨迹与 TTC。
- 代码修复（均带回归测试，零真实 episode）：图轴浮点伪差（F-02）、森林图误标（F-03）、
  账本 `budget_scope` 重读丢失（F-01，本轮完成 6 场景独立验收 + 安全拒绝加固）、
  pilot 汇总 manifest 陈旧零值（F-04）、图表长标题溢出（F-05）。
- 全量单测：`python -m unittest discover -s tests -v` → **209 项全部通过**（EXIT 0，47.4 s；
  190 旧 + F-01 验收 15 + 标题换行 4；证据 `docs/V06_TEST_RESULTS_20261013.txt`）。
- `python -m safefliplab doctor` → **17/17 PASS，VERDICT: GO**（改动后复跑；证据
  `docs/DOCTOR_20261013.txt`）。
- F-01 专项独立验收：`docs/F01_LEDGER_ACCEPTANCE_20261013.txt`（仅用临时账本，真实账本只读）。

---

## 1. 预算总账与 PD-01 协议偏离说明

### 1.1 三方对账（账本 / 备份 / 磁盘原始文件）

| 账本 | 数据行 | episodes | 构成 |
|---|---:|---:|---|
| 主账本 `runs/episode_ledger.csv` | 528 | **264** | smoke 24 + 有效 pilot 240 |
| 历史备份 `runs/episode_ledger.csv.buggy_pilot_run1` | 489 | **244** | smoke 24 + 无效 pilot 220（当时整本快照） |
| 磁盘原始 episode JSON | — | **484** | 当前 runs/ 264 + `_buggy_pilot_run1/` 220 |

三方完全吻合：**累计真实发起 484 episodes**；其中有效证据 264（smoke 24 + pilot 240）。
smoke 的 6 个 run 在两本账本中为同一批 run_id（smoke 未重跑；其中 12 个 episode 为
确定性重放，用于跨运行 trace 校验，全部在 24 上限内计费）。

### 1.2 时间线（2026-10-12，GMT+8；来自账本 started/ended_utc 与文件 mtime）

| 事件 | 时间 | episodes |
|---|---|---|
| smoke（有效） | 13:17:03 – 13:17:22 | 24 |
| pilot 第 1 次（后判无效） | 13:32:23 – 13:35:11 | 220 |
| 隔离留痕（备份账本 + 55 run 目录） | 13:44 | — |
| pilot 第 2 次（有效） | 13:45:05 – 13:48:02 | 240 |

### 1.3 PD-01 协议偏离完整说明（不重述为"不存在"）

- **偏离内容**：pilot 阶段累计发起 **460** episodes（220 无效 + 240 有效），
  超过原定 pilot 上限 **240**，偏差 **+220（+91.7%）**。含 smoke 的累计 484 对
  名义 264 同样 +220。
- **成因（D11，已修复）**：`PhaseDriver.completed_quartets()` 未按 phase 过滤，
  pilot 的断点恢复把 smoke 已完成的同键 quartet 误判为"已完成"，跳过
  WideExplore discovery 锚 0/1/2 与 VerifyFirst discovery 锚 0/1，
  第 1 次 pilot 只发起 220/240 且锚覆盖不全 → 该运行**无效**。
- **数据核实（本轮新增证据）**：有效 pilot 的 240 个 (method, stream, anchor,
  repetition, condition) 单元与第 1 次的 220 个**逐一重叠**，独有 20 个恰为当时
  被跳过的锚（WideExplore discovery anchor-0000/0001/0002 与 VerifyFirst
  discovery anchor-0000/0001，各 4 条件）——与 D11 记录精确一致。
- **处置**：无效运行整体移入 `runs/_buggy_pilot_run1/` 与备份账本作审计留痕，
  **不计入科学证据但计入预算消耗**；未删除、未重定义预算、未修改账本历史行。
- **教训与防再发**：D11/D12 相位与主种子隔离修复 + 回归测试；D13–D17 账本原子性、
  跨实例/跨进程锁与锁内磁盘核对；本轮 F-01 进一步保证正式阶段跨进程恢复时
  分作用域预算不丢失（见 §5）。
- **需人工**：接受本偏离及其留痕方式（条件 3）。

### 1.4 附带发现：pilot 汇总 manifest 曾为陈旧零值（F-04，已修复）

- `runs/manifest_pilot_summary.json` 内容为 `episodes_launched=0 / completed=0`，
  而账本为 240/240。根因：该文件由 **D14 修复前**的汇总路径写入（读取编排驱动器
  在子驱动器运行前构建的过期内存视图；现代码 experiments.py:460-463 的注释即描述
  此缺陷），修复后**从未重新生成**。其 `pilot_wall_time_s=177.27` 与有效 pilot
  运行时长（13:45:05–13:48:02 ≈ 177 s）一致，佐证其为有效 pilot 收尾时写入。
- **处置**：以权威账本重新生成该派生文件（240/240/0，保留历史墙钟时间），
  陈旧原件备份为 `runs/manifest_pilot_summary.json.stale_zero_backup`。
  账本本身未被修改。**这是派生工件不同步，不是预算或数据缺陷。**

---

## 2. 算法可比性审计：零碰撞下两方法提名是否退化

### 2.1 提名规则（冻结描述，methods.py）

- 主排序键：`mean delta_both = mean(Y11 − Y00)`（碰撞二元差）。
- WideExplore：`(-delta_both, first_seen, anchor_id)` 取 top-k。
- VerifyFirst：**两段式**——
  - stage-1 选 k（正式 20 / pilot 3）：
    `(-delta_both, -delta_gap, -delta_speed, first_seen, anchor_id)`；
  - 最终提名（正式 top-5 / pilot top-3）：
    `(-mean_delta_both, -valid_n, first_seen, anchor_id)`，`valid_n` = 该锚的完整 quartet 数。

### 2.2 零碰撞下哪些排序键真正起作用（实证，pilot 240 episodes，全部零碰撞）

- **全部 240 个** pilot 完成 episode 的 `ego_collision = 0` ⇒ 每个 anchor 的
  `delta_both = delta_gap = delta_speed = 0`，**三枚单因素/主键全部并列于 0**。

**VerifyFirst 两段式排序逐键分解（R2 修正）**：

| 阶段 | 键序列 | 实际生效的键 | 结果 |
|---|---|---|---|
| stage-1 选 3 | `-delta_both, -delta_gap, -delta_speed, first_seen, anchor_id` | **仅 `(first_seen, anchor_id)`** | 三枚 delta 键对全部 anchor 并列于 0，从不判别；选择完全由锚在流内序号决定 → 选中 `anchor-0000/0001/0002` |
| stage-2 扩样 | — | — | 上述 3 锚各追加 3 个 repetition quartet ⇒ `valid_n = 1 + 3 = 4`；其余 stage-1 锚（0003/0004/0005）保持 `valid_n = 1`（实测） |
| 最终提名 top-3 | `-mean_delta_both, -valid_n, first_seen, anchor_id` | **`-valid_n`（首枚有效判别键）** | `mean_delta_both` 对全部 anchor 并列于 0 ⇒ `valid_n`（4 vs 1）成为第一顺位生效键，恰好选出被 stage-2 提升的 3 个锚 |

- **修正（R2）**：早前稿称"tie-break 链（单因素差、valid_n）**从未被触发**"**不准确**。
  准确表述是：
  1. 三枚 delta 键（`delta_both` / `delta_gap` / `delta_speed`）在所有 anchor 上并列于 0，
     **从不产生判别**——这一点早前稿正确；
  2. `valid_n` **并非"未被触发"**：它是**最终提名阶段第一枚生效的判别键**，把被 stage-2
     提升过的锚（`valid_n=4`）与仅 stage-1 的锚（`valid_n=1`）区分开。
- 因此 VerifyFirst 的"先验证再复测"结构**在 `valid_n` 上确实可见**；但 `valid_n` 是 stage-1
  选择的确定性函数，而 stage-1 又完全由流内序号决定 ⇒ 两方法实际提名的 audit 锚集合
  **完全相同**（`anchor-0000/0001/0002`），方法间不可区分（正式阶段同理：`valid_n=4` vs `1`）。

### 2.3 有效独立单元与"零碰撞"的量级边界（R1：修正 rule of three 的独立性假设）

**常见误用**：由"每条件 60 个 episode 全零"推出"95% 上界 ≈ 3/60 ≈ **5%**"（rule of three）。
该式要求 n 个**独立同分布 Bernoulli(p)** 观测。pilot 数据**不满足**该假设，须分层修正：

- **episode 级不独立**：同一 anchor 的 4 个 repetition 并非对 ego–lead 交互的独立重采样
  （§3.3：`sim_seed` 只随机化 ramp nuisance 车，min-TTC 由 lead 决定且跨 repetition 逐位相同）；
  同一 quartet 内 4 个条件共享同一配对 `sim_seed`，彼此相关。故"60 个 episode"的实际自由度
  远小于 60，**不能直接套用 3/60 ≈ 5%**。
- **anchor 级亦非 iid**：anchor 由 SHA-256 拒绝采样流**确定性**生成，并非从某总体独立抽取；
  同一 anchor 同时进入两个干预臂，锚内条件配对相关。rule of three 的 iid 前提高度可疑。

**分层后的可核验计数（真实账本，本轮脚本复核）**：

| 层级 | 观测单元 | 计数 | 若机械套用 rule of three |
|---|---|---:|---:|
| episode 级（不独立，仅列作参照） | 每条件完成 episode | 60 | ≈ 5% |
| anchor 级（每条件不同锚数，全 pilot 并集） | 不同 anchor | 15 | ≈ 20% |
| 方法×流×条件 | WideExplore discovery | 15 | ≈ 20% |
| 方法×流×条件 | VerifyFirst discovery | 6 | ≈ 50% |
| 方法×流×条件 | WideExplore / VerifyFirst **audit** | **3** | ≈ 100%（无约束力） |

- **修正（R1）**：只能作**描述性**表述——"pilot 60 个完成 episode（15 个不同 anchor）内
  **0 次碰撞观测**"。**不得**宣称"碰撞率大概率低于约 5%"：该 5% 建立在被违反的独立性假设上；
  若强行按锚层级套用，上界退化为 ≈ 20%，而 audit 流仅 3 个锚、几无约束力。
  正式阶段的有效样本量必须按**锚点数**计（而非 episode 数），并显式处理锚内相关
  （见 `docs/V02_RESEARCH_PROPOSAL.md` §8 与 §5）。

### 2.3b 当前数据能支持 / 不能支持的结论

**可以支持（描述性）**：
1. 管道端到端正确：真实 HighwayEnv、确定性种子、干预正确施加（66/66 quartet 干预生效）、
   账本与原始记录一致。
2. anchor 内四条件比较：在**探索性连续量**（TTC/奖励/轨迹）上可观察条件差异
   （见 §3），碰撞二元值全零。
3. 零碰撞的**描述性**计数：pilot 60 个完成 episode / 15 个不同 anchor 内 0 次碰撞观测
   （**不作 rule of three 的"<5%"量级宣称**，理由见 §2.3）。

**不能支持**：
1. **任何 WideExplore vs VerifyFirst 的方法间比较**：提名信号零方差，
   两方法行为不可区分；pilot 对"哪方法更擅长发现风险锚"**零信息量**。
2. 任何"审计流独立复现了风险信号"的结论：被审计锚由 tie-break 选出，不含风险信息。
3. 任何关于碰撞差分的统计推断（零事件、零方差；无可估计区间）。
4. 将 pilot 数字外推为正式结论（dev_seed、单种子、审计 quartet 数 5 ≪ 正式 20）。

---

## 3. `min_forward_ttc_sampled_s` 计算语义审计

### 3.1 上游实现（cornercaselab 0.3.0，公开依赖）

- `metrics.longitudinal_ttc(obs)`：对 observation 中**前方**（`ox > x`）且
  **横向重叠**（`|oy − y| ≤ 2.0 m`）的车，`gap = ox − x − 5.0`（扣 5 m 车长），
  `closing = vx − ovx`；`gap ≤ 0 → 0.0`；`closing > 0 → gap/closing`（常速假设）；
  无候选返回 `None`（**None ≠ 安全**）。
- 采样：`evaluate()` 在 reset 后与**每个 policy step（5 Hz，最多 125 步）**各算一次，
  取最小。是**决策频率采样最小值**，不是连续时间最小值；只算纵向，不算侧撞。
- 本场景 observation 只有 3 辆车（ego / lead / ramp）。

### 3.2 从原始轨迹的实证（重算全部 240 个 pilot episode）

- **最小值对应的前车：240/240 均为 lead（车辆索引 1）**；ramp 从未成为最小值车。
- **最小值出现时刻**：t = 1.2 – 9.2 s（均值 4.9 s；如 anchor-0000 在
  t≈5.4–6.0 s，step 27–30/75）。该时刻 gap ≈ 7.1 – 11.7 m，
  闭合速度 ≈ 7.8 – 8.8 m/s；ego 正在减速（boundary 控制器 TTC 阈值 0.90 s）。
- 重算值与存储值一致（差 ≤ 1.3e-6，来自轨迹 9 位小数舍入与 vx≈speed·cos(heading)
  近似），证实语义理解正确。

### 3.3 为什么不同 repetition 种子下 ΔTTC 高度一致（逐位相同）

机制链（全部有数据证据）：

1. `sim_seed` 的唯一作用：`env.reset(seed)` 后 `randomize_behavior()` 把两个 IDM NPC 的
   指数 `DELTA` 随机化到 [3.5, 4.5]。
2. **lead 车**以目标速度起步且前方无车，自由流加速度
   `COMFORT_ACC_MAX·(1 − (v/v₀)^DELTA)` 在 v = v₀ 时对任意 DELTA 恒为 0
   ⇒ lead 轨迹**与种子无关**（实测速度全程恒定 18.620022，12 位小数不变）。
3. **ego** 使用确定性 boundary 控制器；在 ramp 的种子扰动影响到它之前，
   ego–lead 闭环节点与种子无关。
4. **ramp 车**朝向不同目标速度加速，加速度依赖 DELTA ⇒ 从 step 1 起轨迹即不同
   （trace 哈希差异的唯一来源）。
5. 关键次序：**所有 ego 轨迹分歧都严格晚于 TTC 最小值步**
   （anchor-0001：argmin k=25–28 vs 分歧 k=40–56；anchor-0002：k=15–16 vs k=48–63；
   anchor-0000：全程无分歧）。分歧后 ego 因 ramp 在前而减速，ego–lead TTC 只会上升，
   不可能产生更低的最小值。
6. 实测：36 个多 repetition 组的 `min_forward_ttc_sampled_s` **全部逐位相同**。

#### 3.3.1 适用范围限定（R3：不得外推）

上述"种子无关"是**机制性**结论，但它依赖的每个前提都是**当前 pilot 采样锚点的具体属性**，
**不得**外推到未采样的 anchors、正式阶段锚点集合或任何碰撞事件：

1. **"lead 与种子无关"依赖 lead 处于自由流且初速=目标速度**。本 pilot 全部锚中，lead 前方无
   更慢车、以巡航目标速度起步 ⇒ IDM 加速度对指数 `DELTA` 恒为 0。若未来锚点令 lead 初速低于
   目标速度、或在 lead 前方放置更慢车，则 lead 加速度将依赖 `DELTA`，其轨迹**会随种子变化**，
   本结论即失效。
2. **"min-TTC 恒由 lead 决定"是采样结果，不是恒等式**。pilot 中 ramp 从未成为 min-TTC 车；
   对不同几何（如 ramp 更早并入、或 lead 更近），min-TTC 车可能改变。
3. **"ego 分歧晚于 min-TTC 步"是逐锚观测，不是普遍次序**。若正式锚点中 ego 因 ramp 更早
   减速，分歧可能早于 min-TTC，从而破坏"min-TTC 与种子无关"。
4. **碰撞事件本身在全 pilot 中未观察到（全零）**，因此**无法断言碰撞与种子无关**：
   ego 一旦分歧，其后一切（含潜在碰撞）都可能依赖种子。任何"碰撞也确定/种子无关"的说法
   **无证据支持**。

### 3.4 科学解读（重要限定）

- 负 ΔTTC(both)（组合干预降低最小前向 TTC）是**确定性闭环节点 + 场景几何**的属性，
  由 boundary 控制器的反馈时序决定，**不是随机碰撞风险的反转**，不得宣称为
  "干预增加碰撞风险"：全部 episode 碰撞二元值为 0，TTC 是诊断性代理量
  （5 Hz 采样、常速、纵向），不是碰撞概率。
- **repetition 级"新鲜种子"不重采样 ego–lead 交互**，只重采样 ramp 干扰车。
  因此：审计流的"独立复现"与多 repetition 平均，对 ego–lead 终点（碰撞与 TTC）
  **不提供独立证据**；正式阶段的独立单元是**锚点（场景）**，不是 episode 数。
  此限制必须进入正式统计分析计划（聚类/有效样本量），见 §6 与条件 5。
- **限定（R3）**：以上"repetition 不提供独立证据"是**在现 pilot 锚点与被冻结的现状下验证**的
  结论，**不等于**"任何未来设计下 repetition 都无信息"。若候选方案保留现种子语义，
  该结论继续成立；若 V02 选择引入**能真正改变 ego–lead 交互的随机扰动**（如随机化 lead
  初速/目标速度、或在 lead 前方加入扰动车），则 repetition 可重新获得独立信息——
  但这必须作为**新预注册设计**的一部分显式定义并冻结（见 V02 §4），不得沿用 V01 的锚点结论。

---

## 4. 四张图的统计与展示审计

| 图 | 内容 | 审计结论 | 处置 |
|---|---|---|---|
| 1 四条件配对结果 | 每锚四条件 Y 标记 | 诚实：全零直接可见，无统计宣称 | 不变 |
| 2 每 anchor 风险差 | delta_both 点估计 | **F-03**：名为"森林图"但无任何区间；零方差下区间不可估计 | 改称点估计图，标题注明 "zero variance - no CI estimable" |
| 3 discovery→audit | 提名锚两点对比 | **F-02**：全零单点 marker 数据使 autoscale 产生 ±1e-17 退化范围，渲染出无意义的 "1e−17" 轴偏移（tick 实为 1e-17 倍数） | `_sane_value_axis` 修正：\|v\|<1e-12 吸附为 0、退化时显式设 ±0.5、禁用 offset；现 ylim=(−0.5, 0.5)，无偏移 |
| 4 探索性 TTC 裕度 | ΔTTC 条形点估计 | **F-03**：报告文本称"森林图"实为条形点估计；锚内 ΔTTC 跨 repetition 逐位相同（§3.4），不存在 repetition 级区间 | 报告文本改称"点估计图"；图题注明 no CI；表格增加**跨锚描述范围（min–max，明确非置信区间）** |

- 修复实现：`safefliplab/report.py::_sane_value_axis`（防退化轴）+ `_wrap_title`（标题换行）+
  三个图函数应用 + `savefig(bbox_inches="tight")` 兜底；
  回归测试 `tests/test_figure_axes.py`（**10 项**：全零/微浮点/真实分布/空值/两图集成 +
  长标题换行/保词/短标题不变/真实图标题含换行）。
- **F-05（本轮新增，已修复）**：`figure_2/3/4` 的长英文标题以单行 `fontsize=9` 绘制，
  `tight_layout` 不计入标题宽度 → 右侧被画布裁切（"…no C"、"…no CI estima"）。
  修复：`_wrap_title` 按词换行 + `bbox_inches="tight"`。再验收四图：标题完整不裁切。
- 原则：**没有可估计区间时绝不绘制或冒充置信区间**；浮点噪声永不充当坐标尺度；
  **全零观测、估计不确定性、无法估计跨主种子不确定性三者必须分别表述**——
  图 1 直接显示全零观测；图 2/3/4 均为**点估计**并显式注明 `zero variance - no CI estimable`
  （零方差下区间不可估计，非"区间为零"）。

---

## 5. 决策记录逐项审核（D4/D5/D6、D12–D20）

| 项 | 内容 | 状态 | 本轮审核意见 |
|---|---|---|---|
| D4 | sim_seed 映射 | PROPOSED，**未批准** | 实现与数据一致（四条件共享同 repetition 种子）。但 §3.4 表明种子只随机化 ramp nuisance：正式阶段应把"锚点为独立单元"写入统计计划，否则 8 seed × 800 会被误读为 8 组独立交互样本 |
| D5 | tie-break 细节 | PROPOSED，**未批准** | §2.2：零碰撞下主键恒 0，tie-break 决定一切，两方法提名不可区分。若正式阶段碰撞基线仍近 0，**该规则集在科学上退化**——需人工决定提名信号（见 §6） |
| D6 | pilot 结构缩放 | PROPOSED，**未批准** | 结构与精确 240 闭合属实；审计 quartet 数 5 ≪ 正式 20，审计证据有限（D10 已列） |
| D11 | 相位隔离 bug | 已修复 + 回归测试 | 本轮用数据证实修复正确（§1.3）；PD-01 偏离已留痕 |
| D12 | 跨 master_seed 隔离 | 已修复 + 8 项回归测试 | 代码与测试属实；**待人工复核**其对正式跨 seed 断点恢复的覆盖（D11 已建议） |
| D13–D16 | 账本原子性/正式调度/安全门/配置冻结 | 已修复 + 测试 | 源码审计属实；正式 CLI 锁与 `_require_formal_go` 双层保护完好（formal 未执行） |
| D17 | 跨实例/跨进程预算同步 | 已修复 + 测试 | 属实；**本轮发现其遗留缺口 F-01 并修复**（见下） |
| D18 | 报告主种子/run_id 隔离 | 已修复 + 测试 | 属实；margins 模块沿用同一 primary/replay 语义 |
| D19 | 规则冻结 + 实现一致性交叉核验 | 已修复 + 测试 | 属实；`configs/formal_v01.json` 未改动（mtime 早于全部运行） |
| D20 | 探索性 TTC 裕度分析 | PROPOSED，非协议 | 保留，但须按 §3.4 限定：ΔTTC 跨种子逐位相同、非随机风险反转；已在报告边界声明与图题中落实 |

### 本轮新发现缺陷（均已修复 + 回归测试，待人工复核）

- **F-01（代码，正式相关）**：磁盘账本表头/数据行均为 **20 列**（早于 `budget_scope` 列），
  而当前代码追加 21 字段行；重读时第 21 字段被丢弃 ⇒ 新实例
  `launched_count_scope("formal\|method\|seed") = 0`，**跨进程/断点恢复的正式
  分作用域预算失效**（实测复现：append 后新实例 scope=0）。
  **修复**：`ledger.py::resolve_fieldnames` 对"COLUMNS 前缀式"遗留表头补齐尾部规范列名
  （只读侧，不改写账本文件）；同时新增 `LedgerFormatError`：表头非 `COLUMNS` 亦非其严格前缀
  （多余列/乱序/未知/同宽异名）→ **安全拒绝**；数据行字段数多于已解析列数 → 也拒绝
  （杜绝静默丢列）。先解析校验、后推进计数，拒绝时不污染状态。
  **回归测试**：`tests/test_ledger_legacy_acceptance.py`（15 项，独立临时账本）覆盖 6 场景：
  (1) 遗留表头→追加 21 字段行→关闭→重开往返；(2) `budget_scope` 落盘并在重开恢复；
  (3) 每 `(method, seed)` 作用域重开后独立；(4) **8 个 OS 进程共享一份遗留账本、cap=3 →
  恰 3 成功 5 拒绝，无超支**；(5) 中断无 outcome 仍计费、重复 key 拒绝、新 run_id 再次计费
  （无免费重试）；(6) 4 类不兼容表头全部安全拒绝。
  **证据**：`docs/F01_LEDGER_ACCEPTANCE_20261013.txt`；真实账本打开前后
  `smoke=24 / pilot=240` 不变、文件字节数不变（只读）。**待人工复核**。
- **F-02（图表）**、**F-03（图表误标）**、**F-04（manifest 陈旧）**：见 §1.4、§4。
- **L-01（设计，PROPOSED，本轮新增）**：正式阶段应采用**独立 canonical 21 列标准账本**，
  与旧（20 列遗留）账本物理分离、绝不混写；完整方案见
  `docs/V02_RESEARCH_PROPOSAL.md` §9。未实现、未改任何文件。

---

## 6. 主要终点选择：保留 V01 vs 新建 V02（只列利弊，**不代为选择**）

背景事实：pilot 240 episodes 零碰撞（15 个不同 anchor；**不作 rule of three 的"<5%"量级宣称**，
见 §2.3）；主指标（碰撞二元差）零方差；连续 TTC 裕度有可观察差异但为非协议指标；
§3.4 的种子语义限制对两种方案都成立。**本轮新增 `docs/V02_RESEARCH_PROPOSAL.md`**，
对"新建 V02"给出完整预注册设计草案（全部标记 PROPOSED）；本节保留为**决策摘要**。

### 方案 A：保留 V01 原协议（碰撞二元主指标 + 碰撞差提名 + 8 seed × 800）

- 优点：不改变冻结设计与指纹；与任务书/配置一致；pilot 工件继续有效；
  预算与计划已定（12,800）；无需重新论证效力。
- 缺点：若正式碰撞基线仍近 0，主指标可能仍零方差 ⇒ 提名退化为 tie-break、
  两方法不可区分、审计复述无信息；锚内结果对种子确定（§3.4）⇒ repetition/审计
  不增加 ego–lead 终点的独立信息，有效独立单元=锚点数，需聚类分析；
  12,800 episodes 的期望信息增益可能极低。**（注：不再引用"5% 上界"——该数字建立在
  被违反的 iid 假设上，见 §2.3。）**

### 方案 B：新建 V02 预注册协议（如以连续 TTC 裕度为主/共同主指标，碰撞降为次要）

- 优点：pilot 已观察到非零方差与一致方向（描述性），主指标可估计、可构区间、
  可比较方法；与干预的真实作用面（连续安全裕度）对齐。
- 缺点：**在看到 pilot 探索结果后更换主指标存在事后选择风险**，必须完整预注册
  （终点、提名信号、种子语义、样本量、分析计划）并经人工批准后方可运行任何
  formal episode；与原始任务书冻结设计不可比；pilot 数据只能作管道验证、
  不能作 V02 证据；且 V02 仍需解决 §3.4：若保留现种子语义，repetition 仍不
  重采样 ego–lead 交互，"新鲜种子"的随机化内容（如是否也随机化 lead 行为）
  需重新定义并冻结。

### 共性待决（两方案都需人工裁决）

1. 有效样本量与聚类单元（锚点 vs episode）的正式定义；
2. 零碰撞/低事件率下 audit 流的角色（是否保留、保留则解释力如何表述）；
3. 若改任一点，即构成新预注册协议，旧结论一律不得混用。

---

## 7. GO / CONDITIONAL GO / NO-GO 建议

### 7.1 分维度结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 代码正确性 | **GO** | 209 单测全过（EXIT 0，47.4 s）；doctor 17/17 GO；F-01/F-02/F-03/F-04/F-05 已修复并各带回归测试（F-01 含 6 场景独立验收）；正式 CLI 锁与安全门完好；冻结配置未改动 |
| 实验协议合规性 | **CONDITIONAL GO** | smoke/pilot 均在预算内精确执行（smoke 24/24；有效 pilot 240/240）；PD-01（+220）已完整披露并留痕、未掩盖——**需用户接受**；D4/D5/D6 未经批准即用于 dev 阶段（pilot 仅作管道验证，未当正式证据） |
| 科研结论有效性 | **NO-GO（对 formal 执行）** | 主指标零方差；两方法提名退化不可区分；repetition 不重采样 ego–lead 交互；ΔTTC 为确定性属性非风险反转。formal 12,800 在此设计下可能无法产出方法间结论 |

### 7.2 总体建议

**CONDITIONAL GO（工程与代码就绪）+ formal 执行维持 NO-GO**，直至以下人工条件全部满足：

1. **批准或修订 D4/D5/D6**（含"有效样本数在提名中的权重"与提名信号选择）；
2. **裁决 BLOCKER-3**：在 §6 的方案 A/B 中明确选择（或提出并经同等严格预注册的第三方案），
   并据此确定正式统计分析计划（含锚点为独立单元的聚类处理）；
3. **接受 PD-01 偏离**（pilot +220）及其留痕方式；
4. **复核 D12–D19 与本轮 F-01–F-05 修复**（回归测试已就位；F-01 已完成 6 场景独立验收）；
5. **确认种子语义限制的处理**（§3.4）：正式阶段"新鲜种子"随机化内容是否足够，
   否则 repetition/审计证据强度须在报告中如实降级；
6. **formal 执行需用户单独明确 GO**（CLI 锁保留；本构建不会自动运行、不会发布 GitHub）。

---

## 8. 证据索引（本轮命令与退出码）

| # | 命令 / 操作 | 结果 |
|---|---|---|
| 1 | 账本/备份/磁盘三方对账脚本（tmp_audit/budget_reconcile.py, deep_dive.py, timeline.py, verify20.py） | 264 / 244 / 484 完全吻合；20 个独有单元=D11 跳过锚 |
| 2 | `python -m unittest discover -s tests -v` | **Ran 209 tests, OK**，EXIT 0，47.4 s（`docs/V06_TEST_RESULTS_20261013.txt`） |
| 3 | `python -m safefliplab doctor` | 17/17 PASS，VERDICT: GO（`docs/DOCTOR_20261013.txt`） |
| 4 | TTC 语义重算（ttc_semantics.py, seed_consistency.py, per_vehicle_divergence.py, ttc_generalise.py, argmin_vs_divergence.py） | argmin 车 240/240=lead；argmin t=1.2–9.2 s；ego 分歧全部晚于 argmin；36/36 组 TTC 跨种子逐位相同 |
| 5 | 提名退化分析（nomination_analysis.py） | 两方法 audit 锚集合相同（0000–0002）；delta 全 0 |
| 6 | **F-01 独立验收**（f01_acceptance.py → `docs/F01_LEDGER_ACCEPTANCE_20261013.txt`；`tests/test_ledger_legacy_acceptance.py` 15 项） | 6 场景全过：往返/作用域恢复/每 (method,seed) 独立/8 进程 cap=3 不超支/无免费重试/格式安全拒绝；真实账本 24/240 不变 |
| 7 | `python -m safefliplab report --phase smoke / pilot` | EXIT 0；四图重建（标题换行、无 1e−17）；manifest 自账本重新生成（旧件备份） |
| 8 | 预算边界 | 本轮新发起 episode = **0**（账本 528 行、原始 JSON 484 个、manifest 墙钟 177.27 s 均未变） |
| 9 | **第二轮复审修订**（rev_data.py → `docs/REVISION_ANALYSIS_20261013.txt`） | R1 rule of three 独立性假设被否定；R2 `valid_n` 证实为最终提名首枚生效键（4 vs 1）；R3 TTC 确定性结论限定到已采样锚；分层单元计数：WE discovery 15 锚 / VF discovery 6 锚 / audit 3 锚 |

关键文件：`reports/{smoke,pilot}_report.md`（含新边界声明）、
`reports/{smoke,pilot}_margins.csv`、`reports/<phase>/figure_*.png`、
`runs/manifest_pilot_summary.json`（已修正）+ `.stale_zero_backup`、
`safefliplab/ledger.py`（`LedgerFormatError`/`resolve_fieldnames`）、
`safefliplab/report.py`（`_sane_value_axis`/`_wrap_title`）、
`tests/test_ledger_legacy_acceptance.py`、`tests/test_figure_axes.py`、
`tests/ledger_proc_worker.py`、`docs/F01_LEDGER_ACCEPTANCE_20261013.txt`、
`docs/V06_TEST_RESULTS_20261013.txt`、`docs/DOCTOR_20261013.txt`、
`docs/REVISION_ANALYSIS_20261013.txt`、`docs/V02_RESEARCH_PROPOSAL.md`（本轮新增）。

---

## 9. 明确未做（按用户约束）

- 未运行 formal 12,800；未重跑 smoke/pilot；未自动发布 GitHub；未访问/修改 CornerCaseLab 旧项目；
  未修改 `configs/formal_v01.json`（mtime 证据）；未删除任何历史记录或原始数据；
  未宣布任何用户批准；未修改主碰撞指标；未选择 §6 任一方案；未开始 V02 开发（本轮仅**设计**）。
- 本轮**新增真实仿真预算 = 0 episodes**（统计解释修订 + 设计方案，均为文档/只读分析）。
