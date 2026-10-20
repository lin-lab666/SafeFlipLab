# SafeFlipLab v1.2.0 — Release Notes（待发布，未推送）

- **版本**：v1.2.0
- **性质**：对 v1.1.0 的工程品质增量升级（**非** v1.1.0 的重新标签）。科研数据与
  结论不变（ENGINEERING CLOSEOUT PASS / SCIENTIFIC CLAIM INCONCLUSIVE）。
- **状态**：**本地 Release Candidate**，位于分支 `upgrade/v1.2`。**尚未推送、
  尚未打 tag、尚未发布**（需项目负责人授权）。
- **前一版**：v1.1.0（tag 已发布，main `7d193ac`，保持不动）。

---

## 1. 本版新增

- **`examples/read_real_results.py`** — 只读、纯离线的真实结果展示：读取公开的
  `v02/reports/` 汇总（JSON/CSV/MD），打印结构化 M1/M2/C13/样本量摘要，从公开 CSV
  复算锚级均值并与存储点估计交叉核对，并渲染一张结果图。**零 episode、零 `runs/`
  写入、不导入仿真器**。头部明确标注四类内容（合成 / 真实历史 / 可复算 /
  需私有数据）。
- **`docs/assets/result_summary.png`** — M1 锚级森林图 + 逐锚 `delta_gap` 散点，
  从公开汇总只读生成。
- **README（中/英）升级**：新增「四条件反事实设计如何工作」「真实结果摘要
  （M1/M2/C13）」「关键图表」小节；补 `RELEASE_NOTES.md` 文档索引。
- **`scripts/ci_offline_guard.py`** — 可执行的 CI 离线守卫（见 §4）。
- **`tests/test_ci_offline_guard.py`** — 守卫的正向 + 负向测试（证明守卫真实生效）。

## 2. 本版修复

- **版本号统一为 `1.2.0`**：`pyproject.toml` `version`、`CITATION.cff` `version`、
  `safefliplab/__init__.py` `__version__` 三处此前均为 `0.1.0`（陈旧），现统一为
  `1.2.0`。v1.1.0 仍是已发布的历史 tag，本版不是拿 v1.1.0 冒充 v1.2.0。
- **README 测试口径**：现行测试套件 `V01 227` → `242`（227 为 v1.0 历史口径，
  242 = 227 + 7 项 v1.1 回归测试 + 8 项 v1.2.0 离线守卫测试）；历史处保留 227。
- **README 可见性表述**：移除"私有仓库 / collaborators only"（仓库已公开，改为中性）。
- **第三方许可归属性**：NumPy 误标 MIT 更正为 **BSD-3-Clause**；完整列表
  （HighwayEnv MIT / Gymnasium MIT / NumPy BSD-3-Clause / Pillow HPND /
  matplotlib license / pygame LGPL）在 README 与 `PUBLICATION_SCOPE.md` §6 勘误
  中陈述。冻结的 `docs/PROVENANCE.md` 保持字节不变（仅追加勘误）。

## 3. 科研状态（未变）

- ENGINEERING CLOSEOUT PASS / **SCIENTIFIC CLAIM INCONCLUSIVE**。
- 无安全反转证据；无 p 值、无显著性声明；M1/M2 方向不一致（D43）保留公开；
  D42/D44 历史审计不独立；C13 二元端点近乎无信息（54 quartet 仅 2 次碰撞）；
  有效 528 vs 历史发起 748（含作废 220）；D37 保留；TTC 为 1D 代理量非碰撞概率。
- V01 formal（12,800 episodes）**永久 NO-GO**，本版未解除。

## 4. CI 离线守卫（本版强化）

- `scripts/ci_offline_guard.py` 以**退出码**拦截四类真实仿真入口：子进程启动
  （`subprocess`/`os.system`/`Popen`）、CLI 入口列表形式、真实适配器构造
  （`ScenarioAdapter(` / `RealAdapterV02(`）、真实仿真器导入
  （`cornercaselab.simulator`）。
- `tests/test_ci_offline_guard.py` 用**可执行负向测试**证明：植入的
  `smoke --max-episodes 24` / `pilot` / `formal --confirm` / 真实适配器 / 真实仿真器
  导入均被拦截（FAIL），合法 FakeAdapter/mock 套件不误伤（PASS）。
- **自动触发保持关闭**（`workflow_dispatch` 手动）——本轮**未**开启 push/PR 自动
  触发（涉及 Actions 配额与授权，待项目负责人决定）。

## 5. 数据边界（未变）

- 公开包含：源码、测试、配置样例、结果汇总（`reports/`、`v02/reports/`）、文档。
- 不包含：`runs/`、`v02/runs/`、账本、原始 episode JSON、`_buggy_pilot_run1`。
- 原始数据由项目负责人保存，可合理申请（见 `DATA_AVAILABILITY.md`）。

## 6. 验证（本地实测）

```text
V01 单元测试                        Ran 242, OK (skipped=1)   EXIT 0
V02 单元测试                        Ran 143, OK               EXIT 0
scripts/verify_publication.py       PASS（v1.0 字节级冻结）   EXIT 0
examples/read_real_results.py       真实历史摘要              EXIT 0
scripts/ci_offline_guard.py         合法树 OK；负向 FAIL       EXIT 0 / 1
tests/test_ci_offline_guard.py      Ran 8, OK                 EXIT 0
pip install -e .（全新 venv）       EXIT 0；version 1.2.0
零 runs/ 残留（全部命令之后）
```

## 7. 待授权事项

1. 推送 `upgrade/v1.2` 分支；
2. 打 tag `v1.2.0` 并创建 GitHub Release；
3. （可选）开启 CI push/PR 自动触发（需确认 Actions 配额）。
