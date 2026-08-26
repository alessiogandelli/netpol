# netpol — engineering spec (v0.1, hand-off to coding agent)

Working name: **`netpol`** — `[REVISIT: check PyPI/GitHub for name
collisions before registering]`. Package/import name: `netpol`.

Purpose: implementable spec for a minimal, correct first version. Trimmed
deliberately — no speculative plugin architecture, no packaging ceremony
that isn't needed to start writing code. Add structure later when a
second real use case actually demands it, not preemptively.

Companion docs (consult only when resolving a `[REVISIT]` item, not
needed to start coding):
- `polarization_lib_design_spec.md` — methodological reasoning.
- `tool_vs_paper_strategy_discussion.md` — why this is a separate tool
  from the climate/COP26 paper.

---

## 1. Package basics

- License: MIT.
- Python: 3.10+.
- Runtime dependencies: `networkx>=3.0`, `pandas>=2.0`, `numpy>=1.24`,
  `diptest>=0.8`. No `uunet` dependency.
- Dev dependencies: `pytest>=7.0`.
- That's it for setup — no lint/type-check/coverage gates, no
  `CITATION.cff`/`CHANGELOG.md` yet. Add those when preparing an actual
  release, not now.

## 2. Package layout

```
netpol/
  __init__.py         public API exports
  config.py             PolarizationConfig
  influencers.py         select_influencers() — one file, no sub-package
  edges.py                build_influencer_edges()
  scoring.py                IdeologyScorer protocol
  bimodality.py               dip_test(), apply_fdr_correction()
  layer_result.py               LayerResult
  pipeline.py                     analyze_layer(), analyze_layers()
tests/
  fixtures.py
  test_influencers.py
  test_edges.py
  test_bimodality.py
  test_pipeline.py
examples/
  quickstart.py
pyproject.toml
README.md
LICENSE
```

Six small modules instead of a nested package. Flatten further if any of
these end up under ~20 lines each.

## 3. Input contract

- Single-layer functions take a `networkx.DiGraph`.
- Multi-layer orchestration takes `dict[Hashable, networkx.DiGraph]`.
- Directed graphs only — raise `TypeError` if given an undirected graph.
  `[REVISIT if a use case needs undirected support]`
- Edge convention, fixed: `a -> b` means "a retweets/endorses b". State
  this once, clearly, in the README and in `edges.py`'s module docstring.
  No `MultiDiGraph` support in v0.1 — raise `TypeError` if given one.

## 4. Config

```python
@dataclass(frozen=True)
class PolarizationConfig:
    influencer_strategy: str = "in_degree"   # "degree" | "in_degree" — see §5
    n_influencers: int = 30
    ideology_dimensions: int = 2
    significance_level: float = 0.05
    fdr_correction: bool = True
    min_edges: int = 10
    exclude_layers: tuple = ()
    random_seed: int | None = None
```

No `influencer_scope`, no `normalization_method` in v0.1 — both are
genuinely open design questions (see design-spec) and don't need a
config slot until an implementation exists behind it. Adding a config
field for a feature that doesn't exist yet just invites confusion.

Validation in `__post_init__`: `n_influencers > 0`, `0 < significance_level
< 1`, `ideology_dimensions >= 1`, `min_edges >= 0`, `influencer_strategy
in {"degree", "in_degree"}`.

## 5. Influencer selection

One function, not a plugin system:

```python
def select_influencers(
    graph: nx.DiGraph, strategy: str, n: int
) -> tuple[list, list]:
    """Rank nodes by 'degree' (total) or 'in_degree', descending.
    Ties broken by node id (stringified) ascending, for determinism.
    Returns (influencers, others), split at n.
    If n >= number of nodes, `others` is empty (do not raise)."""
```

Implement `"degree"` and `"in_degree"` inline (small `if/elif`, or a
`dict[str, Callable]` lookup — whichever is less code). Default is
`"in_degree"` `[REVISIT once source-method paper's actual choice is
confirmed — see design-spec §3a]`.

Authority/HITS-based ranking: **not in v0.1.** Add it as a third branch
in this same function when it's actually needed — don't build a
Protocol/registry for it ahead of time.

## 6. Edge construction

```python
def build_influencer_edges(graph: nx.DiGraph, influencers: list) -> pd.DataFrame:
    """Columns: ['influencer', 'user']. One row per edge INTO an
    influencer. Excludes self-loops. No deduplication, no special-casing
    of influencer-influencer edges."""
```

Build as a list of dicts → single `pd.DataFrame(...)` call. This is the
one hard performance requirement carried over from the original script
review (was `pd.concat` in a nested loop — must not regress). Everything
else in this spec is negotiable; this isn't.

