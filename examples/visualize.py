"""Visualize netpol results and the polarized networks.

Runs the polarization pipeline over a COP multilayer GML and writes static
PNGs: an overview of the dip-test results plus, for the largest polarized
topics, the score distribution and the influencer-interaction network (users
coloured by latent-ideology score).

Run with the topiclayers venv (has matplotlib) plus netpol + diptest on the
path -- see the sys.path bootstrap at the top of this file:

  .../test_library/.venv/bin/python examples/visualize.py <folder> \
      --out examples/out/cop22
"""

import argparse
import os
import random
import sys
from pathlib import Path

# --- bootstrap: make `netpol`, `_gml`, and `diptest` importable ------------
_EXAMPLES_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_EXAMPLES_DIR)  # .../netpol (holds the `netpol` package)
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, _EXAMPLES_DIR)

_venv_sp = os.path.join(
    _REPO_ROOT, ".venv", "lib",
    f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages",
)
if os.path.isdir(_venv_sp):
    sys.path.insert(0, _venv_sp)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402

from netpol import (  # noqa: E402
    LatentIdeologyScorer,
    PolarizationConfig,
    analyze_layers,
    read_multilayer_gml,
)
from _gml import load_topic_labels  # noqa: E402

N_COP = 22
N_INFLUENCERS = 100
MIN_SOURCES = 2
MAX_NODES_PER_NETWORK = 500
TOP_INFLUENCERS_PER_NETWORK = 10

CMAP = plt.get_cmap("RdBu")


def _score_color(score: float):
    return CMAP((score + 1.0) / 2.0)


def _interaction_subgraph(graph, influencers, scores, m, max_nodes):
    """Subgraph of ``user -> influencer`` edges among the top ``m`` influencers.

    Nodes are the top-``m`` influencers plus the scored users who retweet them.
    If too many users, subsample deterministically to keep the layout fast.
    """
    top = influencers[:m]
    top_set = set(top)
    g = nx.DiGraph()
    g.add_nodes_from(top)
    for u in top:
        for v in graph.predecessors(u):
            if v in scores.index:
                g.add_edge(v, u)

    users = [n for n in g.nodes if n not in top_set]
    if len(users) > max_nodes:
        keep = set(random.Random(42).sample(users, max_nodes))
        g = g.subgraph(top_set | keep).copy()
    return g


def plot_network(ax, graph, influencers, scores, m):
    g = _interaction_subgraph(
        graph, influencers, scores, m, MAX_NODES_PER_NETWORK
    )
    top_set = set(influencers[:m])
    pos = nx.spring_layout(g, seed=42, k=0.35)

    node_colors = []
    node_sizes = []
    for n in g.nodes:
        if n in top_set:
            node_colors.append("#222222")
            node_sizes.append(180)
        else:
            node_colors.append(_score_color(scores.loc[n, "score_1"]))
            node_sizes.append(24)

    nx.draw_networkx_edges(g, pos, ax=ax, edge_color="#cccccc", width=0.3, arrows=False)
    nx.draw_networkx_nodes(g, pos, ax=ax, node_color=node_colors, node_size=node_sizes, linewidths=0)
    ax.set_axis_off()


def plot_scores(ax, scores, title):
    vals = scores["score_1"]
    ax.hist(vals, bins=30, color="#7f7f7f", edgecolor="white")
    ax.axvline(0, color="black", lw=0.5, ls="--")
    ax.set_xlabel("latent ideology score")
    ax.set_ylabel("users")
    ax.set_title(title, fontsize=9)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", help="COP data folder (contains networks/ and cache/)")
    parser.add_argument("--n-cop", type=int, default=N_COP, help=f"COP number (default {N_COP})")
    parser.add_argument("--out", default="examples/out/cop22", help="output directory")
    parser.add_argument("--top-n", type=int, default=4, help="how many polarized networks to plot")
    args = parser.parse_args()

    folder = Path(args.folder).expanduser()
    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    projected_path = folder / "networks" / f"cop{args.n_cop}_retweet_network_ml.gml"
    if not projected_path.exists():
        sys.exit(f"multilayer GML not found: {projected_path}")

    topic_label = load_topic_labels(folder, args.n_cop)
    layers = read_multilayer_gml(str(projected_path))

    config = PolarizationConfig(
        influencer_strategy="in_degree",
        n_influencers=N_INFLUENCERS,
        ideology_dimensions=1,
        significance_level=0.05,
        fdr_correction=True,
        min_edges=10,
        exclude_layers=(-1,),
    )
    results = analyze_layers(layers, config, LatentIdeologyScorer(min_sources=MIN_SOURCES))

    polarized = [
        (lid, r) for lid, r in results.items() if r.was_analyzed and r.is_polarized
    ]
    polarized_by_dip = sorted(polarized, key=lambda kv: kv[1].dip_statistic, reverse=True)
    selected = sorted(polarized, key=lambda kv: len(kv[1].scores), reverse=True)[: args.top_n]

    # ---- overview figure ---------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    top = polarized_by_dip[:15]
    labels = [f"{lid}: {topic_label.get(lid, '?')[:38]}" for lid, _ in top]
    dips = [r.dip_statistic for _, r in top]
    colors = [CMAP(r.adjusted_p_value / 0.05) if r.adjusted_p_value is not None else "#999999" for _, r in top]
    ax1.barh(range(len(top)), dips, color=colors)
    ax1.set_yticks(range(len(top)))
    ax1.set_yticklabels(labels, fontsize=7)
    ax1.invert_yaxis()
    ax1.set_xlabel("dip statistic")
    ax1.set_title("Top polarized topics by dip statistic")

    analyzed = [(lid, r) for lid, r in results.items() if r.was_analyzed]
    xs = [r.n_edges for _, r in analyzed]
    ys = [r.dip_statistic for _, r in analyzed]
    cs = ["#c0392b" if r.is_polarized else "#7f8c8d" for _, r in analyzed]
    ax2.scatter(xs, ys, c=cs, alpha=0.6, s=30)
    ax2.set_xscale("log")
    ax2.set_xlabel("n_edges (log)")
    ax2.set_ylabel("dip statistic")
    ax2.set_title("Dip vs. layer size (small samples inflate dip)")

    fig.tight_layout()
    fig.savefig(out_dir / "overview.png", dpi=130)
    plt.close(fig)

    # ---- per-layer figures -------------------------------------------------
    for lid, r in selected:
        graph = layers[lid]
        label = topic_label.get(lid, "?")
        title = f"topic {lid} ({label})  dip={r.dip_statistic:.3f} adj_p={r.adjusted_p_value:.3g}"

        fig, (ax_s, ax_n) = plt.subplots(1, 2, figsize=(16, 8))
        plot_scores(ax_s, r.scores, f"score distribution\n{title}")
        plot_network(ax_n, graph, r.influencers, r.scores, TOP_INFLUENCERS_PER_NETWORK)
        ax_n.set_title(f"influencer-interaction network\n{title}", fontsize=9)

        fig.tight_layout()
        fig.savefig(out_dir / f"topic_{lid}.png", dpi=130)
        plt.close(fig)
        print(f"  wrote topic_{lid}.png  (n_edges={r.n_edges}, scored={len(r.scores)})")

    print(f"overview.png + {len(selected)} topic figures written to {out_dir}")


if __name__ == "__main__":
    main()
