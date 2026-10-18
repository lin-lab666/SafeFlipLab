# 账本对账报告（LEDGER RECONCILIATION）

**日期**：2026-10-16（GMT+8）　│　**执行者**：WorkBuddy（结题执行）
**范围**：V01 与 V02 的**全部**账本、原始记录与历史作废运行的独立对账
**本轮新增真实仿真**：**0**（纯只读核对 + 离线派生）
**授权依据**：《SafeFlipLab｜自主完成结题任务》第三节 B；绝对安全边界（五）未被触碰。

---

## 0. 结论速览

| 项 | 结论 |
|---|---|
| 有效账本（可作为证据） | V01 **264** + V02 **264** = **528** 次真实 episode |
| 历史**真实发起总数**（含作废） | V01 **484** + V02 **264** = **748** 次 |
| 磁盘原始记录 | **748** 个 JSON，与上完全一致 |
| 孤儿 launch（无 outcome） | **0**（V01、V02 各自） |
| 账本 ↔ 磁盘 一致性 | **双向 1:1，无缺失、无未登记文件** |
| 重复 episode_key | **0** |
| 失败记录是否被删除 | **否**（作废运行完整留痕） |
| 重新计费 / 伪造成功 | **无** |
| 协议偏离 | **2 项**（见 §5），均**已留痕且未抹除** |

---

## 1. V01 有效账本（`runs/episode_ledger.csv`）

| 项目 | 值 |
|---|---:|
| 数据行 | **528**（launch 264 + outcome 264） |
| smoke | **24**（24 completed） |
| pilot | **240**（240 completed） |
| 孤儿 launch | **0** |
| 重复 episode_key | **0** |
| 原始 JSON 与账本 `raw_path` 的交集 | **264 / 264**（声明缺失 0，未登记 0） |
| 碰撞 | **全部 `ego_collision = 0`** |
| formal | **0**（从未授权执行） |

## 2. V01 历史作废运行（`runs/episode_ledger.csv.buggy_pilot_run1` + `runs/_buggy_pilot_run1/`）

> **这是本项目最重要的历史成本项，不得因有效账本只记 264 次而被抹去。**

| 项目 | 值 |
|---|---:|
| 备份账本数据行 | **488**（launch 244 + outcome 244） |
| 其中 smoke | **24** |
| 其中 **pilot（作废）** | **220** |
| 作废 pilot 的 outcome 状态 | **全部 completed**（仿真确实跑完） |
| 作废 pilot 的原始 JSON（`runs/_buggy_pilot_run1/`） | **220** 个 |
| 与有效账本的重叠 | smoke **24/24 完全重叠**（同一批 smoke）；pilot 的 `run_id` **重叠 0**，内容键重叠 220（同 (anchor, rep, cond, method, stream) 但**重新模拟**过） |

**口径说明（防止把两个数看成矛盾）**：
- 文件名的数字 **244** = 备份账本的**总 launch 行**（= 24 smoke + 220 pilot）；
- **220** = 其中**作废的 pilot** 部分。
- 二者**不矛盾**，只是范围不同。历史文档曾以「220 次无效 pilot」和「244」分别表述，本报告统一为：
  **作废 pilot = 220；备份账本总行 = 244。**

**为何作废**：首轮 pilot 存在**阶段隔离缺陷**，不同方法/阶段的行被错误地视作同一隔离键，
使账本的自洽性被破坏。该轮被**整体作废并备份**，随后以修复后的代码**重新运行** 240 次有效 pilot。
作废轮次的仿真**确实消耗了真实算力**，因此计入历史成本，但**不作为科学证据**。
旁证：`runs/manifest_pilot_summary.json.stale_zero_backup`（该缺陷的产物：
`episodes_launched = 0` 却记录 `pilot_wall_time_s = 177.27`，正是"跑了但没记上"的症状）。

**V01 历史真实发起总数 = 24 + 220 + 240 = 484。**

## 3. V02 有效账本（`v02/runs/<phase>/episode_ledger.csv`）

| 项目 | smoke | pilot |
|---|---:|---:|
| launch / outcome | **24 / 24** | **240 / 240** |
| 孤儿 launch | **0** | **0** |
| 重复 episode_key | **0** | **0** |
| `budget_scope` | `v02-smoke` ×24 | `v02-pilot` ×240 |
| exit_status | completed **23** + error **1（D37）** | completed **240** |
| 原始 JSON 数 | **24** | **240** |
| 账本 `raw_path` ↔ 磁盘 | **24/24 双向 1:1** | **240/240 双向 1:1** |
| run_id 数 | 7 | 60 |

