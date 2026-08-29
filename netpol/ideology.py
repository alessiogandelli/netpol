"""Built-in latent-ideology scorer.

Implements correspondence analysis (CA) to map retweet patterns onto a
bipolar ideology axis, following the method of Falkenberg et al. (2021) and
Flamino et al. (2021).  This is a self-contained, deterministic rewrite of the
approach, maintained here rather than depending on the external
``latent-ideology`` package.

Method
------
1. From the ``(influencer, user)`` interaction table, build a weighted
   ``user x influencer`` adjacency matrix ``A`` (weight = number of retweets).
2. Keep only users who retweeted at least ``min_sources`` distinct
   influencers (the ``n`` threshold of the original method) and, optionally,
   only the top ``max_sources`` influencers by total interactions.
3. Correspondence analysis: standardize ``A`` to residuals
   ``S = Dr^-1/2 (P - r c^T) Dc^-1/2`` and take its truncated SVD.
4. Row scores ``X = Dr^-1/2 U`` are rescaled to ``[-1, 1]`` per dimension.

Deviations from the reference implementation, for reproducibility: SVD is
computed with ``numpy.linalg.svd`` (deterministic LAPACK) instead of
``sklearn``'s ``randomized_svd`` (``random_state=None``, non-deterministic).

References
----------
- M. Falkenberg et al., "Growing polarisation around climate change on social
  media", arXiv:2112.12137 (2021).
- J. Flamino et al., "Shifting polarization and Twitter news influencers
  between two US presidential elections", arXiv:2111.02505 (2021).
"""

from __future__ import annotations

from typing import Hashable

import numpy as np
import pandas as pd

from netpol.scoring import IdeologyScorer
from netpol.types import InteractionTable, ScoreTable


class LatentIdeologyScorer(IdeologyScorer):
    """Correspondence-analysis ideology scorer.

    Args:
        min_sources: Minimum number of *distinct* influencers a user must have
            retweeted to be scored.  Users below this threshold are dropped.
            This is the ``n`` parameter of the original method (default 2).
        max_sources: If set, restrict to the top ``max_sources`` influencers by
            total interactions (the original ``m`` parameter).  ``None`` keeps
            all influencers present in the interaction table.
    """

    def __init__(self, min_sources: int = 2, max_sources: int | None = None):
        if min_sources < 1:
            raise ValueError("min_sources must be >= 1")
        if max_sources is not None and max_sources < 2:
            raise ValueError("max_sources must be >= 2 or None")
        self.min_sources = min_sources
        self.max_sources = max_sources

    def score(self, edges: InteractionTable, n_dimensions: int) -> ScoreTable:
        if edges is None or edges.empty:
            raise ValueError("cannot score an empty interaction table")
        if "influencer" not in edges.columns or "user" not in edges.columns:
            raise ValueError("edges must have 'influencer' and 'user' columns")
        if n_dimensions < 1:
            raise ValueError("n_dimensions must be >= 1")

        adjacency, influencers = self._build_adjacency(edges)
        n_users, n_influencers = adjacency.shape

        if n_users < 2:
            raise ValueError(
                f"need at least 2 users after filtering, got {n_users}"
            )
        if n_influencers < 2:
            raise ValueError(
                f"need at least 2 influencers, got {n_influencers}"
            )

        scores = self._correspondence_scores(adjacency, n_dimensions)
        return pd.DataFrame(
            scores,
            index=adjacency.index,
            columns=[f"score_{d + 1}" for d in range(scores.shape[1])],
        )

    # -- helpers ---------------------------------------------------------

    def _build_adjacency(
        self, edges: InteractionTable
    ) -> tuple[pd.DataFrame, list[Hashable]]:
        """Return the (users x influencers) weighted adjacency matrix.

        Users touching fewer than ``min_sources`` distinct influencers are
        dropped; empty influencer columns are removed afterwards.
        """
        df = edges[["user", "influencer"]].copy()

        # count distinct influencers per user, drop users below threshold
        distinct = df.groupby("user")["influencer"].nunique()
        keep_users = distinct[distinct >= self.min_sources].index
        df = df[df["user"].isin(keep_users)]

        if self.max_sources is not None:
            top = (
                df.groupby("influencer")
                .size()
                .sort_values(ascending=False)
                .head(self.max_sources)
                .index
            )
            df = df[df["influencer"].isin(top)]

        # weighted user x influencer matrix (count of interactions)
        weighted = (
            df.groupby(["user", "influencer"]).size().reset_index(name="weight")
        )
        matrix = weighted.pivot(
            index="user", columns="influencer", values="weight"
        ).fillna(0.0)

        # drop influencer columns left with no interactions after filtering
        matrix = matrix.loc[:, (matrix != 0).any(axis=0)]
        return matrix, list(matrix.columns)

    @staticmethod
    def _correspondence_scores(
        adjacency: pd.DataFrame, n_dimensions: int
    ) -> np.ndarray:
        A = adjacency.to_numpy(dtype=float)
        total = A.sum()
        if total <= 0:
            raise ValueError("adjacency matrix has no interactions")

        P = A / total
        r = P.sum(axis=1)  # row (user) masses
        c = P.sum(axis=0)  # column (influencer) masses

        Dr_inv_sqrt = np.diag(np.power(r, -0.5))
        Dc_inv_sqrt = np.diag(np.power(c, -0.5))

        S = Dr_inv_sqrt @ (P - np.outer(r, c)) @ Dc_inv_sqrt

        k = min(n_dimensions, min(S.shape) - 1)
        if k < 1:
            raise ValueError("matrix too small for any ideology dimension")

        U, _, _ = np.linalg.svd(S, full_matrices=False)
        X = Dr_inv_sqrt @ U[:, :k]

        # scale each dimension into [-1, 1]
        scaled = np.empty_like(X)
        for d in range(k):
            span = X[:, d].max() - X[:, d].min()
            if span == 0:
                raise ValueError(
                    f"degenerate score distribution in dimension {d + 1}"
                )
            scaled[:, d] = -1 + 2 * (X[:, d] - X[:, d].min()) / span
        return scaled
