"""Reproduce the original COP pipeline (climate-network-analysis/src/analysis/ideology.py).

This mirrors the data preparation from the original script: read a multilayer
GML, convert to a ``dict[layer_id, DiGraph]``, and run
``netpol.analyze_layers``.  The multiplex GML is parsed directly with networkx
-- netpol only ever sees plain networkx graphs.

Requires the COP data folder to exist (not available in CI / this checkout),
e.g.:

  /Users/<you>/data/cop26/            (original layout)
  .../test_library/out/cop22/         (topiclayers output layout)

Run with:  python examples/cop_pipeline.py <folder> [--n-cop N]
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from netpol import LatentIdeologyScorer, PolarizationConfig, analyze_layers  # noqa: E402

from _gml import load_topic_labels, read_multilayer_gml  # noqa: E402

N_COP = 22
N_INFLUENCERS = 100
MIN_SOURCES = 2  # the original `n` parameter of latent_ideology.apply_method


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", help="COP data folder (contains networks/ and cache/)")
    parser.add_argument("--n-cop", type=int, default=N_COP, help=f"COP number (default {N_COP})")
    args = parser.parse_args()

    folder = Path(args.folder).expanduser()
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
        exclude_layers=(-1,),  # the "no topic" layer excluded by the original
    )
    scorer = LatentIdeologyScorer(min_sources=MIN_SOURCES)

    results = analyze_layers(layers, config, scorer)

    # sort by dip statistic, most polarized first
    analyzed = [
        (lid, r) for lid, r in results.items() if r.was_analyzed and r.is_polarized
    ]
    ranked = sorted(analyzed, key=lambda kv: kv[1].dip_statistic, reverse=True)

    print("Most polarized topics:")
    for lid, r in ranked[:10]:
        print(f"  layer {lid} ({topic_label.get(lid, '?')}): "
              f"dip={r.dip_statistic:.3f} adj_p={r.adjusted_p_value:.3g}")

    skipped = {lid: r.skip_reason for lid, r in results.items() if not r.was_analyzed}
    if skipped:
        print(f"\n{len(skipped)} layers skipped:")
        for lid, reason in list(skipped.items())[:5]:
            print(f"  layer {lid}: {reason}")


if __name__ == "__main__":
    main()