## 7. Ideology scoring — the one place a real interface is required

This has to be a plug point, not a shortcut, because `latent_ideology`
isn't redistributable:

```python
class IdeologyScorer(Protocol):
    def score(self, edges: pd.DataFrame, n_dimensions: int) -> pd.DataFrame:
        """edges has columns ['influencer','user'].
        Returns a DataFrame indexed by node id with columns
        ['score_1', ..., 'score_n']. Raises ValueError if edges is empty."""
```

`netpol` ships **no default implementation** of this — the core
package must import and be testable with zero ideology-scoring
dependency installed. Provide one example adapter in `examples/`
wrapping a `latent_ideology`-style object, but keep it out of the
package itself.

Tests use a `FakeIdeologyScorer` (fixed, precomputed scores) — see §9.

## 8. Bimodality

```python
def dip_test(scores: np.ndarray) -> tuple[float, float]:
    """Hartigan's dip statistic and p-value. Raises ValueError if
    len(scores) < 4."""

def apply_fdr_correction(pvalues: dict) -> dict:
    """Benjamini-Hochberg, dependency-free (no statsmodels).
    Handles {} -> {} and single-element input without error."""
```

No `effect_size()` in v0.1 — leaving it out entirely rather than
shipping a placeholder marked "don't trust this." Add it once there's a
citation backing a specific measure (design-spec §5). No normalization
module either, for the same reason — `[REVISIT]` both once the
methodology settles.

## 9. Result type and pipeline

```python
@dataclass
class LayerResult:
    layer_id: Hashable
    n_nodes: int
    n_edges: int
    influencers: list
    scores: pd.DataFrame | None
    dip_statistic: float | None
    p_value: float | None
    adjusted_p_value: float | None = None
    is_polarized: bool | None = None
    skip_reason: str | None = None

    @property
    def was_analyzed(self) -> bool: ...

def analyze_layer(graph, config, ideology_scorer) -> LayerResult: ...
def analyze_layers(layers: dict, config, ideology_scorer) -> dict[Hashable, LayerResult]: ...
```

`ideology_scorer` passed in explicitly (dependency injection) so
`pipeline.py` is testable with `FakeIdeologyScorer`, no external
dependency required.

`analyze_layers` applies FDR correction across all layers with a
non-`None` `p_value`. No bare `except:` anywhere in the pipeline — every
skip path sets a specific, human-readable `skip_reason` instead of
silently swallowing an exception. This is a direct fix for the bug found
in the original script and is non-negotiable.

## 10. Test fixtures (`tests/fixtures.py`)

Keep to what's actually needed to test the functions above:

1. `star_graph()` — one hub, 5 in-edges. Tests both influencer
   strategies unambiguously.
2. `tied_degree_graph()` — two nodes with equal degree, tests the
   tie-break rule.
3. `bimodal_scores()` / `unimodal_scores()` — plain numpy arrays (not
   even graphs needed) to test `dip_test` directly.
4. `FakeIdeologyScorer` — returns fixed precomputed scores, used with a
   small graph fixture to test `analyze_layer` end-to-end without the
   real dependency.
5. `sparse_layer()` — fewer edges than `min_edges` — `analyze_layer`
   returns `skip_reason` set, does not raise.

That's five fixtures, not the longer list from the earlier draft —
enough to hand-check every code path without over-building the test
harness before there's real code to test against.

## 11. Definition of done for v0.1

- [ ] Modules in §2 implemented, exported from `__init__.py`.
- [ ] `pytest tests/` passes.
- [ ] `build_influencer_edges` uses a single `pd.DataFrame(...)` call —
      no `pd.concat` in a loop anywhere in the package.
- [ ] No bare `except:` anywhere in `pipeline.py`.
- [ ] `examples/quickstart.py` runs end-to-end using `FakeIdeologyScorer`
      (so it's runnable without the real ideology dependency installed).
- [ ] README states: install instructions, the `a -> b` edge convention,
      a short "what this does / doesn't do yet" list pulling in the
      `[REVISIT]` items from this doc.

No coverage percentage gate, no `mypy` requirement, no JOSS-readiness
checklist for v0.1 — those get added once the core is working and you're
actually preparing a release.

## 12. Explicitly deferred (not designed yet, not just unimplemented)

- Influencer scope beyond per-layer (global/hybrid) — no interface
  drafted, don't add a config field or stub method for it.
- Adaptive/proportional influencer pool sizing.
- Authority/HITS-based influencer ranking.
- Effect-size measure alongside the dip test.
- Score normalization across layers.
- Any packaging/release ceremony (CI, CITATION.cff, docs site, JOSS
  submission prep).

Each of these gets designed when there's a concrete reason to build it —
not speculatively now.
