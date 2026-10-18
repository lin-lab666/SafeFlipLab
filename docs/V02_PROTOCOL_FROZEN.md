# V02 协议冻结记录（FREEZE RECORD）

> **本文件描述在 V02 任何真实 episode 之前冻结的配置。**
> ⚠️ **时间戳诚实声明（独立复核 F6）**：真正承载冻结的是配置文件
> `v02/configs/v02_frozen_v1.json`（mtime **17:04**），它**早于**全部 V02 真实数据
> （smoke 首条 launch **17:10**、pilot 首条 **17:17**），其 SHA-256 也已写入 manifest 可核验。
> 但**本叙述文档与决策日志写于 17:24，晚于数据**。因此本文件**不是**「预注册」的时间证据，
> 只能作为配置冻结的说明。本项目**未**做外部预注册。
> 冻结时间：2026-10-15（GMT+8）
> 冻结人：WorkBuddy 自主项目负责人（依据 2026-10-15《项目总负责人自主执行授权》）
> 冻结对象：`v02/configs/v02_frozen_v1.json`（全部参数 `status = FROZEN`）

---

## 0. 冻结的完整性声明（必须诚实阅读）

- 本次冻结是**项目负责人在授权范围内自主做出的工程与科研设计决定**，理由记录在
  `docs/AUTONOMOUS_DECISIONS.md`（D28–D36）。
- 它**不是**外部同行评审，**不得**被表述为「已通过独立科研评审」或「已获外部批准」。
- V01 中未经批准的 **D4 / D5 / D6 并未因此获得追认**；V02 使用**全新编号 D28+**，
  与 V01 决策严格分离。
- V01 的冻结配置 `configs/formal_v01.json` **未被修改**（mtime 仍为 2026-10-12 12:13）。

## 1. 协议指纹

| 项 | 值 |
|---|---|
| protocol id | `SafeFlipLab-v02` |
| 配置文件 | `v02/configs/v02_frozen_v1.json` |
| 配置 SHA-256（canonical JSON） | 见 `v02/runs/**/manifest_*.json` 的 `protocol_hash` 字段（运行时写入） |
| 账本 schema | `sfl-v02-21col`（21 列）。表头 SHA-256 **`24eeb3915d91bcec45e26749f0f84e71ab87f5908fe1c16c3b96ea4815643d16`**，记录于 **`v02/runs/smoke/episode_ledger.schema.json`** 与 **`v02/runs/pilot/episode_ledger.schema.json`**（由 `EpisodeLedger21.write_schema_fingerprint()` 生成，并可用 `verify_schema_fingerprint()` 复核），同一哈希亦见各阶段 `manifest_*.json` 的 `header_sha256` 字段 |
| 仿真契约 | `cornercaselab==0.3.0`、`policy=boundary`、25 s 视界、15 Hz 仿真 / 5 Hz 策略 |
| 上游 bounds | `ego_speed [20,32]`、`front_gap [18,80]`、`front_speed [15,32]`、`ramp_x [80,140]`、`ramp_speed [12,30]`、`ramp_target_speed [20,34]` |

## 2. 研究问题

在**冻结的简化高速汇入场景族 + 冻结 `boundary` 规则控制器**下：

- **主问题**：把初始前车间距 +2.0 m、把自车初速 −1.0 m/s，是否会**提高**「自车与前车更接近」
  的风险？即：干预是否**降低**连续安全裕度（最小前向 TTC）—— 这就是**安全反转（H-R）**。
- **主问题（交互）**：两个干预的联合效应在**风险差尺度**上是否**非可加**（H-I-lin）？
- **辅助问题**：等预算下 WideExplore 与 VerifyFirst 在**独立审计**中的提名质量是否有差异（H2）。

先验方向由**机制**推导（不由 V01 观测符号决定）：更大前车间距、更低自车初速直觉上更安全，
因此 `Δgap > 0`、`Δspeed > 0`、`Δboth > 0` 为「直觉方向」；`< 0` 即反转。

## 3. 终点（数据前冻结）

| 层级 | 名称 | 定义 | 角色 |
|---|---|---|---|
| 连续 | **M1 主终点** | 每个 episode 的最小前向 TTC（秒），由上游 `longitudinal_ttc` 语义逐 policy step 计算后取最小；缺失/截断按三层规则处理 | **唯一主终点** |
| 二元 | **B1 次终点** | `ego_collision` | 次要；**仅描述性计数**（本场景控制器主动制动，事件率极低） |
| 连续 | M2 | 前向 TTC < 1.0 s 的 policy step 占比 | 登记为次要（本报告不作主推断） |

