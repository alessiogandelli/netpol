"""The ideology-scoring plug point.

The pipeline only depends on the ``IdeologyScorer`` protocol below, never on a
specific implementation.  ``netpol`` ships a default implementation
(``netpol.ideology.LatentIdeologyScorer``) that users can ignore, but the
protocol lets them swap in their own correspondence-analysis code, a different
method entirely, or a patched/expanded version of the built-in scorer.
"""

from __future__ import annotations

from typing import Protocol

from netpol.types import InteractionTable, ScoreTable


class IdeologyScorer(Protocol):
    """Something that maps an influencer-user interaction table to scores.

    Implementations receive the output of
    :func:`netpol.edges.build_influencer_edges` and must return one row per
    scored node, indexed by node id, with one column per dimension named
    ``score_1`` ... ``score_n``.
    """

    def score(self, edges: InteractionTable, n_dimensions: int) -> ScoreTable:
        """Compute per-node ideology scores.

        Args:
            edges: DataFrame with columns ``['influencer', 'user']``.
            n_dimensions: Number of score dimensions to return.

        Returns:
            A DataFrame indexed by node id with columns
            ``['score_1', ..., 'score_n']``.

        Raises:
            ValueError: if ``edges`` is empty or scoring cannot proceed.
        """
        ...
