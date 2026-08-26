"""Configuration for a polarization analysis run.

A ``PolarizationConfig`` captures every decision that shapes what a run
counts as "polarized": how influencers are chosen, how many, the ideology
dimensionality, and how significance is handled.  These are methodological
choices, not implementation details -- see ``DEBATES.md`` for the reasoning
and open questions behind each default.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PolarizationConfig:
    """Immutable configuration for :func:`netpol.pipeline.analyze_layers`.

    Attributes:
        influencer_strategy: How to rank nodes when selecting influencers.
            One of ``"degree"`` (in + out degree) or ``"in_degree"`` (authority
            in a retweet network: "gets retweeted a lot").
        n_influencers: Number of top influencers to select per layer.
        ideology_dimensions: Number of latent-ideology dimensions to compute.
            Default 1 -- a single bipolar axis with scores in ``[-1, 1]``.
        significance_level: p-value threshold for the dip test.
        fdr_correction: Apply Benjamini-Hochberg correction across layers.
        min_edges: Layers with fewer directed edges than this are skipped
            before scoring (with a ``skip_reason``), instead of crashing.
        exclude_layers: Layer ids to skip entirely (e.g. a "misc/no topic"
            layer).  Replaces the hard-coded ``l != -1`` of the original
            script.
        random_seed: Reserved for future deterministic scoring.  Note: the
            built-in scorer is already deterministic (see ``DEBATES.md``).
    """

    influencer_strategy: str = "in_degree"
    n_influencers: int = 30
    ideology_dimensions: int = 1
    significance_level: float = 0.05
    fdr_correction: bool = True
    min_edges: int = 10
    exclude_layers: tuple = field(default_factory=tuple)
    random_seed: int | None = None

    def __post_init__(self) -> None:
        if self.influencer_strategy not in {"degree", "in_degree"}:
            raise ValueError(
                f"influencer_strategy must be 'degree' or 'in_degree', "
                f"got {self.influencer_strategy!r}"
            )
        if self.n_influencers <= 0:
            raise ValueError("n_influencers must be > 0")
        if self.ideology_dimensions < 1:
            raise ValueError("ideology_dimensions must be >= 1")
        if not 0 < self.significance_level < 1:
            raise ValueError("significance_level must be in (0, 1)")
        if self.min_edges < 0:
            raise ValueError("min_edges must be >= 0")