**TTC 三层处理**（`v02lab/ttc_state.py`）：
- Layer 1 逐 step：`NORMAL_CLOSING`（有限 TTC）/ `NO_CLOSING`（有车但不接近，+∞）/
  `NO_CANDIDATE`（前方无横向重叠候选，`None`）。**`None ≠ 安全`，`None ≠ 0`**。
- Layer 2 episode：`FINITE` / `CENSORED`（右截断于 `τ_cap = 10.0 s`）/ `NO_CANDIDATE`
  （主分析按 **(b) 赋 `τ_cap` + 标记**，并同时给出 **(a) 剔除**的敏感性分析）/ `MISSING`（技术失败，剔除但仍计费）。
- Layer 3 终止：`HORIZON_REACHED` / `TERMINAL_EVENT` / `TECHNICAL_FAILURE`（强制 Layer 2 = MISSING）。
- 配对缺失：`PAIR_MISSING` ⇒ 该 repetition 的全部对比未定义并从锚汇总剔除（**不补位、不插补**）。

**效应量**：锚级配对差均值
`Δgap = mean[M(10) − M(00)]`、`Δspeed = mean[M(01) − M(00)]`、
`Δboth = mean[M(11) − M(00)]`、`I_lin = mean[M(11) − M(10) − M(01) + M(00)]`
（先在 repetition 内配对，再对 repetition 求均值）。

`I_log`（次要尺度）**仅在四量均有限且 > 0 时有定义**，否则返回原因码
（`ZERO_TTC` / `CENSORED_INFINITY` / `MISSING`）；**不启用地板 φ**，不使用任何替换值。

## 4. 场景域（V02，冻结）

| 维度 | V02 anchor 域 | 扰动半宽 | 干预 | 极端情形是否仍在上游 bounds 内 |
|---|---|---|---|---|
| ego_speed | [23.0, 30.0] | ±0.5 | −1.0 | [21.5, 30.5] ⊂ [20,32] ✅ |
| front_gap | [21.0, 40.0] | ±3.0 | +2.0 | [18.0, 45.0] ⊂ [18,80] ✅ |
| front_speed | [17.0, 21.0] | ±1.5 | 0 | [15.5, 22.5] ⊂ [15,32] ✅ |
| ramp_x | [80.0, 140.0] | 0 | 0 | ⊂ [80,140] ✅ |
| ramp_speed | [12.0, 30.0] | 0 | 0 | ⊂ [12,30] ✅ |
| ramp_target_speed | [20.0, 34.0] | 0 | 0 | ⊂ [20,34] ✅ |

- 采样使用**域内拒绝采样**并额外做「扰动极端角点合法性」检查；**任何情况下都不裁剪（no clip）**。
- 域被收窄到「ego 快于 lead」的接近式区间，使 ego–lead 交互成为主导过程。

## 5. 干预（四条件，结构固定）

| 条件 | 仅改变的量 |
|---|---|
| `00` | 无（对照） |
| `10` | `front_gap += 2.0 m` |
| `01` | `ego_speed −= 1.0 m/s` |
| `11` | 两者同时 |

除声明变元外，其余四维、控制器、策略、时域、设置完全一致。四条件共享**同一次扰动抽样**与
**同一个 `sim_seed`**（`condition` 从不进入种子标签）。

## 6. 锚内扰动（V02 的关键修正，冻结）

每个 `(anchor, repetition)` 抽取**一次共享扰动**，叠加在锚名义值上，四条件共用：
- `front_gap`：±3.0 m（零中心均匀）
- `front_speed`：±1.5 m/s
- `ego_speed`：±0.5 m/s

**理由**：V01 中 `sim_seed` 只随机化 IDM NPC 的 `DELTA`，而 lead 以「初速 = 目标速度」自由流运行，
其轨迹与种子无关，导致 min-TTC 跨 repetition 逐位相同。V02 通过**初始条件扰动**使不同 repetition
真的落在不同的 ego–lead 几何上 ⇒ repetition 重新携带独立信息。

**实现边界**：扰动**纯场景层**，直接复用上游 `cornercaselab.simulator.evaluate()`；
**不修改任何仿真物理语义、控制器或环境构造**。

## 7. 种子规范（冻结）

- V02 主种子：`2279189195` = `SHA256(canonical_json(["SafeFlipLab-v02","dev-master",0]))[:4]`（32 位）。
  确定性派生，**非结果挑选**；仅用于 V02 dev 阶段。
