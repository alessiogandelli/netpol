"""netpol -- measure polarization in (multilayer) social networks.

Given a network (or a ``dict`` of per-layer networks), the pipeline selects
top influencers, scores every user on a bipolar latent-ideology axis via
correspondence analysis, and tests whether the resulting score distribution
is multimodal (polarized) using Hartigan's dip test with optional FDR
correction across layers.

Edge convention: ``a -> b`` means "a retweets/endorses b".
"""

from netpol.bimodality import apply_fdr_correction, dip_test
from netpol.config import PolarizationConfig
from netpol.edges import build_influencer_edges
from netpol.ideology import LatentIdeologyScorer
from netpol.influencers import select_influencers
from netpol.io import load_layers, read_multilayer_gml
from netpol.layer_result import LayerResult
from netpol.pipeline import analyze_layer, analyze_layers
from netpol.scoring import IdeologyScorer

__version__ = "0.1.0"

__all__ = [
    "PolarizationConfig",
    "LayerResult",
    "IdeologyScorer",
    "LatentIdeologyScorer",
    "select_influencers",
    "build_influencer_edges",
    "dip_test",
    "apply_fdr_correction",
    "analyze_layer",
    "analyze_layers",
    "load_layers",
    "read_multilayer_gml",
    "__version__",
]
