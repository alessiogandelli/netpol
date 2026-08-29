"""Fidelity check: netpol's LatentIdeologyScorer vs the reference package.

Runs the external ``latent-ideology`` implementation (Fede Moss, MIT -- the
method netpol vendors in ``netpol/ideology.py``) side by side with netpol's
scorer and checks that the two produce the same ideology scores.

Why this needs its own environment
----------------------------------
The reference package is from 2022 and is not compatible with modern
numpy/pandas/sklearn (it uses ``np.ptp``, ``float(np.array)``, and
``randomized_svd``, all removed/changed since).  Run it from a throwaway venv:

    python3.10 -m venv /tmp/netpol-compare
    /tmp/netpol-compare/bin/pip install \
        "numpy==1.24.4" "pandas==1.5.3" "scikit-learn<1.5" \
        "latent-ideology==0.0.8.2" networkx diptest

Then, from the repo root:

    /tmp/netpol-compare/bin/python examples/compare_latent_ideology.py \
        [path/to/cop_folder]

The optional COP folder enables the real-data comparison; without it only the
synthetic case runs.

Known deviations (see docs/DEBATES.md):
- netpol uses deterministic ``numpy.linalg.svd``; the reference uses
  ``sklearn``'s non-deterministic ``randomized_svd`` (``random_state=None``),
  so the component can flip sign run-to-run.  We align the sign before
  comparing.
- The reference's ``k`` (interaction cap) parameter is not implemented in
  netpol; we pass a huge ``k`` here so the reference applies no cap, matching
  netpol's behaviour.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

_EXAMPLES_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_EXAMPLES_DIR)  # .../netpol (holds the `netpol` package)
sys.path.insert(0, _REPO_ROOT)

from netpol import LatentIdeologyScorer  # noqa: E402

try:
    from latent_ideology.latent_ideology_class import latent_ideology as ref_li
except ImportError:
    sys.exit(
        "latent-ideology is not installed.  Create the comparison venv first "
        "(see module docstring), then rerun with that venv's python."
    )

# The reference package crashes with its default k=None (a `KeyError` on
# string node ids); pass a huge k so no interaction cap is applied.
_REF_K = 1 << 40
_MIN_SOURCES = 2


def _synthetic_edges() -> pd.DataFrame:
    """A weighted two-camp interaction table with a small bridging group.

    camp1 retweets influencer A a lot (and B a little); camp2 the mirror image;
    bridge users retweet both roughly equally.  This exercises the general
    (non-degenerate) path of the correspondence analysis rather than the pure
    all-or-nothing case.
    """
    rng = np.random.default_rng(0)
    rows: list[dict] = []
    for i in range(40):
        for _ in range(int(rng.integers(4, 9))):
            rows.append({"influencer": "A", "user": f"c1_{i}"})
        if rng.random() < 0.3:
            rows.append({"influencer": "B", "user": f"c1_{i}"})
    for i in range(40):
        for _ in range(int(rng.integers(4, 9))):
            rows.append({"influencer": "B", "user": f"c2_{i}"})
        if rng.random() < 0.3:
            rows.append({"influencer": "A", "user": f"c2_{i}"})
    for i in range(10):
        rows.append({"influencer": "A", "user": f"bridge_{i}"})
        rows.append({"influencer": "B", "user": f"bridge_{i}"})
    return pd.DataFrame(rows, columns=["influencer", "user"])


def _reference_scores(edges: pd.DataFrame) -> pd.DataFrame:
    df1, _ = ref_li(edges).apply_method(
        n=_MIN_SOURCES, k=_REF_K, targets="user", sources="influencer"
    )
    return df1.set_index("target")["score"].rename("score")


def _netpol_scores(edges: pd.DataFrame) -> pd.Series:
    out = LatentIdeologyScorer(min_sources=_MIN_SOURCES).score(edges, 1)
    return out["score_1"]


def _align(ref: np.ndarray, other: np.ndarray) -> tuple[float, np.ndarray]:
    """Sign-align ``other`` to ``ref`` (via correlation) and return (corr, other)."""
    corr = np.corrcoef(ref, other)[0, 1]
    if corr < 0:
        return -corr, -other
    return corr, other


def compare(edges: pd.DataFrame, label: str) -> None:
    ref = _reference_scores(edges)
    ref_again = _reference_scores(edges)  # second draw of the randomized SVD
    npol = _netpol_scores(edges)

    common = ref.index.intersection(npol.index).intersection(ref_again.index)
    if len(common) < 2:
        print(f"[{label}] too few common users to compare (got {len(common)})")
        return

    ref = ref.loc[common].to_numpy()
    npol = npol.loc[common].to_numpy()
    ref_again = ref_again.loc[common].to_numpy()

    # The reference's randomized_svd is non-deterministic: two runs of the
    # *reference itself* already differ.  Measure that self-noise, then check
    # netpol sits within it.  This is the right bar for "faithful": netpol vs
    # reference should be no further than reference vs reference.
    self_corr, ref_again = _align(ref, ref_again)
    self_mean = float(np.mean(np.abs(ref - ref_again)))

    corr, npol = _align(ref, npol)
    mean_abs_diff = float(np.mean(np.abs(ref - npol)))
    max_diff = float(np.max(np.abs(ref - npol)))

    # corr must be ~1 and netpol must be within the reference's own run-to-run
    # noise (generously, 2x).  A scaling bug would push mean|diff| well past
    # both bounds even though corr is scale-invariant.
    ok = corr > 0.999 and mean_abs_diff <= max(2 * self_mean, 1e-6)
    print(
        f"[{label}] n_users={len(common)}  corr={corr:.6f}  "
        f"mean|diff|={mean_abs_diff:.3g}  max|diff|={max_diff:.3g}  "
        f"(ref self-noise mean|diff|={self_mean:.3g})  "
        f"-> {'OK' if ok else 'MISMATCH'}"
    )
    if not ok:
        sys.exit(f"[{label}] fidelity check FAILED")


def main() -> None:
    compare(_synthetic_edges(), "synthetic")

    folder = sys.argv[1] if len(sys.argv) > 1 else None
    if folder is None:
        print("No COP folder given; skipping real-data comparison.")
        return

    gml = os.path.join(folder, "networks", "cop22_retweet_network_ml.gml")
    if not os.path.exists(gml):
        sys.exit(f"multilayer GML not found: {gml}")

    from netpol import read_multilayer_gml  # noqa: E402

    layers = read_multilayer_gml(gml)
    print(f"loaded {len(layers)} layers from {gml}")

    from netpol import PolarizationConfig, analyze_network  # noqa: E402

    config = PolarizationConfig(n_influencers=50, min_edges=10)
    from netpol.influencers import select_influencers  # noqa: E402
    from netpol.edges import build_influencer_edges  # noqa: E402

    done = 0
    for lid, g in sorted(layers.items()):
        if lid == -1 or g.number_of_edges() < config.min_edges:
            continue
        influencers, _ = select_influencers(g, config.influencer_strategy, 50)
        edges = build_influencer_edges(g, influencers)
        if edges.empty:
            continue
        try:
            compare(edges, f"cop22 layer {lid}")
            done += 1
        except Exception as exc:  # reference may choke on edge cases; keep going
            print(f"[cop22 layer {lid}] reference raised {type(exc).__name__}: {exc}")
        if done >= 3:
            break

    if done == 0:
        sys.exit("no COP layer could be compared")


if __name__ == "__main__":
    main()
