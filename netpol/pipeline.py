"""The polarization pipeline.

Three entry points, from simplest to most general:

* ``analyze`` -- the top-level convenience function: pass a single network,
  a multilayer mapping, or a path to any of those (plain GML, multilayer
  GML, or a topiclayers output folder) and get back the matching result
  shape.
* ``analyze_network`` -- the primitive: one directed graph in, one
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

from pathlib import Path

import networkx as nx

from netpol.bimodality import apply_fdr_correction, dip_test
from netpol.config import PolarizationConfig
from netpol.edges import build_influencer_edges
from netpol.ideology import LatentIdeologyScorer
from netpol.influencers import select_influencers
from netpol.io import _read_projected_gml, load_layers, read_multilayer_gml
from netpol.layer_result import LayerResult, Results
from netpol.scoring import IdeologyScorer
from netpol.types import Layers, ScoreTable


def analyze(
    target: nx.DiGraph | Layers | str | Path,
    config: PolarizationConfig,
    ideology_scorer: IdeologyScorer | None = None,
) -> LayerResult | Results:
    """Analyze a single network, a multilayer network, or a path to either.

    The top-level entry point: dispatches to :func:`analyze_network` when
    given a bare ``DiGraph`` (or a path to a plain GML file) and to
    :func:`analyze_layers` when given a ``dict[layer_id, DiGraph]`` (or a
    path to a multilayer GML / topiclayers output folder).

    Args:
        target: A directed graph, a mapping ``layer_id -> DiGraph``, or a
            path to a plain GML file, a multilayer GML file, or a
            topiclayers output folder.
        config: Run configuration.
        ideology_scorer: Optional scorer.  Defaults to
            `netpol.ideology.LatentIdeologyScorer`.

    Returns:
        A ``LayerResult`` for a single network, or a mapping
        ``layer_id -> LayerResult`` for a multilayer network.
    """
    target = _coerce_target(target)
    if isinstance(target, nx.DiGraph):
        return analyze_network(target, config, ideology_scorer)
    return analyze_layers(target, config, ideology_scorer)


def analyze_network(
    graph: nx.DiGraph | str | Path,
    config: PolarizationConfig,
    ideology_scorer: IdeologyScorer | None = None,
) -> LayerResult:
    """Run the polarization pipeline on a single directed network.

    Args:
        graph: A directed graph (``a -> b`` = "a retweets b"), or a path
            to a plain GML file.
        config: Run configuration.
        ideology_scorer: Optional scorer.  Defaults to `netpol.ideology.LatentIdeologyScorer`.

    Returns:
        A ``LayerResult``.  ``is_polarized`` reflects the raw p-value only;
        FDR correction is applied later by ``analyze_layers``.
    """
    graph = _coerce_target(graph)
    if not isinstance(graph, nx.DiGraph):
        raise TypeError(
            "analyze_network expects a single network; got a multilayer "
            "mapping. Use analyze or analyze_layers instead."
        )
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

    # Select influencers 
    influencers, _ = select_influencers( graph, config.influencer_strategy, config.n_influencers)
    result.influencers = influencers

    # Build the subgraph of edges into the selected influencers. a -> b = "a retweets b" so we want edges where the target is an influencer.
    edges = build_influencer_edges(graph, influencers)

    if edges.empty:
        result.skip_reason = "no edges into selected influencers"
        return result

    # Score the edges with the ideology scorer.  This is a plug point; the default scorer is LatentIdeologyScorer.
    scorer = ideology_scorer or LatentIdeologyScorer()

    try:
        scores: ScoreTable = scorer.score(edges, config.ideology_dimensions)
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
    layers: Layers | str | Path,
    config: PolarizationConfig,
    ideology_scorer: IdeologyScorer | None = None,
) -> Results:
    """Run ``analyze_network`` per layer and apply FDR correction across layers.

    Args:
        layers: Mapping ``layer_id -> DiGraph``, or a path to a multilayer
            GML file or a topiclayers output folder.
        config: Run configuration.  ``exclude_layers`` entries are skipped
            with a ``skip_reason``.
        ideology_scorer: Optional scorer; defaults to the built-in one.

    Returns:
        Mapping ``layer_id -> LayerResult``.  When ``config.fdr_correction``
        is True, ``adjusted_p_value`` is set on analyzed layers and
        ``is_polarized`` is re-evaluated against the adjusted p-value.
    """
    layers = _coerce_target(layers)
    if not isinstance(layers, dict):
        raise TypeError(
            "analyze_layers expects a multilayer mapping (or a path to "
            "one); got a single network. Use analyze or analyze_network "
            "instead."
        )
    results: Results = {}

    for layer_id, graph in layers.items():
        result = analyze_network(graph, config, ideology_scorer)
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


def _coerce_target(target: nx.DiGraph | Layers | str | Path) -> nx.DiGraph | Layers:
    """Normalize the entry-point input into a graph or a layer mapping.

    ``DiGraph`` and ``dict`` pass through untouched.  A ``str``/``Path`` is
    loaded: a directory via ``load_layers``, a multilayer GML (first
    non-empty line starts with ``#TYPE``) via ``read_multilayer_gml``,
    anything else as a single plain GML network.
    """
    if isinstance(target, (nx.DiGraph, dict)):
        return target

    if isinstance(target, (str, Path)):
        path = Path(target)
        if not path.exists():
            raise FileNotFoundError(f"network path not found: {path}")
        if path.is_dir():
            return load_layers(path)
        with open(path) as fh:
            first = next((line.strip() for line in fh if line.strip()), "")
        if first.startswith("#TYPE"):
            return read_multilayer_gml(path)
        return _read_projected_gml(path)

    raise TypeError(
        "expected a networkx.DiGraph, a dict[layer_id, DiGraph], or a "
        f"path to either, got {type(target).__name__}"
    )


def _require_digraph(graph: nx.DiGraph) -> None:
    if isinstance(graph, nx.MultiDiGraph):
        raise TypeError("MultiDiGraph is not supported")
    if not isinstance(graph, nx.DiGraph):
        raise TypeError(
            "expected a networkx.DiGraph; undirected and multigraphs are not "
            "supported (the edge direction encodes who retweets whom)"
        )
