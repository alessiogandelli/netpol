import networkx as nx
import pytest

from netpol import analyze_layer, analyze_layers
from netpol.config import PolarizationConfig
from netpol.ideology import LatentIdeologyScorer

from .fixtures import FakeIdeologyScorer, sparse_layer, star_graph


def _bimodal_layer():
    """Two influencers, each retweeted by a camp of users -> bimodal scores."""
    g = nx.DiGraph()
    for i in range(50):
        g.add_edge(f"c1_{i}", "i1")
    for i in range(50):
        g.add_edge(f"c2_{i}", "i2")
    return g


def test_analyze_layer_end_to_end():
    g = _bimodal_layer()
    config = PolarizationConfig(n_influencers=2, min_edges=1)
    scorer = LatentIdeologyScorer(min_sources=1)
    res = analyze_layer(g, config, scorer)
    assert res.was_analyzed
    assert res.p_value is not None
    assert res.dip_statistic is not None
    assert res.is_polarized is True  # two-camp distribution is non-unimodal


def test_analyze_layer_skips_below_min_edges():
    res = analyze_layer(sparse_layer(), PolarizationConfig())
    assert not res.was_analyzed
    assert "min_edges" in res.skip_reason


def test_analyze_layer_skip_on_scorer_failure():
    g = star_graph()

    class ExplodingScorer:
        def score(self, edges, n_dimensions):
            raise ValueError("boom")

    res = analyze_layer(g, PolarizationConfig(min_edges=1), ExplodingScorer())
    assert not res.was_analyzed
    assert res.skip_reason.startswith("scoring_failed")


def test_analyze_layer_rejects_undirected():
    g = nx.Graph()
    g.add_edge("a", "b")
    with pytest.raises(TypeError):
        analyze_layer(g, PolarizationConfig())


def test_analyze_layer_rejects_multidigraph():
    g = nx.MultiDiGraph()
    g.add_edge("a", "b")
    with pytest.raises(TypeError):
        analyze_layer(g, PolarizationConfig())


def test_analyze_layers_applies_fdr():
    # Two identical polarized layers: raw p small, FDR-adjusted still small.
    layers = {"l1": _bimodal_layer(), "l2": _bimodal_layer()}
    config = PolarizationConfig(n_influencers=2, min_edges=1, fdr_correction=True)
    scorer = LatentIdeologyScorer(min_sources=1)
    results = analyze_layers(layers, config, scorer)
    assert results["l1"].adjusted_p_value is not None
    assert results["l2"].adjusted_p_value is not None
    assert results["l1"].is_polarized is True


def test_analyze_layers_excludes_layers():
    layers = {"l1": _bimodal_layer(), "noise": sparse_layer()}
    config = PolarizationConfig(
        n_influencers=2, min_edges=1, exclude_layers=("noise",)
    )
    results = analyze_layers(layers, config, LatentIdeologyScorer(min_sources=1))
    assert results["noise"].skip_reason == "excluded by config.exclude_layers"
    assert results["noise"].is_polarized is None


def test_analyze_layers_without_fdr():
    layers = {"l1": _bimodal_layer()}
    config = PolarizationConfig(n_influencers=2, min_edges=1, fdr_correction=False)
    results = analyze_layers(layers, config, LatentIdeologyScorer(min_sources=1))
    assert results["l1"].adjusted_p_value is None
