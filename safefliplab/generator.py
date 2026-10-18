"""ScenarioGenerator: the shared, deterministic legal-anchor stream.

Both methods and all seeds draw anchors from the *same* stream for a given
master seed. Anchors are sampled with the public ``cornercaselab.domain``
uniform sampler and *rejected* when they are not quartet-legal (any of the
four conditions would fall outside the upstream bounds). Rejection happens
before any simulation, so it costs no episode budget.

Determinism: anchor ``i`` of the stream is a pure function of the master
seed. ``stream_draws`` records how many uniform draws were consumed, so the
sampling process itself is auditable.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cornercaselab.domain import sample_scenario

from .domain import Anchor, anchor_in_domain
from .seeds import anchor_id, anchor_stream_seed, check_seed, derive_seed


class ScenarioGenerator:
    """Deterministic stream of quartet-legal anchors for one master seed."""

    def __init__(self, master_seed: int) -> None:
        check_seed(master_seed)
        self.master_seed = master_seed
        self._stream_seed = anchor_stream_seed(master_seed)
        self._anchors: list[Anchor] = []
        self._draw_index = 0

    def _draw_scenario(self):
        seed = derive_seed(self._stream_seed, "draw", self._draw_index)
        self._draw_index += 1
        return sample_scenario(seed)

    def _next_anchor(self) -> Anchor:
        while True:
            draws_before = self._draw_index
            scenario = self._draw_scenario()
            if anchor_in_domain(scenario):
                index = len(self._anchors)
                return Anchor(
                    index=index,
                    scenario=scenario,
                    stream_draws=self._draw_index - draws_before,
                )

    def anchor(self, index: int) -> Anchor:
        """Return anchor ``index`` (0-based), extending the stream if needed."""
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ValueError(f"anchor index must be a non-negative int, got {index!r}")
        while len(self._anchors) <= index:
            self._anchors.append(self._next_anchor())
        return self._anchors[index]

    def anchors(self, count: int) -> list[Anchor]:
        return [self.anchor(i) for i in range(count)]

    def stream_state(self) -> dict[str, Any]:
        return {
            "master_seed": self.master_seed,
            "stream_seed": self._stream_seed,
            "legal_anchors_so_far": len(self._anchors),
            "uniform_draws_consumed": self._draw_index,
        }

    def save_stream(self, path: str | Path) -> None:
        payload = {
            "protocol": "SafeFlipLab-v01",
            "master_seed": self.master_seed,
            "anchors": [a.to_dict() for a in self._anchors],
        }
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def anchors_for(master_seed: int, count: int) -> list[Anchor]:
    """Convenience: the first ``count`` legal anchors of a master seed stream."""
    return ScenarioGenerator(master_seed).anchors(count)
