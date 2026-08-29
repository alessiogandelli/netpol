import networkx as nx
import pytest

from netpol import analyze, analyze_network, analyze_layers
from netpol.config import PolarizationConfig
from netpol.ideology import LatentIdeologyScorer
from netpol.layer_result import LayerResult

from .fixtures import FakeIdeologyScorer, sparse_layer, star_graph

MULTILAYER_GML = """#TYPE
multiplex

#VERSION
3.0

#LAYERS
1.0,DIRECTED,LOOPS
2.0,DIRECTED,LOOPS

#ACTORS
a
b
c

#EDGES
a,b,1.0
a,c,2.0
"""


def _bimodal_layer():
    """Two influencers, each retweeted by a camp of users -> bimodal scores."""
    g = nx.DiGraph()
    for i in range(50):
        g.add_edge(f"c1_{i}", "i1")
    for i in range(50):
        g.add_edge(f"c2_{i}", "i2")
    return g


def test_analyze_network_end_to_end():
    g = _bimodal_layer()
    config = PolarizationConfig(n_influencers=2, min_edges=1)
    scorer = LatentIdeologyScorer(min_sources=1)
    res = analyze_network(g, config, scorer)
    assert res.was_analyzed
    assert res.p_value is not None
    assert res.dip_statistic is not None
    assert res.is_polarized is True  # two-camp distribution is non-unimodal


def test_analyze_network_skips_below_min_edges():
    res = analyze_network(sparse_layer(), PolarizationConfig())
    assert not res.was_analyzed
    assert "min_edges" in res.skip_reason


def test_analyze_network_skip_on_scorer_failure():
    g = star_graph()

    class ExplodingScorer:
        def score(self, edges, n_dimensions):
            raise ValueError("boom")

    res = analyze_network(g, PolarizationConfig(min_edges=1), ExplodingScorer())
    assert not res.was_analyzed
    assert res.skip_reason.startswith("scoring_failed")


def test_analyze_network_rejects_undirected():
    g = nx.Graph()
    g.add_edge("a", "b")
    with pytest.raises(TypeError):
        analyze_network(g, PolarizationConfig())


def test_analyze_network_rejects_multidigraph():
    g = nx.MultiDiGraph()
    g.add_edge("a", "b")
    with pytest.raises(TypeError):
        analyze_network(g, PolarizationConfig())


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


def test_analyze_dispatches_single_graph():
    config = PolarizationConfig(n_influencers=2, min_edges=1)
    scorer = LatentIdeologyScorer(min_sources=1)
    res = analyze(_bimodal_layer(), config, scorer)
    assert isinstance(res, LayerResult)
    assert res.was_analyzed


def test_analyze_dispatches_multilayer_dict():
    config = PolarizationConfig(n_influencers=2, min_edges=1)
    scorer = LatentIdeologyScorer(min_sources=1)
    results = analyze({"l1": _bimodal_layer()}, config, scorer)
    assert isinstance(results, dict)
    assert results["l1"].was_analyzed


def test_analyze_rejects_other_types():
    with pytest.raises(TypeError):
        analyze(42, PolarizationConfig())


def test_analyze_rejects_missing_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        analyze(tmp_path / "nope.gml", PolarizationConfig())


@pytest.fixture
def projected_folder(tmp_path):
    prj = tmp_path / "networks" / "projected"
    prj.mkdir(parents=True)

    g = nx.DiGraph()
    g.add_edge("a", "b")
    nx.write_gml(g, prj / "cop22__prj_1.gml")
    return tmp_path


# --- path dispatch -----------------------------------------------------------


def _write_graph(path, g):
    nx.write_gml(g, path)
    return path


def test_analyze_loads_plain_gml_path(tmp_path):
    path = _write_graph(tmp_path / "net.gml", _bimodal_layer())
    config = PolarizationConfig(n_influencers=2, min_edges=1)
    scorer = LatentIdeologyScorer(min_sources=1)
    res = analyze(path, config, scorer)
    assert isinstance(res, LayerResult)
    assert res.was_analyzed
    assert res.n_edges == 100


def test_analyze_loads_multilayer_gml_path(tmp_path):
    path = tmp_path / "cop22_retweet_network_ml.gml"
    path.write_text(MULTILAYER_GML)
    results = analyze(path, PolarizationConfig(min_edges=1))
    assert isinstance(results, dict)
    assert set(results) == {1, 2}


def test_analyze_loads_output_folder_path(projected_folder):
    results = analyze(projected_folder, PolarizationConfig(min_edges=1))
    assert isinstance(results, dict)
    assert set(results) == {1}


def test_analyze_network_accepts_gml_path(tmp_path):
    path = _write_graph(tmp_path / "net.gml", _bimodal_layer())
    res = analyze_network(path, PolarizationConfig(n_influencers=2, min_edges=1),
                          LatentIdeologyScorer(min_sources=1))
    assert res.was_analyzed


def test_analyze_network_rejects_multilayer_path(tmp_path):
    path = tmp_path / "cop22_retweet_network_ml.gml"
    path.write_text(MULTILAYER_GML)
    with pytest.raises(TypeError):
        analyze_network(path, PolarizationConfig())


def test_analyze_layers_rejects_single_network_path(tmp_path):
    path = _write_graph(tmp_path / "net.gml", _bimodal_layer())
    with pytest.raises(TypeError):
        analyze_layers(path, PolarizationConfig())
