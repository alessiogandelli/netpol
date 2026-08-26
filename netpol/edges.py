"""Build the influencer-user interaction table.

Edge convention (fixed, stated here and in the README):

    ``a -> b`` means "a retweets/endorses b".

Given a list of influencer ids, this module produces the long-form table of
interactions that the ideology scorer consumes: one row per edge *into* an
influencer, with columns ``['influencer', 'user']`` (``user`` is the retweeter,
``influencer`` is the retweeted account).
"""

from __future__ import annotations

import networkx as nx
import pandas as pd


def build_influencer_edges(
    graph: nx.DiGraph, influencers: list
) -> pd.DataFrame:
    """Return a DataFrame of ``(influencer, user)`` rows for edges into influencers.

    One row per edge ``user -> influencer`` where ``influencer`` is in
    ``influencers``.  Self-loops are excluded.  No deduplication and no
    special-casing of influencer-influencer edges -- influencer selection and
    edge construction are fully decoupled.

    Implemented as a single list comprehension feeding one ``pd.DataFrame``
    call; do not regress this to the ``pd.concat``-in-a-loop pattern.
    """
    influencer_set = set(influencers)
    rows = [
        {"influencer": u, "user": v}
        for u in influencers
        for v in graph.predecessors(u)
        if v != u
    ]
    return pd.DataFrame(rows, columns=["influencer", "user"])
