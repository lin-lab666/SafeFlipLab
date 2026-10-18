# Attribution — SafeFlipLab

Every third-party library is used as an **installed dependency** through its
public interface. Nothing is copied into, vendored in, or redistributed by
this repository.

| Dependency | How it is used here | Bundled? |
|---|---|---|
| CornerCaseLab 0.3.0 | scenario schema, HighwayEnv merge adapter, frozen `boundary` controller (imported) | No |
| HighwayEnv | road geometry, vehicle dynamics, IDM background traffic, action implementation (subclassed) | No |
| Gymnasium | environment interface, reached through HighwayEnv | No |
| NumPy | numerical/runtime functionality (transitive) | No |
| Pillow | optional GIF output (not used by default runs) | No |
| matplotlib | report figures (`safefliplab/report.py`) | No |
| pygame | transitive rendering dependency of HighwayEnv; not imported directly | No |

CornerCaseLab's own files are Apache-2.0 ((c) 吴昊霖 / lin-lab666) and are
**not** relicensed by this project. The `boundary` controller, the scenario
bounds and the merge adapter belong to that project; SafeFlipLab adds the
quartet protocol, the two budgeted methods, the audit isolation and the
statistics on top.

This project was prepared with AI assistance. The owner should review,
understand and validate it, and follow any venue's disclosure requirements.
Do not claim that the simulator or upstream behavioural models were
independently authored here.
