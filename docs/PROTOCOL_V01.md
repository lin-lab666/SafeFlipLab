# PROTOCOL_V01 — SafeFlipLab 冻结研究协议（v01）

> 本文件冻结正式评估（formal）的研究设计。依据：《SafeFlipLab_完整任务书与续接手册》
> 附录原始八节任务书 + WorkBuddy 执行说明。凡本任务书未精确定义的实现细节，
> 在本文件中以 **PROPOSED** 标注，formal 启动前必须经人工批准；未标注项视为已冻结。

## 1. 研究对象与边界

- 仿真：HighwayEnv merge 场景，经 cornercaselab==0.3.0 公开接口驱动
  （`merge-scenario-v1`，六维场景，25 s horizon，15 Hz 仿真 / 5 Hz 策略）。
- 控制器：cornercaselab `boundary` 观察式规则控制器（gap 6.0 m / headway 0.30 s /
  TTC 0.90 s，巡航目标 30 m/s）。所有条件、方法、种子、阶段保持一致。
- 碰撞观察：`ego_collision`（`env.vehicle.crashed`）。
- 只研究仿真模型行为；不构成真实道路安全结论；不声称全球首创。

## 2. 场景域与四条件（已冻结）

六维上游边界（cornercaselab BOUNDS）：

| 维度 | 上游边界 | anchor 域（收紧后） |
|---|---|---|
| ego_speed | [20, 32] m/s | [21, 32]（-1.0 干预需留量） |
| front_gap | [18, 80] m | [18, 78]（+2.0 干预需留量） |
| front_speed | [15, 32] m/s | 同上游 |
| ramp_x | [80, 140] m | 同上游 |
| ramp_speed | [12, 30] m/s | 同上游 |
| ramp_target_speed | [20, 34] m/s | 同上游 |

四条件（每个条件都是独立真实 episode，恰好 4 次尝试/quartet）：

- `00`：原始 anchor；`10`：仅 `front_gap += 2.0 m`；
  `01`：仅 `ego_speed -= 1.0 m/s`；`11`：两者同时。
- 只采样四条件全部位于上游边界内的 anchors（generator 拒绝采样，不裁剪）。
  越界条件构造直接报错，不 clip。
- 同一 anchor 同一 repetition 的四条件共享一个配对 `sim_seed`。

## 3. 种子派生（已冻结）

- 全部 SHA-256 派生（`safefliplab/seeds.py`），禁止 Python `hash()`。
- `dev_seed = 20261011`：仅 smoke/pilot，不作正式证据。
- 8 个 formal master seeds：
  `SHA256(canonical_json(["SafeFlipLab-v01","formal-master",i]))`, i=0..7，
  冻结于 `configs/formal_v01.json`：
  3451794858, 3280522798, 3404856911, 4151677968,
  565867193, 2023892289, 4034206253, 3582183474。
- **PROPOSED（seed 映射细节，需批准）**：
  `sim_seed = SHA256([protocol, "seed", master_seed, "sim", method, stream,
  anchor_id, repetition])`，其中 `stream ∈ {discovery, audit}`；
  派生标签**不含**条件代码（保证四条件共享），**含** method（两方法流独立）
  与 stream（审计种子绝不与 discovery 种子相同）。
- anchor 流：`SHA256([protocol,"seed",master_seed,"anchor-stream","v01"])`
  支配的统一拒绝采样流；anchor_id = `anchor-%04d`（流内序号，跨方法共享）。

## 4. 指标（已冻结）

- `delta_both = mean(Y11-Y00)`；`delta_gap = mean(Y10-Y00)`；
  `delta_speed = mean(Y01-Y00)`；
  `interaction = mean(Y11-Y10-Y01+Y00)`（风险差尺度的二因素交互）。
- `reverse_pairs = count(Y00=0,Y11=1)`；`rescue_pairs = count(Y00=1,Y11=0)`。
- 不完整 quartet 排除出 quartet 级统计；缺失观察绝不当 0 或 1。
- 单个 reverse 不称"稳定反转"；发现阶段与独立审计阶段必须分开报告。
- bootstrap/区间：聚类单位为 anchor；dev_seed 下任何区间仅为探索性说明。

## 5. 两种方法与 800 episodes/method/seed 预算（已冻结）

**WideExplore**
- discovery：100 个不同 anchor × 1 quartet = 400 episodes；
- 提名 5 个：按 discovery `delta_both` 降序，tie-break（first_seen, anchor_id）；
- audit：5 个提名 × 20 个全新 seed quartet = 400 episodes。

**VerifyFirst**
- stage 1：anchor 流前 40 个 × 1 quartet = 160 episodes；
- 冻结 20 个：按 `delta_both` 降序，tie-break 依次为其余两个单因素差
  （**PROPOSED 顺序：delta_gap 第二、delta_speed 第三**，均降序），
  最后（first_seen, anchor_id）；冻结后不得更改；
- stage 2：20 个 × 3 个新 repetition quartet = 240 episodes；
- discovery 合计 400；从全部 40 个 stage-1 anchor 中提名 5 个，
  **PROPOSED 冻结排序**：mean delta_both 降序 → 有效 quartet 数降序 →
  first_seen → anchor_id；
- audit：5 个提名 × 20 个全新 seed quartet = 400 episodes。

**共同规则**
- 提名先于任何审计 episode 冻结；审计不得复用 discovery 观察；
  审计结果不得反向影响提名规则。
- 所有已发起 episode（含失败、中断、无效）计费；无免费重试；
  未用预算必须报告。
- 正式总量：2 methods × 8 master seeds × 800 = **12,800 episodes**，
  必须 `--confirm --max-episodes 12800` 且人工 GO 后才可启动。

## 6. smoke / pilot（本轮预算，已冻结）

- smoke ≤ 24 个真实 episodes；pilot ≤ 240 个真实 episodes；不进入正式分析。
- smoke 计划（24）：WideExplore discovery 3 quartet（12）+
  VerifyFirst stage-1 2 quartet（8）+ 同 seed 重放 1 quartet（4，验证
  seed→trace 可复现性）。
- **PROPOSED（pilot 结构缩放，需批准）**：每方法 120 episodes。
  WideExplore：15 anchors discovery + 3 提名 × 5 audit quartet；
  VerifyFirst：6 anchors stage-1 + 选 3 × 3 追加 quartet + 3 提名 × 5 audit quartet。
  缩写比例保持正式设计的结构（discovery→冻结提名→独立全新 seed 审计）。

## 7. 停止条件

- 接口/语义不可比 → GO/NO-GO 记录为 NO-GO，停止真实实验。
- smoke/pilot 关键技术失败 → 记录真实错误与 BLOCKED，停止对应操作。
- formal 未获人工 GO 前：只允许实现与准备命令。
