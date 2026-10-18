# OWNER_GUIDE_V02 — SafeFlipLab V02 中文教学与复现指南

> 面向「想逐步看懂代码的研究者」。本指南假定你会用 PyCharm，但不假定你熟悉本项目的缩写。
> V01 的指南见 `docs/OWNER_GUIDE.zh-CN.md`（仍然有效，两者**互相独立**）。

---

## 0. 一分钟理解 V02 在做什么

V01 用「本车是否碰撞」（0/1）当主指标，结果 264 次真实仿真**一次都没撞**，
于是所有条件看起来都一样，方法也分不出来。V02 换了一个思路：

1. **主指标换成连续量**：每次仿真里「本车与前车的最小前向 TTC」（秒），
   数值越小说明两车越接近（越危险）。
2. **让重复运行真的有区别**：V01 里同一个场景跑 3 次，结果**一模一样**
   （因为随机种子只影响旁边一辆干扰车，不影响前车）。V02 每次重复时，
   对**初始场景**做一次小幅随机扰动（间距、前车速度、自车速度），
   四个条件**共用这一次抽样**，这样条件之间的比较仍然是配对的，
   但不同重复之间真的不同了。

一句话：**V02 把「有没有撞」换成了「离得多近」，并修好了「重复等于没重复」的毛病。**

---

## 1. 环境准备（与 V01 共用）

```powershell
cd D:\SafeFlipLab
.\.venv\Scripts\python.exe -c "import cornercaselab, highway_env; print('ok')"
```

依赖（已锁定）：`cornercaselab==0.3.0`、`highway-env==1.10.2`、`gymnasium==1.2.2`、
`numpy<3`、`matplotlib<4`、`Pillow<13`。

**V02 的代码在 `D:\SafeFlipLab\v02\`**，V01 在 `D:\SafeFlipLab\safefliplab\`。
两者**互不 import**，账本与报告**物理分离**：

| | V01 | V02 |
|---|---|---|
| 代码 | `safefliplab/` | `v02/v02lab/` |
| 配置 | `configs/` | `v02/configs/` |
| 账本 | `runs/episode_ledger.csv`（20 列，只读） | `v02/runs/{smoke,pilot}/episode_ledger.csv`（21 列） |
| 报告 | `reports/` | `v02/reports/` |

---

## 2. 四条命令

```powershell
cd D:\SafeFlipLab\v02

# 1) 只读体检（不跑任何仿真）
..\.venv\Scripts\python.exe -m v02lab doctor

# 2) 单元测试（零真实 episode）
..\.venv\Scripts\python.exe -m unittest discover -s tests -v

# 3) 真实小实验（预算硬上限 24 / 240）
..\.venv\Scripts\python.exe -m v02lab smoke --max-episodes 24
..\.venv\Scripts\python.exe -m v02lab pilot --max-episodes 240

