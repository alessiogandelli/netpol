"""Public type aliases.

These exist so that IDEs and type checkers can show users exactly what shape
the data flowing through ``netpol`` has.  They are plain ``pandas`` /
``networkx`` types under the hood -- the aliases carry the documentation.

Import them from the package root::

    from netpol import Layers, LayerId
"""

from __future__ import annotations

from typing import Hashable

import networkx as nx
import pandas as pd

LayerId = Hashable
"""Key identifying a layer in a multilayer network (any hashable: int, str, ...)."""

Layers = dict[LayerId, nx.DiGraph]
"""Mapping ``layer_id -> DiGraph`` that :func:`netpol.analyze_layers` consumes."""

InteractionTable = pd.DataFrame
"""Long-form interaction table with columns ``['influencer', 'user']``.

One row per edge ``user -> influencer`` (``a -> b`` means "a retweets b").
Produced by :func:`netpol.build_influencer_edges`, consumed by
``IdeologyScorer.score``.
"""

ScoreTable = pd.DataFrame
"""Per-node ideology scores: indexed by node id, columns ``score_1..score_n``.

One row per scored user, one column per ideology dimension, values in
``[-1, 1]``.  Returned by ``IdeologyScorer.score`` and stored in
``LayerResult.scores``.
"""

__all__ = [
    "LayerId",
    "Layers",
    "InteractionTable",
    "ScoreTable",
]
