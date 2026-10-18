# v02 — V02 离线开发区域（与 V01 隔离）

> **状态（2026-10-15 更新）：V02 协议已由项目负责人在授权范围内自主冻结
> （`configs/v02_frozen_v1.json`，全部参数 `FROZEN`），并已在该冻结协议下完成
> V02 smoke（24/24）与 V02 pilot（240/240）真实运行。**
>
> 冻结记录见 `../docs/V02_PROTOCOL_FROZEN.md`；设计决策见 `../docs/AUTONOMOUS_DECISIONS.md`（D28–D40）；
> 进度见 `../docs/AUTONOMOUS_PROGRESS.md`；报告见 `../reports/v02/`。
>
> ⚠️ 该冻结是**项目负责人的自主决定**，**不是**外部同行评审，**不得**表述为「已获外部批准」。
> V01 未批准的 D4/D5/D6 **并未**因此获得批准。
> V02 **没有** formal（12,800）入口，本项目**不允许**创建 V03 以获取额外预算。

## 1. 边界（硬约束，写死在本 README）

1. **不导入** `safefliplab`（V01 包），**不修改** `configs/formal_v01.json` 或 V01 源码；
2. 仅在 `v02lab/adapter_real.py` 中**调用**上游公开接口 `cornercaselab.simulator.evaluate`
   （不改其源码、不改控制器/物理语义）；pure-function 模块仍**只用标准库**，上游 bounds 以参数传入；
3. 真实仿真**只允许**在冻结协议下、经由预算受控的 `smoke` / `pilot` 入口运行
   （硬上限 24 / 240，独立账本计费）；`FakeAdapterV02` 是**测试替身**（`is_test_double=True`），
   永不消费仿真预算；
4. **不发布** GitHub、**不启动**任何 formal；
5. 所有研究参数只能来自**显式冻结配置**；**禁止**以任意默认值冒充科研决断
   （任何非 `FROZEN` 参数在取用时抛 `UnsetParameterError`）。

## 2. 目录结构

```
v02/
  README.md                       # 本文件
  v02lab/                         # 隔离包（仅标准库）
    __init__.py
    schema.py                     # 配置 schema 校验（强制显式 status，杜绝任意默认）
    conditions.py                 # 四条件合法性 / 共享扰动 / SHA256 派生（纯函数）
    ttc_state.py                  # TTC 三层状态模型（纯函数）
    ledger21.py                   # 独立 canonical 21 列账本（离线）
    stats_anchor.py               # 锚级估计/区间 + 受门控的检验（默认 PENDING）
    reporting.py                  # 报告/统计接口（合成数据）
    fake_adapter.py               # 合成数据测试替身（非真实仿真）
    anchors.py                    # V02 锚域 + 确定性拒绝采样
    quartet.py                    # 一次重复 = 共享扰动 + 四条件
    adapter_real.py               # 真实适配（调用上游 evaluate + 轨迹重算 TTC）
    runner.py                     # 计费→执行→归档（先计费再仿真）
    methods.py                    # 两方法提名规则（连续终点版）
    phases.py                     # smoke / pilot 编排（断点恢复不重跑）
    report.py                     # 统计 / 门槛 / CSV / 图表
    cli.py                        # doctor / smoke / pilot / report
  configs/
    v02_proposed_schema.json      # 参数 schema（每个参数强制 status）
    v02_proposed_config.json      # 早期 PROPOSED 草案（已被冻结配置取代，保留存档）
    v02_frozen_v1.json            # **冻结的 V02 协议（全部 FROZEN）**
  runs/                           # V02 独立账本 + 原始 episode 记录（21 列）
  reports/                        # V02 报告 / CSV / 图
  tests/                          # unittest（合成数据 + 临时账本，零真实 episode）
```

## 3. 运行测试（零真实 episode）

```bash
cd D:/SafeFlipLab/v02
python -m unittest discover -s tests -v
```

## 4. 与 V02 研究提案的对应

| 提案章节 | 本区构件 |
|---|---|
| §3.4 TTC 三层处理 | `v02lab/ttc_state.py` |
| §2.2 `I_log` 定义域 | `v02lab/ttc_state.py::log_interaction` |
| §5 四条件配对 / 因子结构 | `v02lab/conditions.py` |
| §4 共享扰动抽样 / 种子派生 | `v02lab/conditions.py` |
| §8 锚级估计 / `PENDING` 门控 | `v02lab/stats_anchor.py` |
| §9 canonical 21 列账本 | `v02lab/ledger21.py` |
| §6 / §3 报告与统计接口 | `v02lab/reporting.py` |

> 本区的通过**不**代表协议获批；仍在 `docs/V02_PROTOCOL_REVIEW_CHECKLIST.md` 的人工裁决之下。
