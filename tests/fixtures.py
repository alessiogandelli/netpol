"""Shared test fixtures."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from netpol.scoring import IdeologyScorer


def star_graph():
    """One hub (in-degree 5), five leaves. Directed edges leaf -> hub."""
    import networkx as nx

    g = nx.DiGraph()
    hub = "hub"
    for i in range(5):
        g.add_edge(f"leaf_{i}", hub)
    return g


def tied_degree_graph():
    """Two nodes with equal degree, to test deterministic tie-breaking."""
    import networkx as nx

    g = nx.DiGraph()
    # "a" and "b" each get 1 in-edge; node ids break the tie
    g.add_edge("x", "a")
    g.add_edge("y", "b")
    return g


def bimodal_scores():
    rng = np.random.default_rng(0)
    return np.concatenate([rng.normal(-1, 0.2, 500), rng.normal(1, 0.2, 500)])


def unimodal_scores():
    rng = np.random.default_rng(0)
    return rng.normal(0, 1, 1000)


def sparse_layer():
    """A layer with fewer than the default min_edges (10)."""
    import networkx as nx

    g = nx.DiGraph()
    g.add_edge("a", "b")
    g.add_edge("c", "b")
    return g


class FakeIdeologyScorer(IdeologyScorer):
    """Returns fixed, precomputed scores keyed by node id."""

    def __init__(self, score_map: dict | None = None):
        # default: two-camp bimodal distribution over arbitrary user ids
        self.score_map = score_map or {}

    def score(self, edges: pd.DataFrame, n_dimensions: int) -> pd.DataFrame:
        if edges.empty:
            raise ValueError("empty edges")
        users = sorted(edges["user"].unique())
        if self.score_map:
            values = [self.score_map.get(u, 0.0) for u in users]
        else:
            # deterministic synthetic bimodal scores derived from the user id
            values = [1.0 if hash(u) % 2 else -1.0 for u in users]
        cols = {f"score_{d + 1}": values for d in range(n_dimensions)}
        return pd.DataFrame(cols, index=users)


@pytest.fixture
def fake_scorer():
    return FakeIdeologyScorer()
