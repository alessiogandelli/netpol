"""Ground-truth regression tests: graphs whose answer is known by construction.

Unlike the unit tests in the other files, these encode *what the answer should
be* for synthetic networks where polarization (or its absence) is guaranteed by
how the graph is built.  If any of these break, netpol is no longer doing its
job -- regardless of whether the lower-level units still pass.
"""

import networkx as nx

from netpol import LatentIdeologyScorer, PolarizationConfig, analyze_network


def _two_camps(n: int = 50) -> nx.DiGraph:
    """Two influencers, each retweeted exclusively by one camp."""
    g = nx.DiGraph()
    for i in range(n):
        g.add_edge(f"c1_{i}", "inf_1")
    for i in range(n):
        g.add_edge(f"c2_{i}", "inf_2")
    return g


def _consensus(n: int = 100) -> nx.DiGraph:
    """Everyone retweets both influencers equally -> a single ideological blob."""
    g = nx.DiGraph()
    for i in range(n):
        g.add_edge(f"u_{i}", "inf_1")
        g.add_edge(f"u_{i}", "inf_2")
    return g


def _camps_with_bridge(n: int = 40, bridge: int = 20) -> nx.DiGraph:
    """Two camps plus a group that retweets both sides (fills the middle)."""
    g = _two_camps(n)
    for i in range(bridge):
        g.add_edge(f"bridge_{i}", "inf_1")
        g.add_edge(f"bridge_{i}", "inf_2")
    return g


def _single_hub(n: int = 30) -> nx.DiGraph:
    """Everyone retweets one account -- no second pole to polarize around."""
    g = nx.DiGraph()
    for i in range(n):
        g.add_edge(f"u_{i}", "hub")
    return g


_CFG = PolarizationConfig(n_influencers=2, min_edges=1, fdr_correction=False)
_SCORER = LatentIdeologyScorer(min_sources=1)


def test_two_camps_is_polarized():
    res = analyze_network(_two_camps(), _CFG, _SCORER)
    assert res.was_analyzed
    assert res.is_polarized is True
    assert res.p_value < 0.05


def test_consensus_is_not_polarized():
    res = analyze_network(_consensus(), _CFG, _SCORER)
    assert res.was_analyzed
    assert res.is_polarized is False
    assert res.p_value >= 0.05


def test_two_camps_scores_are_bimodal_and_bounded():
    res = analyze_network(_two_camps(), _CFG, _SCORER)
    scores = res.scores["score_1"]
    assert (scores.abs() <= 1.0).all()
    # each camp collapses to one pole; the two poles are opposite (the global
    # sign of the axis is arbitrary, so assert separation, not which is +).
    camp1 = scores[[f"c1_{i}" for i in range(50)]]
    camp2 = scores[[f"c2_{i}" for i in range(50)]]
    # within-camp spread is floating-point noise
    assert (camp1 - camp1.median()).abs().max() < 1e-6
    assert (camp2 - camp2.median()).abs().max() < 1e-6
    # the two camps sit on opposite sides of the axis, far apart
    assert (camp1.max() < camp2.min()) or (camp2.max() < camp1.min())
    assert abs(camp1.median() - camp2.median()) > 1.9


def test_bridge_reduces_dip_vs_pure_camps():
    pure = analyze_network(_two_camps(), _CFG, _SCORER)
    bridged = analyze_network(_camps_with_bridge(), _CFG, _SCORER)
    assert bridged.is_polarized is True
    # a middle population makes the distribution more unimodal -> lower dip
    assert bridged.dip_statistic < pure.dip_statistic


def test_single_hub_is_skipped_not_polarized():
    res = analyze_network(_single_hub(), _CFG, _SCORER)
    assert not res.was_analyzed
    assert res.is_polarized is None
    assert "influencers" in res.skip_reason
