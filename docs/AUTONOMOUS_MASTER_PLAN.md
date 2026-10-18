# AUTONOMOUS_MASTER_PLAN — SafeFlipLab 自主执行总计划

> 授权来源：《SafeFlipLab — 项目总负责人自主执行授权》（2026-10-15）。
> 本人担任首席研究工程师 / 项目负责人 / 质量验收负责人，负责制定计划、执行、测试、
> 修复、审计与交付。本文件记录**实际状态与证据**，不猜测。
>
> 最后更新：2026-10-15（GMT+8）

---

## 0. 硬边界（全程不可突破）

| # | 边界 | 状态 |
|---|---|---|
| B1 | 唯一写入路径 `D:\SafeFlipLab`；禁止改动 `D:\CornerCaseLab` | 遵守 |
| B2 | 禁止改写 V01 冻结配置（`configs/formal_v01.json`）、V01 旧账本、历史原始记录 | 遵守 |
| B3 | 禁止未经授权启动 formal（12,800 次） | 遵守 |
| B4 | V02 新增真实预算上限：**smoke ≤ 24**、**pilot ≤ 240**；**不可互相借用**；失败/中断/UNKNOWN 均计费 | 遵守 |
| B5 | 禁止管理员提权、改系统 Python、放开全局权限 | 遵守 |
| B6 | 禁止自动公开 GitHub、投稿、付费购买、外发私有数据 | 遵守 |
| B7 | 不得把未审核的科研方案宣称为正式批准 | 遵守 |
| B8 | 不得创建 V03 或任何版本以获取额外预算 | 遵守 |

## 1. 预算总账（权威 = 各账本）

| 版本 | 阶段 | 上限 | 已发起 | 剩余 | 账本 |
|---|---|---:|---:|---:|---|
| V01 | smoke | 24 | 24（历史，已耗尽） | 0 | `runs/episode_ledger.csv` |
| V01 | pilot | 240 | 240 有效 + 220 无效（历史，已耗尽） | 0 | 同上 + `runs/episode_ledger.csv.buggy_pilot_run1` |
| V01 | formal | 12800 | 0（未授权） | 12800 | — |
| **V02** | **smoke** | **24** | 见 `AUTONOMOUS_PROGRESS.md` | ≥0 | `v02/runs/episode_ledger.csv` |
| **V02** | **pilot** | **240** | 见 `AUTONOMOUS_PROGRESS.md` | ≥0 | `v02/runs/pilot/episode_ledger.csv` |

> V01 预算已耗尽，**不重跑、不补跑、不改名重置**。V02 为**全新独立预算**，独立账本、独立证据目录。

## 2. 阶段计划与状态

| 阶段 | 内容 | 状态 |
|---|---|---|
| 1 | 审计 V01：核验工程、实验、预算事故、统计结果、已知缺陷 | ✅ DONE |
| 2 | 设计 V02：研究零碰撞根因、真实随机性、连续安全指标适用性 | ✅ DONE |
| 3 | 冻结 V02 协议：问题/终点/场景域/种子/预算/方法/统计/停止条件 | ✅ DONE |
| 4 | 完成 V02 工程：adapter/算法/统计/可视化/错误处理/预算保护/真实数据审计 + 单测 | ✅ DONE |
| 5a | V02 真实 smoke（≤24） | ✅ DONE |
| 5b | V02 真实 pilot（≤240） | ✅ DONE |
| 6 | 统计与真实图表 | ✅ DONE |
| 7 | 中文研究报告 + 英文论文初稿 + 文献综述 + 复现指南 | ✅ DONE |
| 8 | 独立验收（代码 / 统计 / 科研方法）与最终交付 | ✅ DONE |

## 3. 关键技术判断（决定整体路线）

1. **零碰撞根因**：`policy=boundary` 为确定性规则控制器（gap 6.0 m / headway 0.30 s / TTC 0.90 s），
   在 25 s 时域内主动制动维持安全间距 ⇒ 二元碰撞指标结构性接近 0，**不是**仿真故障。
2. **V01 的致命统计缺陷**：`sim_seed` 只随机化 IDM NPC 的 `DELTA`；lead 以「初速 = 目标速度」
   处于自由流 ⇒ 其轨迹与种子无关；min-TTC 恒由 lead 决定 ⇒ **同一锚的条件差异跨 repetition
   逐位相同**，导致 repetition 与 audit 不提供独立信息。
3. **V02 的解法（本计划核心）**：
   - 主终点改为**连续最小前向 TTC**（有方差、可区间估计）；
   - 引入**锚内共享扰动抽样**（front_gap / front_speed / ego_speed 抖动），使不同 repetition
     的初始条件真的不同 ⇒ repetition 重新携带信息；
   - 扰动**纯场景层**实现，直接复用上游 `cornercaselab.simulator.evaluate()`，
     **不修改仿真物理语义**（G1/G2/G9 构造性满足）。
4. **统计推断**：以 **anchor 为独立单元**；锚级 cluster bootstrap 区间。
   sign-flip / max-T **保持 PENDING**（抽样假设 A/B/C 未被证明，**不自行批准**）。

## 4. V02 预算分配（冻结）

- **smoke（24）**：3 anchors × 2 repetitions × 4 conditions = 24。
- **pilot（240）**：
  - 主研究（反转与交互）：**18 anchors × 3 repetitions × 4 conditions = 216**
  - 辅助 H2（方法比较，独立审计）：**2 methods × 3 nominees × 1 fresh audit quartet = 24**
  - 合计 **240**（恰好用满授权上限；不借用、不超支）

## 5. 交付物清单

| # | 交付物 | 路径 |
|---|---|---|
| 1 | 完整源码与可执行命令 | `safefliplab/`、`v02/v02lab/`、`v02/configs/` |
| 2 | 实际测试报告 | `docs/V10_V02_TEST_RESULTS_20261015.txt`（V02）、`docs/V12_FINAL_V01_TESTS_20261015.txt` / `docs/V12_FINAL_V02_TESTS_20261015.txt`（结题轮最终） |
| 3 | 真实实验账本与全部历史预算统计 | `v02/runs/**`、`runs/episode_ledger.csv`、`docs/V02_BUDGET_LEDGER.md` |
| 4 | V01/V02 科学有效性审计 | `docs/AUDIT_V01_V02.md` |
| 5 | 统计数据与真实图表 | `v02/reports/**` |
| 6 | 中文研究报告 | `reports/v02/REPORT.zh-CN.md` |
| 7 | 英文论文初稿 | `reports/v02/PAPER_DRAFT_EN.md` |
| 8 | 中文教学与复现指南 | `docs/OWNER_GUIDE_V02.zh-CN.md` |
| 9 | 正式评估人工决策清单 | `docs/HUMAN_DECISION_CHECKLIST.md` |
| 10 | 最终交付说明 | `docs/FINAL_DELIVERY.md` |

## 6. 推进规则

- 每完成一个子任务：读本计划 → 找下一项未完成且未阻塞的工作 → 继续执行，不请求分配。
- 一个任务受阻：继续其他可安全执行的任务；仅当关键资源/权限/研究前提不可解时才报 BLOCKED。
- 会话中断前：先持久化状态、真实预算与精确恢复方式（见 `docs/LATEST_HANDOFF.md` 与
  `AUTONOMOUS_PROGRESS.md`）。
- **严禁**循环自启动、重复运行、反复消耗预算。
