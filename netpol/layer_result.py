"""Result of analyzing a single layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable

from netpol.types import LayerId, ScoreTable


@dataclass
class LayerResult:
    """Outcome of running the polarization pipeline on one layer.

    ``was_analyzed`` is True iff scoring completed and a dip test was run.
    When a layer is skipped, ``skip_reason`` explains why (instead of the
    original script's silent ``except: continue``).

    Attributes:
        layer_id: Layer identifier (``None`` for a bare ``analyze_network``).
        n_nodes: Number of nodes in the layer's graph.
        n_edges: Number of directed edges in the layer's graph.
        influencers: Ids of the selected influencer nodes.
        scores: ``ScoreTable`` (DataFrame indexed by node id with columns
            ``score_1..score_n``), or ``None`` if the layer was skipped.
        dip_statistic: Hartigan's dip statistic, or ``None`` if skipped.
        p_value: Raw dip-test p-value, or ``None`` if skipped.
        adjusted_p_value: Benjamini-Hochberg adjusted p-value (only set by
            ``analyze_layers`` when ``fdr_correction`` is on).
        is_polarized: Whether the (adjusted, if available) p-value is below
            ``config.significance_level``.
        skip_reason: Human-readable reason when the layer was skipped.
    """

    layer_id: Hashable | None
    n_nodes: int
    n_edges: int
    influencers: list[Hashable]
    scores: ScoreTable | None = None
    dip_statistic: float | None = None
    p_value: float | None = None
    adjusted_p_value: float | None = None
    is_polarized: bool | None = None
    skip_reason: str | None = None

    @property
    def was_analyzed(self) -> bool:
        return self.skip_reason is None and self.p_value is not None


Results = dict[LayerId, LayerResult]
"""Mapping ``layer_id -> LayerResult`` returned by :func:`netpol.analyze_layers`."""


__all__ = ["LayerResult", "Results"]
