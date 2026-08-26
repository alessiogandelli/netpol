import numpy as np
import pandas as pd
import pytest

from netpol.ideology import LatentIdeologyScorer


def _two_camps_edges(n_per_camp=5):
    rows = []
    for i in range(n_per_camp):
        for _ in range(10):
            rows.append({"influencer": "A", "user": f"camp1_{i}"})
        rows.append({"influencer": "B", "user": f"camp1_{i}"})
    for i in range(n_per_camp):
        rows.append({"influencer": "A", "user": f"camp2_{i}"})
        for _ in range(10):
            rows.append({"influencer": "B", "user": f"camp2_{i}"})
    return pd.DataFrame(rows, columns=["influencer", "user"])


def test_two_camps_produce_opposite_scores():
    edges = _two_camps_edges()
    scores = LatentIdeologyScorer(min_sources=2).score(edges, 1)

    camp1 = scores.loc[[f"camp1_{i}" for i in range(5)], "score_1"].to_numpy()
    camp2 = scores.loc[[f"camp2_{i}" for i in range(5)], "score_1"].to_numpy()

    # opposite sides of the axis, no overlap
    assert (camp1.max() < camp2.min()) or (camp2.max() < camp1.min())


def test_scores_bounded_in_unit_interval():
    edges = _two_camps_edges()
    scores = LatentIdeologyScorer(min_sources=2).score(edges, 1)
    assert (scores["score_1"].abs() <= 1.0).all()


def test_min_sources_filters_users():
    rows = [
        {"influencer": "A", "user": "loyal"},  # only 1 distinct influencer
        {"influencer": "A", "user": "loyal"},
        {"influencer": "A", "user": "bridged1"},
        {"influencer": "B", "user": "bridged1"},
        {"influencer": "A", "user": "bridged2"},
        {"influencer": "B", "user": "bridged2"},
    ]
    edges = pd.DataFrame(rows, columns=["influencer", "user"])
    scores = LatentIdeologyScorer(min_sources=2).score(edges, 1)
    assert {"bridged1", "bridged2"} <= set(scores.index)
    assert "loyal" not in scores.index


def test_multi_dimension_returns_n_columns():
    # three influencers -> rank-2 structure -> two dimensions available
    rows = []
    for i in range(10):
        for _ in range(5):
            rows.append({"influencer": "A", "user": f"c1_{i}"})
        rows.append({"influencer": "B", "user": f"c1_{i}"})
    for i in range(10):
        rows.append({"influencer": "B", "user": f"c2_{i}"})
        for _ in range(5):
            rows.append({"influencer": "C", "user": f"c2_{i}"})
    edges = pd.DataFrame(rows, columns=["influencer", "user"])
    scores = LatentIdeologyScorer(min_sources=2).score(edges, 2)
    assert list(scores.columns) == ["score_1", "score_2"]
    assert len(scores) == 20


def test_deterministic():
    edges = _two_camps_edges()
    s1 = LatentIdeologyScorer(min_sources=2).score(edges, 1)
    s2 = LatentIdeologyScorer(min_sources=2).score(edges, 1)
    pd.testing.assert_frame_equal(s1, s2)


def test_empty_edges_raises():
    with pytest.raises(ValueError):
        LatentIdeologyScorer().score(pd.DataFrame(columns=["influencer", "user"]), 1)


def test_insufficient_influencers_raises():
    rows = [
        {"influencer": "A", "user": "u1"},
        {"influencer": "A", "user": "u2"},
        {"influencer": "A", "user": "u3"},
    ]
    edges = pd.DataFrame(rows, columns=["influencer", "user"])
    with pytest.raises(ValueError):
        LatentIdeologyScorer(min_sources=1).score(edges, 1)
