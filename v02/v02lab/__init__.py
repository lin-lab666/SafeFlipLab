"""V02 isolated offline development package.

Boundaries (see ``v02/README.md``):

* standard library only — no ``safefliplab`` (V01) and no ``cornercaselab``
  simulator/policy imports;
* every research parameter must come from an explicit PROPOSED config or an
  unimplemented interface — **no arbitrary defaults** masquerading as research
  decisions (UNSET parameters raise :class:`v02lab.schema.UnsetParameterError`);
* nothing here runs a real HighwayEnv episode.
"""

__all__ = [
    "schema",
    "conditions",
    "ttc_state",
    "ledger21",
    "stats_anchor",
    "reporting",
    "fake_adapter",
    "anchors",
    "quartet",
    "adapter_real",
    "runner",
    "methods",
    "phases",
    "report",
    "cli",
]

PROTOCOL_ID_V02 = "SafeFlipLab-v02"
OFFLINE_ONLY = False  # since 2026-10-15 the V02 dev phase runs real episodes
