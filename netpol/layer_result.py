"""Result of analyzing a single layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Hashable

import pandas as pd


@dataclass
class LayerResult:
    """Outcome of running the polarization pipeline on one layer.

    ``was_analyzed`` is True iff scoring completed and a dip test was run.
    When a layer is skipped, ``skip_reason`` explains why (instead of the
    original script's silent ``except: continue``).
    """

    layer_id: Hashable
    n_nodes: int
    n_edges: int
    influencers: list
    scores: pd.DataFrame | None = None
    dip_statistic: float | None = None
    p_value: float | None = None
    adjusted_p_value: float | None = None
    is_polarized: bool | None = None
    skip_reason: str | None = None

    @property
    def was_analyzed(self) -> bool:
        return self.skip_reason is None and self.p_value is not None
