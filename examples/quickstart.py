"""Minimal end-to-end example using only synthetic data.

Run with:  poetry run python examples/quickstart.py
"""

import networkx as nx

from netpol import LatentIdeologyScorer, PolarizationConfig, analyze_layers, analyze_network


def make_polarized_layer(camp_size: int = 100) -> nx.DiGraph:
    """Two influencers, each retweeted exclusively by one camp of users."""
    g = nx.DiGraph()
    for i in range(camp_size):
        g.add_edge(f"camp1_{i}", "inf_1")
        g.add_edge(f"camp2_{i}", "inf_2")
    return g


def make_consensus_layer(camp_size: int = 100) -> nx.DiGraph:
    """Every user retweets both influencers equally -> unimodal scores."""
    g = nx.DiGraph()
    for i in range(camp_size):
        g.add_edge(f"u_{i}", "inf_1")
        g.add_edge(f"u_{i}", "inf_2")
    return g


def main() -> None:
    layers = {
        "polarized": make_polarized_layer(),
        "consensus": make_consensus_layer(),
    }

    config = PolarizationConfig(
        n_influencers=2,
        min_edges=1,
        fdr_correction=True,
    )
    scorer = LatentIdeologyScorer(min_sources=1)

    results = analyze_layers(layers, config, scorer)

    for layer_id, r in results.items():
        print(f"{layer_id:12s} "
              f"dip={r.dip_statistic:.3f} "
              f"p={r.p_value:.3f} "
              f"adj_p={r.adjusted_p_value if r.adjusted_p_value is None else round(r.adjusted_p_value, 3)} "
              f"polarized={r.is_polarized} "
              f"skip={r.skip_reason}")

    # A single network can be analyzed directly -- no dict wrapper needed.
    single = analyze_network(make_polarized_layer(), config, scorer)
    print(f"{'single':12s} polarized={single.is_polarized}")


if __name__ == "__main__":
    main()
