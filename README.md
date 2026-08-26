# netpol

Measure polarization in (multilayer) social networks.

Given a network -- or a `dict` of per-layer networks -- `netpol` selects the
top influencers, scores every user on a **bipolar latent-ideology axis** via
correspondence analysis, and tests whether the resulting score distribution is
multimodal (polarized) using **Hartigan's dip test**, with optional
**Benjamini-Hochberg FDR correction** across layers.

The method follows Falkenberg et al. (2021) and Flamino et al. (2021).

## Install

```bash
pip install netpol
```

For local development:

```bash
git clone https://github.com/alessiogandelli/netpol && cd netpol
poetry install
poetry run pytest
```

## Edge convention

Fixed and non-negotiable:

> `a -> b` means **"a retweets/endorses b"**.

Pass `networkx.DiGraph`s only (undirected graphs and `MultiDiGraph`s raise
`TypeError`).  A multilayer network is just `dict[layer_id, DiGraph]`.

## Quickstart

```python
import networkx as nx
from netpol import LatentIdeologyScorer, PolarizationConfig, analyze_layers

def layer():                       # two camps, each retweeting one influencer
    g = nx.DiGraph()
    for i in range(100):
        g.add_edge(f"c1_{i}", "inf_1")
        g.add_edge(f"c2_{i}", "inf_2")
    return g

config = PolarizationConfig(n_influencers=2, min_edges=1)
results = analyze_layers({"l1": layer()}, config, LatentIdeologyScorer(min_sources=1))
print(results["l1"].is_polarized)   # True
```

See `examples/quickstart.py` for a runnable version.

## How it works

Per layer:

1. **Select influencers** -- top `n_influencers` nodes by `in_degree`
   (configurable) with deterministic tie-breaking.
2. **Build the interaction table** -- one row per edge *into* an influencer
   (`['influencer', 'user']`), self-loops excluded.
3. **Score users** -- correspondence analysis maps each user to a score in
   `[-1, 1]` on a bipolar ideology axis (the `IdeologyScorer` plug point; the
   built-in `LatentIdeologyScorer` is deterministic).
4. **Test for polarization** -- Hartigan's dip test on the score distribution.

Across layers, `analyze_layers` applies Benjamini-Hochberg FDR correction to
the per-layer p-values and re-evaluates `is_polarized` against the adjusted
values.

## API

- `PolarizationConfig` -- frozen config dataclass (see `netpol/config.py`).
- `analyze_layer(graph, config, scorer=None)` -> `LayerResult`
- `analyze_layers(layers, config, scorer=None)` -> `dict[layer_id, LayerResult]`
- `LatentIdeologyScorer(min_sources=2, max_sources=None)` -- built-in scorer.
- `IdeologyScorer` -- `Protocol` to plug in your own scoring.
- `LayerResult` -- `layer_id`, `n_nodes`, `n_edges`, `influencers`, `scores`,
  `dip_statistic`, `p_value`, `adjusted_p_value`, `is_polarized`, `skip_reason`.

## What this does / doesn't do (yet)

Does:

- Faithful, deterministic implementation of the latent-ideology + dip-test
  pipeline (single-layer and multilayer).
- FDR correction, explicit `skip_reason` on every failure path (no silent
  `except`), directed-graph validation, `min_edges` guardrail.

Does **not** do yet (see [`docs/DEBATES.md`](docs/DEBATES.md) for the open
questions and `[REVISIT]` items):

- Effect-size / separation measure paired with the dip test.
- Score normalization across layers for comparison.
- Multivariate modality testing for `ideology_dimensions > 1`.
- Influencer-selection scope beyond per-layer (global/hybrid), adaptive pool
  sizing, or authority/HITS ranking.

## References

- M. Falkenberg et al., "Growing polarisation around climate change on social
  media", arXiv:2112.12137 (2021).
- J. Flamino et al., "Shifting polarization and Twitter news influencers
  between two US presidential elections", arXiv:2111.02505 (2021).

## License

MIT. See `LICENSE`.
