# SafeFlipLab smoke 阶段报告

- 已发起 episodes（含失败/中断，全部计费）：**24**
- 成功完成 episodes：**24**
- 错误 episodes：**0**
- 中断 episodes：**0**
- 中断/未知 episodes：**0**
- 完整 quartets（主）：**5**
- 重放 quartets（同 key 的二次运行，非独立证据）：**1**
- 不完整 quartets：**0**

## 方法 / 流汇总（池化跨主种子，仅完整主 quartet）

| method | stream | quartets | mean delta_both | mean delta_gap | mean delta_speed | mean interaction | reverse | rescue |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| WideExplore | discovery | 3 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 |
| VerifyFirst | discovery | 2 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 |

碰撞率按条件（完整主 quartet 内，池化）：

- WideExplore / discovery: 00=0.0000, 10=0.0000, 01=0.0000, 11=0.0000
- VerifyFirst / discovery: 00=0.0000, 10=0.0000, 01=0.0000, 11=0.0000

## 每个 master_seed × method 的独立结果（discovery/audit 严格分离）

| master_seed | method | stream | quartets | mean delta_both | mean delta_gap | mean delta_speed | mean interaction | reverse | rescue |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 20261011 | WideExplore | discovery | 3 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 |
| 20261011 | VerifyFirst | discovery | 2 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 |

每个 master_seed × method 的独立审计（audit 流，按提名 anchor）：


## 跨主种子汇总（探索性）

> 跨主种子的池化统计仅为探索性参考：正式设计只有少量主种子，样本很小，不提供正式的置信区间或显著性结论；单个 reverse/rescue 配对不构成稳定反转。

- VerifyFirst|discovery：种子数=1，池化 mean delta_both=0.0000，跨种子均值=0.0000，跨种子样本标准差=n/a
  - 每种子 mean delta_both：{'20261011': 0.0}
- WideExplore|discovery：种子数=1，池化 mean delta_both=0.0000，跨种子均值=0.0000，跨种子样本标准差=n/a
  - 每种子 mean delta_both：{'20261011': 0.0}

## 失败 / 中断 / 不完整 quartet（如实记录）

- 错误 episodes：**0**；中断 episodes：**0**；已发起但无结果：**0**
- 不完整 quartet：**0**

### 重复运行（不作为独立科学证据）

- 同 (master_seed, method, anchor, repetition, stream) 的二次完整运行：**1**（如 smoke 确定性重放）。已在主统计中排除。
  - seed 20261011 / WideExplore / discovery / anchor-0000 rep 0 run_id=smoke_WideExplore_20261011_20261012T051718866+0000_75021ebe

## 图表

- 四条件配对结果：`D:\SafeFlipLab\reports\smoke\figure_1_paired_condition_outcomes.png`
- 每 anchor 风险差点估计图（无置信区间：零方差）：`D:\SafeFlipLab\reports\smoke\figure_2_forest_delta_both.png`
- discovery 到独立审计点估计对比：数据不足，未生成（不编造数值）

## 探索性连续安全裕度分析（非协议指标）

> 探索性连续安全裕度分析：不是冻结协议的指标，不是正式证据，不构成真实道路安全结论。它只描述 dev_seed 样本下已付费产生的真实 episode 中，连续代理量（最小前向 TTC 等）的条件间配对差。负的 TTC 差表示该干预在这一个仿真 episode 中使自车更接近碰撞，但不等于发生碰撞，也不得外推到其他场景或真实世界。

| method | stream | quartets | mean TTC(00) | mean TTC(10) | mean TTC(01) | mean TTC(11) | mean ΔTTC(both) | mean ΔTTC(gap) | mean ΔTTC(speed) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| WideExplore | discovery | 3 | 1.2025 | 1.1219 | 1.1542 | 0.9867 | -0.2158 | -0.0805 | -0.0483 |
| VerifyFirst | discovery | 2 | 1.2192 | 0.9877 | 1.1732 | 0.9406 | -0.2786 | -0.2315 | -0.0460 |

- ΔTTC(both) = TTC(11) − TTC(00) 的逐 quartet 配对差均值；负值表示组合干预降低了最小前向 TTC（更接近碰撞但不等于碰撞）。
- 该分析只重读已付费产生的原始 episode 记录，未启动任何新仿真。
- ΔTTC(both) 逐锚点描述范围（min–max，**非置信区间**）：VerifyFirst/discovery: [-0.3459, -0.2113]；WideExplore/discovery: [-0.3459, -0.0901]。
- **种子无关性警示**：本场景中 sim_seed 只随机化 ramp 车的 IDM 指数；最小前向 TTC 恒由 lead 车决定且发生在种子无关的时间窗内，因此同一 (anchor, condition) 的 ΔTTC 在不同 repetition 间逐位相同——重复种子不构成对 TTC 指标的独立重采样。
- 同 isolation key 的二次完整运行（如 smoke 确定性重放）：**1** 个，已按主统计规则排除，不计入独立证据。
- 探索性 TTC 裕度点估计图（非协议，无置信区间）：`D:\SafeFlipLab\reports\smoke\figure_4_margin_forest_ttc.png`

## 边界声明

- 以上数字只来自真实 HighwayEnv 仿真记录；dev_seed 结果不是正式证据。
- quartet 仅由同一 run 内的四条件组成；不同 master_seed 或不同 run 批次不混并。
- discovery 与 audit 严格分离，审计从不回灌提名。
- 重复运行（如 smoke 确定性重放）不计入独立科学证据。
- 单个 reverse pair 不构成稳定反转；请同时查看 rescue 对照。
- 缺失/不完整 quartet 已排除，不计入分子或分母。
- 探索性连续安全裕度（TTC 等）不是协议指标：负 ΔTTC 不等于碰撞，不得作为正式证据或真实道路安全结论；ΔTTC 是确定性闭环节点的属性（种子只随机化 ramp nuisance 车），不是随机碰撞风险的反转。

## 预算账附录（真实账本；失败/中断/未知同样计费）

| phase | scope | cap | launched | completed | error | interrupted | pending/unknown | unused slots |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| smoke | smoke | 24 | 24 | 24 | 0 | 0 | 0 | 0 |

- 未用 slots 不得挪用；已发起但无结果的尝试保守记为 pending/unknown 并计费。
