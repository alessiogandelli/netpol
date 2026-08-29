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
from netpol import PolarizationConfig, analyze, LatentIdeologyScorer

def polarized_network():           # two camps, each retweeting one influencer
    g = nx.DiGraph()
    for i in range(100):
        g.add_edge(f"c1_{i}", "inf_1")
        g.add_edge(f"c2_{i}", "inf_2")
    return g

config = PolarizationConfig(n_influencers=2, min_edges=1)
result = analyze(polarized_network(), config, LatentIdeologyScorer(min_sources=1))
print(result.is_polarized)         # True
```

For a multilayer network, pass a `dict[layer_id, DiGraph]` instead -- the
same `analyze` call (or `analyze_layers` explicitly) returns a
`dict[layer_id, LayerResult]` with FDR correction across layers:

```python
results = analyze({"l1": layer1(), "l2": layer2()}, config)
print(results["l1"].is_polarized)
```

You don't have to load the networks yourself: every entry point also accepts
a path -- to a plain networkx GML file (single network), a multilayer GML
(`*_retweet_network_ml.gml`), or a topiclayers output folder -- and loads
the right shape automatically:

```python
from netpol import PolarizationConfig, analyze

result = analyze("networks/projected/cop22__prj_1.gml", config)    # LayerResult
results = analyze("networks/cop22_retweet_network_ml.gml", config) # Results
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

Across layers, `analyze` / `analyze_layers` applies Benjamini-Hochberg FDR
correction to the per-layer p-values and re-evaluates `is_polarized` against
the adjusted values.

## API

Everything public is importable from the package root, so `netpol.` autocompletes
the full surface in your IDE.

Entry points:

- `analyze(target, config, scorer=None)` -- top-level entry point. Pass a
  single `nx.DiGraph` (or a path to a plain GML file) and get a
  `LayerResult`, or a `dict[layer_id, DiGraph]` (or a path to a multilayer
  GML / topiclayers output folder) and get a `dict[layer_id, LayerResult]`
  (with FDR correction).
- `analyze_network(graph, config, scorer=None)` -> `LayerResult` -- the
  single-network primitive. Also accepts a path to a plain GML file.
- `analyze_layers(layers, config, scorer=None)` -> `dict[layer_id, LayerResult]` --
  the multilayer orchestration. Also accepts a path to a multilayer GML or
  output folder.

Configuration and results:

- `PolarizationConfig` -- frozen config dataclass (see `netpol/config.py`).
  `influencer_strategy` is typed `Literal["degree", "in_degree"]`.
- `LatentIdeologyScorer(min_sources=2, max_sources=None)` -- built-in scorer.
- `IdeologyScorer` -- `Protocol` to plug in your own scoring.
- `load_network(path)` -> `nx.DiGraph` -- load a single plain GML file as a
  directed graph (direction fixed up, `MultiDiGraph` rejected).
- `load_layers(path)` / `read_multilayer_gml(path)` -> `dict[layer_id, DiGraph]` --
  explicit loaders if you prefer to load before analyzing.
- `LayerResult` -- what you get back per network/layer:

  | field | type | meaning |
  |---|---|---|
  | `layer_id` | `Hashable \| None` | layer id (`None` for single networks) |
  | `n_nodes`, `n_edges` | `int` | size of the analyzed graph |
  | `influencers` | `list[Hashable]` | selected influencer node ids |
  | `scores` | `DataFrame \| None` | ideology scores, indexed by node id, columns `score_1..score_n`, values in `[-1, 1]` |
  | `dip_statistic`, `p_value` | `float \| None` | Hartigan's dip test output |
  | `adjusted_p_value` | `float \| None` | BH-adjusted p-value (multilayer + FDR only) |
  | `is_polarized` | `bool \| None` | p-value (adjusted if available) below `significance_level` |
  | `skip_reason` | `str \| None` | why the layer was skipped, if it was |
  | `was_analyzed` | `bool` | property: `True` iff scoring and dip test ran |

Type aliases (documented in `netpol/types.py`) make the data shapes explicit:

- `LayerId = Hashable`
- `Layers = dict[LayerId, nx.DiGraph]`
- `Results = dict[LayerId, LayerResult]`
- `InteractionTable = DataFrame` with columns `['influencer', 'user']`
- `ScoreTable = DataFrame` indexed by node id with columns `score_1..score_n`

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