- `sim_seed(master, stream, anchor_id, repetition) = SHA256(["SafeFlipLab-v02","seed",master,"sim",stream,anchor_id,repetition])[:4]`。
  含 `stream` ⇒ 审计种子与 discovery 种子**严格不相交**；不含 `condition` ⇒ 四条件配对。
- 锚流：`SHA256(["SafeFlipLab-v02","seed",master,"anchor",i])` 驱动的确定性拒绝流；
  `anchor_id = v02-anchor-%04d`。**锚流前缀稳定**（smoke 的锚 = pilot 的前缀）。
- 扰动流：`SHA256(["SafeFlipLab-v02","seed",master,"perturb",stream,anchor_index,repetition])`。
- 全部使用 `hashlib.sha256`，**不使用** Python `hash()`。

## 8. 方法（辅助，冻结）

两方法从**同一份 discovery 数据**提名，等预算，差异只在分配规则；**只以全新独立审计评判**。

- **WideExplore**：广度——每个锚只用**第 0 个 repetition**（1 个 quartet），
  按 `delta_both` **升序**（最负者优先，即最像反转者），tie-break `(first_seen, anchor_id)`。
- **VerifyFirst**：深度——使用该锚**全部已验证 repetition** 的锚级均值，
  按 `delta_both` 升序，再按**可用 quartet 数降序**（偏向自己真的复验过的锚），
  再 `(first_seen, anchor_id)`。
- **无可用 quartet 的锚**：不计分、不提名，**不给虚拟 0 分**。
- **评判指标 Q1**：`precision@k = mean_{a∈π} 1{Δboth_audit(a) < −δ_eq}`，`δ_eq = 0.05 s`（预注册）。
  `π` 之外的锚未被审计 ⇒ 全池 recall / oracle **`NOT_ESTIMABLE`**，不估计。
- 该对比标注 **AUXILIARY_EXPLORATORY**，不作主结论、不并入主族多重性校正。

## 9. 预算（冻结，不可互相借用）

| 阶段 | 上限 | 计划 | 结构 |
|---|---:|---:|---|
| V02 smoke | 24 | 24 | 3 anchors × 2 repetitions × 4 conditions |
| V02 pilot | 240 | 240 | 主研究 18 × 3 × 4 = 216；辅助 2 methods × 3 nominees × 1 audit quartet = 24 |

- 独立账本：`v02/runs/smoke/episode_ledger.csv`（scope `v02-smoke`）与
  `v02/runs/pilot/episode_ledger.csv`（scope `v02-pilot`），互不借用。
- **失败 / 中断 / UNKNOWN 一律计费**；无免费重试；不补跑、不改名重置。
- **不存在** V02 formal 入口；本项目**不允许**创建 V03 以获取额外预算。

## 10. 统计推断（冻结）

- **独立单元 = anchor**（场景）。episode 与 repetition **不是**独立样本。
- 区间：**锚级 cluster bootstrap**（对 anchor 有放回重采样，`B = 10000`，`α = 0.05`，
  固定分析种子 `20261015`）。其有效性只依赖「anchor 是抽样单元」。
- **确证性检验（sign-flip / max-T）保持 `PENDING`**：抽样假设 A/B/C **未被证明**，
  **不产出任何 p 值**，**不由系统自行批准**。
- **不套用 rule of three** 于零事件（其 iid Bernoulli 前提在本设计中不成立）；
  零事件只作「未观测到事件」描述。
- 主族 = `{Δgap, Δspeed, Δboth, I_lin}`（预注册，一次性检验方向，不择优挑选）。

## 11. 停止条件（GO / NO-GO）

真实仿真在以下任一情形**立即停止**并记录 NO-GO（保留真实错误与已计费预算）：

1. 上游接口/schema/策略不可用或不一致；
2. **G2** 干预越界（任何条件落在上游 bounds 之外）；
3. **G3a** 锚内主终点方差为 0（⇔ 扰动无效）；
4. **G4** 同一锚的 min-TTC 跨 repetition **仍逐位相同**；
5. **G6** 出现技术失败（error/interrupted）且属于系统性原因；
6. **G10** 不可用 quartet 占比 > 20%；
7. 派生 min-TTC 与上游 `min_forward_ttc_sampled_s` 不一致（度量实现错误）。

## 12. 事后性披露

本设计的整体构思**确实受到 V01 pilot 探索性结果的启发**（零碰撞 → 改用连续主终点；
负 ΔTTC → 关注反转假设；种子语义退化 → 引入锚内扰动）。V01 数据在 V02 中**只作管道验证**，
**永不作为 V02 证据**，且**不与 V02 数据合并**。详见 `docs/AUTONOMOUS_DECISIONS.md` D36。