# 4) 生成报告（只读账本，零 episode）
..\.venv\Scripts\python.exe -m v02lab report --phase smoke
..\.venv\Scripts\python.exe -m v02lab report --phase pilot
```

> ⚠️ **V02 没有 formal 入口**。这是刻意设计的：本项目授权内不存在 12,800 次运行。

---

## 3. 源码模块地图（按推荐阅读顺序）

| 顺序 | 文件 | 职责 | 读它你能搞懂什么 |
|---:|---|---|---|
| 1 | `v02/configs/v02_frozen_v1.json` | 冻结的全部研究参数 | 所有数字（阈值、域、扰动宽度、预算）在这里，且**没有默认值** |
| 2 | `v02lab/schema.py` | 参数状态机 | 为什么 `UNSET` 会报错而不是悄悄取默认值 |
| 3 | `v02lab/anchors.py` | 锚（场景）域 + 确定性拒绝采样 | 「合法域」如何保证四条件永不越界、永不裁剪 |
| 4 | `v02lab/conditions.py` | 四条件、种子派生、扰动抽样 | 为什么四条件共享同一个 `sim_seed`、审计种子如何与发现种子隔离 |
| 5 | `v02lab/quartet.py` | 一次重复 = 一次共享扰动 + 四个条件 | **V02 的核心修正**：重复为什么不再相同 |
| 6 | `v02lab/adapter_real.py` | 真实仿真适配 | 逐 step 的 `(has_candidate, gap, closing)` 如何从轨迹重算；如何与上游对拍 |
| 7 | `v02lab/ttc_state.py` | TTC 三层状态模型 | `None ≠ 安全`；截断与缺失怎么处理 |
| 8 | `v02lab/ledger21.py` | 21 列独立账本 | 先计费再仿真、原子去重、跨进程锁 |
| 9 | `v02lab/runner.py` | 单 episode 执行 | **计费后一切都在 try 里**：结构上不可能出现「孤儿 launch」 |
| 10 | `v02lab/phases.py` | smoke / pilot 编排 | 断点恢复如何做到「绝不重跑已计费 episode」 |
| 11 | `v02lab/methods.py` | 两方法提名规则 | 为什么排序方向是「越负越好」 |
| 12 | `v02lab/stats_anchor.py` | 锚级统计 | 为什么没有 p 值（抽样假设门控） |
| 13 | `v02lab/report.py` | 统计、门槛、CSV、图表 | 每个数字从哪来、哪些被标为不可估计 |
| 14 | `v02lab/cli.py` | 命令入口 | 预算硬上限如何落实 |

---

## 4. 关键概念（用最少的字讲清）

### 4.1 六维场景（上游冻结）

| 字段 | 含义 | 上游范围 | V02 锚域 |
|---|---|---|---|
| `ego_speed` | 自车初速 (m/s) | [20, 32] | [23, 30] |
| `front_gap` | 与前车初始间距 (m) | [18, 80] | [21, 40] |
| `front_speed` | 前车速度 (m/s) | [15, 32] | [17, 21] |
| `ramp_x` | 匝道车纵向位置 (m) | [80, 140] | 同上游 |
| `ramp_speed` | 匝道车初速 (m/s) | [12, 30] | 同上游 |
| `ramp_target_speed` | 匝道车目标速度 (m/s) | [20, 34] | 同上游 |

### 4.2 四条件与「只改一个变量」

| 条件 | 改动 |
|---|---|
| `00` | 什么都不改（对照） |
| `10` | `front_gap += 2.0 m` |
| `01` | `ego_speed −= 1.0 m/s` |
| `11` | 两个都改 |

其余四维**必须完全相同**；越界直接报错，**绝不 clip**（有单测钉死）。

### 4.3 一次「重复（repetition）」到底是什么

```
base = 锚名义值 + 一次共享扰动抽样        # 例如 front_gap −1.86 m、front_speed −1.09 m/s
quartet = { 00: base, 10: base+2.0m, 01: base−1.0, 11: base+2.0m−1.0 }
```
- 四个条件共用 `base`（所以是**配对**比较）；
- 不同 repetition 的 `base` 不同（所以重复**携带新信息**）；
- 同一个 repetition 的四个条件共用**同一个 `sim_seed`**。

### 4.4 两种「距离差」怎么算

设 `M(条件)` = 该 episode 的最小前向 TTC（越大越安全）：

| 量 | 公式 | 含义 |
|---|---|---|
| `Δgap` | `M(10) − M(00)` | 只加间距的效果 |
| `Δspeed` | `M(01) − M(00)` | 只降初速的效果 |
| `Δboth` | `M(11) − M(00)` | 两个一起改的效果 |
| `I_lin` | `M(11) − M(10) − M(01) + M(00)` | **非可加性**（交互） |

**先在一个 repetition 内做差，再对同一锚的多个 repetition 求平均** ⇒ 得到锚级效应。
最后跨锚汇总（锚是独立单元）。

**算术例子**（用 smoke 的真实数字，锚 `v02-anchor-0002`、rep0）：

```
M(00) = 0.0689   M(10) = 0.7543   M(01) = 0.7394   M(11) = 0.2565
Δgap   = 0.7543 − 0.0689 = +0.6854
Δspeed = 0.7394 − 0.0689 = +0.6705
Δboth  = 0.2565 − 0.0689 = +0.1876
I_lin  = 0.2565 − 0.7543 − 0.7394 + 0.0689 = −1.1683
```
读法：单独加间距或单独降速都把 TTC 从 0.069 s 抬到 0.74–0.75 s（明显更安全），
但**两个一起改只抬到 0.257 s** —— 联合效果远小于两者之和，这就是**强次可加交互**
（`I_lin` 明显为负）。注意这个例子里的 `00` 还发生了碰撞。

### 4.5 `I_log` 是什么、为什么常常「未定义」

`I_log = log M(11) − log M(10) − log M(01) + log M(00)`，比值尺度的交互。
只要四个量中**任何一个**是 0、+∞（被截断）或缺失，`I_log` 就**未定义**，
此时报告给的是**原因码**（`ZERO_TTC` / `CENSORED_INFINITY` / `MISSING`），
**不会**用 `log(max(v, ε))` 之类的方式硬凑一个数。

### 4.6 预算公平性

- 两种方法**预算完全相等**，且都从**同一份 discovery 数据**提名，差异**只在分配规则**；
- 新账本按 **budget scope** 独立计费（`v02-smoke` / `v02-pilot`），**互不借用**；
- 失败 / 中断 / UNKNOWN **一律计费**，无免费重试。

### 4.7 断点恢复

`runner.billed_tuple_keys()` 读账本，得到 `(method, anchor, repetition, condition, stream)` 集合；
已存在的**直接跳过**。所以重复调用同一条命令**不会重跑、不会重复计费**，也**不会**补跑失败尝试
（协议禁止补跑）。

---

## 5. 怎么看输出

### 5.1 CSV / JSON

| 文件 | 内容 | 怎么用 |
|---|---|---|
| `v02/reports/<phase>_episodes.csv` | 每个**已计费** episode 一行 | 逐条核对；`result_recorded=0` 表示发起后无结果（记 `unknown`，仍计费） |
| `v02/reports/<phase>_quartets.csv` | 每个 quartet 的四条件 TTC 与四个差值 | 主统计的来源 |
| `v02/reports/<phase>_anchors.csv` | 每锚的可用 quartet 数与四个锚级均值 | 看单锚行为 |
| `v02/reports/<phase>_contrasts.csv` | 四个效应量 + 锚级 bootstrap 区间 | **主结果表** |
| `v02/reports/<phase>_comparisons.csv` | 两方法 `precision@k` | 辅助/探索性，别当主结论 |
| `v02/reports/<phase>_budget_summary.csv` | 预算账 | 失败/未知也计入 `launched` |
| `v02/reports/<phase>_summary.json` | 全部数字 + 门槛状态 | 机器可读 |
| `v02/reports/<phase>_report.md` | 中文叙述报告 | 人读 |

### 5.2 四张图

1. `figure_1_condition_ttc.png` — 四条件的 min-TTC 分布（箱线 + 散点）
2. `figure_2_anchor_contrast_forest.png` — 锚级效应 + **cluster bootstrap 区间**（森林图）
3. `figure_3_within_anchor_variation.png` — **锚内跨 repetition 的散开程度**（V02 是否真的修好了 V01 的毛病）
4. `figure_4_per_anchor_delta_both.png` — 每锚的联合效应（红 = 裕度被压低）

### 5.3 门槛状态怎么读

| 门槛 | 含义 | 失败意味着 |
|---|---|---|
| `G2_intervention` | 四条件确实按声明改动、且都在界内 | 干预实现有问题，必须停 |
| `G3a_within_anchor_variance` | 锚内 min-TTC 方差 > 0 | 扰动无效，设计不成立 |
| `G3b_binary_events` | 是否观测到碰撞 | `DESCRIPTIVE_ONLY` = 二元端点只能说「没观测到」 |
| `G4_perturbation_effective` | min-TTC 是否**不再**跨 repetition 逐位相同 | 失败则 repetition 仍无信息 |
| `G6_simulator_stability` | 技术失败数 | `PASS_WITH_FIXED_CODE_DEFECT` = 唯一错误是本项目已修复的代码缺陷 |
| `G10_missingness` | 不可用 quartet 占比 ≤ 20% | 失败则数据质量不足 |
| `metric_equivalence` | 派生 TTC 与上游值对拍 | 失败则度量实现有语义错误 |

---

## 6. 常见审稿质疑与应答

| 质疑 | 应答 |
|---|---|
| 「你把主指标换成了 TTC，是不是为了得到好看的结果？」 | 是**事后性**设计（已在 D36 披露）。缓解：全部参数在 V02 数据前冻结；方向由机制推导；不做确证性检验；V01 数据不作 V02 证据 |
| 「TTC 不是碰撞风险。」 | 完全同意。报告**不**把 TTC 表述为碰撞概率，只作为「接近程度」的连续代理量 |
| 「18 个锚太少了。」 | 同意。V02 定位为 **pilot 级估计性**研究，区间为描述性；正式样本量需另行确定 |
| 「为什么没有 p 值？」 | 抽样假设 A/B/C 未被证明；产 p 值等于把有效性建立在未验证假设上。**系统无权自行批准** |
| 「两方法比较呢？」 | 明确标为 **辅助/探索性**（每方法 3 个提名 × 1 个审计 quartet）；两提名集**共享同一 anchor**，且曾有一个已修复的种子标签缺陷导致 4 个重复模拟；且与 CornerCaseLab 高度重叠，**不作新颖点** |
| 「你改了仿真器吗？」 | **没有**。扰动纯场景层，直接调用上游未修改的 `evaluate()`；`metric_equivalence` 门槛**验证**度量实现与上游一致 |

## 7. V02 **不能**支持的结论（务必写进任何引用）

- ❌ 不能声称 TTC 下降等于真实道路碰撞风险上升；
- ❌ 不能把 V02 结论外推到收窄的锚域之外；
- ❌ 不能声称「稳定反转」或任何显著性结论（无 p 值）；
- ❌ 不能把方法比较当主结论；
- ❌ 不能把 pilot 结果当作正式评估结果。

## 8. 出问题时的排查顺序

1. `python -m v02lab doctor` 是否 7/7？
2. `python -m unittest discover -s tests` 是否全过？
3. 账本行数是否 = 2 × 已发起数（launch + outcome 必须成对）？
   ```powershell
   ..\.venv\Scripts\python.exe -c "import csv;r=list(csv.DictReader(open('runs/pilot/episode_ledger.csv',newline='',encoding='utf-8')));print(sum(1 for x in r if x['row_type']=='launch'), sum(1 for x in r if x['row_type']=='outcome'))"
   ```
4. `budget_scope` 计数是否已达上限？（到顶就拒绝再跑，这是**正确**行为）
5. 报告里 `metric_equivalence` 是否为 PASS？不是则度量实现对不上，先别信任何统计。
