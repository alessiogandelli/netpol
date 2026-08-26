"""The polarization pipeline.

Two layers, mirroring the API contract in the design spec:

* ``analyze_layer`` -- the primitive: one directed graph in, one
  ``LayerResult`` out.  Fully testable in isolation.
* ``analyze_layers`` -- thin orchestration over ``dict[layer_id, DiGraph]``
  that runs the primitive per layer and applies the one genuinely cross-layer
  step: Benjamini-Hochberg FDR correction across all layers' p-values.

Design constraints enforced here (see the engineering spec):

* Directed graphs only -- ``TypeError`` on ``Graph``/``MultiDiGraph``.
* No bare ``except:`` anywhere; every failure path sets a human-readable
  ``skip_reason``.
"""

from __future__ import annotations

from typing import Hashable

import networkx as nx

from netpol.bimodality import apply_fdr_correction, dip_test
from netpol.config import PolarizationConfig
from netpol.edges import build_influencer_edges
from netpol.ideology import LatentIdeologyScorer
from netpol.influencers import select_influencers
from netpol.layer_result import LayerResult
from netpol.scoring import IdeologyScorer


def analyze_layer(
    graph: nx.DiGraph,
    config: PolarizationConfig,
    ideology_scorer: IdeologyScorer | None = None,
) -> LayerResult:
    """Run the polarization pipeline on a single directed graph.

    Args:
        graph: A directed graph (``a -> b`` = "a retweets b").
        config: Run configuration.
        ideology_scorer: Optional scorer.  Defaults to
            :class:`netpol.ideology.LatentIdeologyScorer`.

    Returns:
        A ``LayerResult``.  ``is_polarized`` reflects the raw p-value only;
        FDR correction is applied later by ``analyze_layers``.
    """
    _require_digraph(graph)

    result = LayerResult(
        layer_id=None,
        n_nodes=graph.number_of_nodes(),
        n_edges=graph.number_of_edges(),
        influencers=[],
    )

    if graph.number_of_edges() < config.min_edges:
        result.skip_reason = (
            f"below min_edges ({graph.number_of_edges()} < {config.min_edges})"
        )
        return result

    influencers, _ = select_influencers(
        graph, config.influencer_strategy, config.n_influencers
    )
    result.influencers = influencers

    edges = build_influencer_edges(graph, influencers)
    if edges.empty:
        result.skip_reason = "no edges into selected influencers"
        return result

    scorer = ideology_scorer or LatentIdeologyScorer()

    try:
        scores = scorer.score(edges, config.ideology_dimensions)
    except Exception as exc:  # scorer is a plug point; report, don't crash
        result.skip_reason = f"scoring_failed: {type(exc).__name__}: {exc}"
        return result

    result.scores = scores

    try:
        dip, p_value = dip_test(scores["score_1"].to_numpy())
    except Exception as exc:
        result.skip_reason = f"dip_test_failed: {type(exc).__name__}: {exc}"
        return result

    result.dip_statistic = dip
    result.p_value = p_value
    result.is_polarized = p_value < config.significance_level
    return result


def analyze_layers(
    layers: dict[Hashable, nx.DiGraph],
    config: PolarizationConfig,
    ideology_scorer: IdeologyScorer | None = None,
) -> dict[Hashable, LayerResult]:
    """Run ``analyze_layer`` per layer and apply FDR correction across layers.

    Args:
        layers: Mapping ``layer_id -> DiGraph``.
        config: Run configuration.  ``exclude_layers`` entries are skipped
            with a ``skip_reason``.
        ideology_scorer: Optional scorer; defaults to the built-in one.

    Returns:
        Mapping ``layer_id -> LayerResult``.  When ``config.fdr_correction``
        is True, ``adjusted_p_value`` is set on analyzed layers and
        ``is_polarized`` is re-evaluated against the adjusted p-value.
    """
    results: dict[Hashable, LayerResult] = {}

    for layer_id, graph in layers.items():
        result = analyze_layer(graph, config, ideology_scorer)
        result.layer_id = layer_id
        if layer_id in config.exclude_layers:
            result.skip_reason = "excluded by config.exclude_layers"
            result.dip_statistic = None
            result.p_value = None
            result.scores = None
            result.is_polarized = None
        results[layer_id] = result

    if config.fdr_correction:
        raw = {
            layer_id: r.p_value
            for layer_id, r in results.items()
            if r.p_value is not None
        }
        adjusted = apply_fdr_correction(raw)
        for layer_id, r in results.items():
            if r.p_value is None:
                continue
            r.adjusted_p_value = adjusted[layer_id]
            r.is_polarized = adjusted[layer_id] < config.significance_level

    return results


def _require_digraph(graph: nx.DiGraph) -> None:
    if isinstance(graph, nx.MultiDiGraph):
        raise TypeError("MultiDiGraph is not supported")
    if not isinstance(graph, nx.DiGraph):
        raise TypeError(
            "expected a networkx.DiGraph; undirected and multigraphs are not "
            "supported (the edge direction encodes who retweets whom)"
        )