**V02 无作废运行**：不存在第二批被丢弃的 episode。
（唯一异常是 D37：**1 个** smoke episode 的真实仿真已执行但归档失败，**已计费、已记 error、未重跑**——
它同时体现为 smoke 的 `n_primary_quartets = 6` 与 `n_usable_quartets = 5` 之差。）

**V02 历史真实发起总数 = 264。**

## 4. 全局汇总

| 版本 | 有效活动账本 | 历史真实发起 | 差额（作废） | 说明 |
|---|---:|---:|---:|---|
| V01 | 264 | **484** | **220** | 首轮 pilot 因隔离缺陷作废（保留原始记录） |
| V02 | 264 | **264** | 0 | 无作废运行；D37 是已计费的 error |
| **合计** | **528** | **748** | **220** | 磁盘原始 JSON 亦为 **748** |

## 5. 协议偏离（如实记录，未被消除）

| # | 偏离 | 处置 | 是否影响证据 |
|---|---|---|---|
| P-1 | **V01 首轮 pilot 的隔离缺陷** → 220 次真实 episode 作废 | 整体备份（账本 + 220 原始 JSON），代码修复后**重新运行** 240 次 | **不影响**：作废轮次**从不混入**统计 |
| P-2 | **V01 账本 2 个 `run_id` 的方法标签错误（F-06）** | `method` 列经 `sim_seed`（SHA-256 含 method）判定为**权威正确**；仅 `run_id` **字符串**标签错 | **不影响**任何 Y 值/种子/锚/统计量（见 `docs/DECISION_LOG.md` D27） |
| P-3 | **V02 D37**：1 个 smoke episode 归档失败 | 计费 1 次、记 error、**未重跑**；已使 1 个 quartet 不可用 | **不影响** pilot 结论（smoke 为管道验证） |
| P-4 | **V02 D42**：审计种子标签硬编码 → 两方法共享同一次审计模拟 | 修复代码 + 回归测试；**4 个 episode（16.7%）重复计费** | **影响辅助方法比较**：该比较**永久不独立**，已披露 |
| P-5 | **V02 D43**：M2 曾按文件名通配读取 episode | 修复为以账本 `raw_path` 为准 + 回归测试 | **仅影响 M2**；已更正并披露 |

**未发生的偏离**：无重跑已发起尝试、无跨阶段借用预算、无免费重试、无删除失败记录、无伪造成功。

## 6. 复现命令（全部零 episode）

```powershell
cd D:\SafeFlipLab
# V01 有效账本与磁盘一致性
.\.venv\Scripts\python.exe -c "import csv;from pathlib import Path;r=[x for x in csv.DictReader(open('runs/episode_ledger.csv',newline='',encoding='utf-8')) if x.get('row_type')];d={Path(x['raw_path']).resolve() for x in r if x['row_type']=='outcome'};k={p.resolve() for p in Path('runs').glob('*/*.json')};print('ledger',len(r),'disk',len(k),'missing',len(d-k),'undeclared',len(k-d))"
# V02 两阶段
cd v02
..\.venv\Scripts\python.exe -c "import csv;from pathlib import Path;[print(ph,[x['row_type'] for x in csv.DictReader(open(f'runs/{ph}/episode_ledger.csv',newline='',encoding='utf-8')) if x.get('row_type')].count('launch')) for ph in ('smoke','pilot')]"
# 历史作废成本（必须保留）
cd ..
.\.venv\Scripts\python.exe -c "import csv;r=[x for x in csv.DictReader(open('runs/episode_ledger.csv.buggy_pilot_run1',newline='',encoding='utf-8')) if x.get('row_type')=='launch'];import collections;print(len(r),collections.Counter(x['phase'] for x in r))"
```

## 7. 边界声明

- 本对账**未运行任何真实 episode**、**未启动 formal**、**未重新运行 smoke/pilot**。
- **未修改**任何账本行、原始记录或冻结配置；**未删除**任何失败记录。
- 本报告为**只读核对**的产物；所有数字均可由 §6 命令独立复算。
