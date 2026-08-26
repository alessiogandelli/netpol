"""Influencer selection.

Rank nodes by a centrality score, take the top ``n`` as "influencers" and
return the rest as "users".  This is intentionally one small function rather
than a plugin system -- see the engineering spec for when to grow it.

Edge convention reminder: ``a -> b`` means "a retweets/endorses b", so
``in_degree`` counts how often a node is retweeted (authority), while total
``degree`` also counts how often it retweets others.
"""

from __future__ import annotations

import networkx as nx


def select_influencers(
    graph: nx.DiGraph, strategy: str, n: int
) -> tuple[list, list]:
    """Split the nodes of ``graph`` into influencers and users.

    Args:
        graph: A directed graph.
        strategy: ``"degree"`` (total degree) or ``"in_degree"``.
        n: Number of influencers to select.

    Returns:
        ``(influencers, others)`` where ``influencers`` holds the top ``n``
        nodes by the chosen score (descending) and ``others`` the rest.  Ties
        are broken by the stringified node id, ascending, for determinism.
        If ``n`` is greater than or equal to the node count, ``others`` is
        empty (this does not raise).
    """
    if strategy == "degree":
        scores = graph.degree()
    elif strategy == "in_degree":
        scores = graph.in_degree()
    else:
        raise ValueError(f"Unknown strategy: {strategy!r}")

    ranked = sorted(scores, key=lambda item: (-item[1], str(item[0])))

    influencers = [node for node, _ in ranked[:n]]
    others = [node for node, _ in ranked[n:]]
    return influencers, others
