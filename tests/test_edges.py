import networkx as nx

from netpol.edges import build_influencer_edges

from .fixtures import star_graph


def test_builds_one_row_per_in_edge():
    g = star_graph()
    df = build_influencer_edges(g, ["hub"])
    assert list(df.columns) == ["influencer", "user"]
    assert len(df) == 5
    assert set(df["influencer"]) == {"hub"}
    assert set(df["user"]) == {f"leaf_{i}" for i in range(5)}


def test_ignores_non_influencer_edges():
    g = nx.DiGraph()
    g.add_edge("u1", "i1")
    g.add_edge("u2", "i2")
    df = build_influencer_edges(g, ["i1"])
    assert len(df) == 1
    assert df.iloc[0]["user"] == "u1"


def test_excludes_self_loops():
    g = nx.DiGraph()
    g.add_edge("i1", "i1")
    g.add_edge("u1", "i1")
    df = build_influencer_edges(g, ["i1"])
    assert len(df) == 1
    assert set(df["user"]) == {"u1"}


def test_includes_influencer_influencer_edges():
    g = nx.DiGraph()
    g.add_edge("i2", "i1")  # influencer retweets influencer
    df = build_influencer_edges(g, ["i1", "i2"])
    assert len(df) == 1
    assert df.iloc[0]["influencer"] == "i1"
    assert df.iloc[0]["user"] == "i2"
