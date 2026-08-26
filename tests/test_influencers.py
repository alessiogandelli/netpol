import networkx as nx

from netpol.influencers import select_influencers

from .fixtures import star_graph, tied_degree_graph


def test_in_degree_strategy_selects_hub():
    g = star_graph()
    influencers, others = select_influencers(g, "in_degree", 1)
    assert influencers == ["hub"]
    assert len(others) == 5


def test_degree_strategy_agrees_on_star():
    g = star_graph()
    influencers, _ = select_influencers(g, "degree", 1)
    assert influencers == ["hub"]


def test_tie_break_is_deterministic():
    g = tied_degree_graph()
    influencers, _ = select_influencers(g, "in_degree", 1)
    # equal in-degree; stringified node id ascending -> "a" before "b"
    assert influencers == ["a"]


def test_n_larger_than_nodes_returns_empty_others():
    g = star_graph()
    influencers, others = select_influencers(g, "in_degree", 100)
    assert set(influencers) == set(g.nodes())
    assert others == []


def test_unknown_strategy_raises():
    g = star_graph()
    try:
        select_influencers(g, "betweenness", 1)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
