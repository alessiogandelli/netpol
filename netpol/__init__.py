"""netpol -- measure polarization in (multilayer) social networks.

Given a network (or a ``dict`` of per-layer networks), the pipeline selects
top influencers, scores every user on a bipolar latent-ideology axis via
correspondence analysis, and tests whether the resulting score distribution
is multimodal (polarized) using Hartigan's dip test with optional FDR
correction across layers.

Edge convention: ``a -> b`` means "a retweets/endorses b".

Everything public is importable from the package root, so ``netpol.`` gives
autocomplete over the full API::

    from netpol import analyze, PolarizationConfig
"""

from netpol.bimodality import apply_fdr_correction, dip_test
from netpol.config import InfluencerStrategy, PolarizationConfig
from netpol.edges import build_influencer_edges
from netpol.ideology import LatentIdeologyScorer
from netpol.influencers import select_influencers
from netpol.io import load_layers, load_network, read_multilayer_gml
from netpol.layer_result import LayerResult, Results
from netpol.pipeline import analyze, analyze_layers, analyze_network
from netpol.scoring import IdeologyScorer
from netpol.types import InteractionTable, LayerId, Layers, ScoreTable

__version__ = "0.2.1"

__all__ = [
    # entry points
    "analyze",
    "analyze_network",
    "analyze_layers",
    # configuration & results
    "PolarizationConfig",
    "LayerResult",
    "IdeologyScorer",
    "LatentIdeologyScorer",
    # building blocks
    "select_influencers",
    "build_influencer_edges",
    "dip_test",
    "apply_fdr_correction",
    "load_layers",
    "load_network",
    "read_multilayer_gml",
    # type aliases
    "LayerId",
    "Layers",
    "Results",
    "InteractionTable",
    "ScoreTable",
    "InfluencerStrategy",
    "__version__",
]
