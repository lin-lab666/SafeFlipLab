# V02 预算总账（含全部历史）

> 权威来源为各账本文件；本文件由 `.workbuddy/tmp_audit/budget_all.py` 只读生成。
> **失败 / 中断 / UNKNOWN 均计入 `launched`**，无免费重试。

| 运行 | 授权上限 | 已发起 | 完成 | 错误 | 中断 | 待定/未知 | run 数 | 账本 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| V01 smoke（历史） | 24 | **24** | 24 | 0 | 0 | 0 | 6 | `runs/episode_ledger.csv` |
| V01 pilot 有效（历史） | 240 | **240** | 240 | 0 | 0 | 0 | 60 | `runs/episode_ledger.csv` |
| V01 pilot 无效首轮（历史留痕） | 240 | **220** | 220 | 0 | 0 | 0 | 55 | `runs/episode_ledger.csv.buggy_pilot_run1` |
| V01 formal | 12800 | **0** | 0 | 0 | 0 | 0 | 0 | **未授权，未启动** |
| V02 smoke | 24 | **24** | 23 | 1 | 0 | 0 | 7 | `v02/runs/smoke/episode_ledger.csv` |
| V02 pilot | 240 | **240** | 240 | 0 | 0 | 0 | 60 | `v02/runs/pilot/episode_ledger.csv` |

## 汇总

- V01 **有效**真实 episode 合计：**264**（smoke 24 + 有效 pilot 240）
- V01 含无效首轮合计：**484**（PD-01 偏离：pilot 单次授权 240，实际累计 460）
- V02 真实 episode 合计：**264**（smoke + pilot）
- **两个版本合计真实 episode：748**

## 关键约束（复述）

- V01 预算**已耗尽**，不得重跑、不得补跑、不得改名重置；本文件不修改任何历史行。
- V02 smoke（≤24）与 V02 pilot（≤240）是**独立授权**，**不可互相借用**；
  V02 使用独立 21 列账本，按 `budget_scope` 独立计费。
- **不存在**任何 formal（12,800）运行；V01 formal CLI 安全门完好。
- 本项目**不创建** V03，不通过新版本获取额外预算。
