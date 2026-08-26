# netpol — debatable points and decisions

This file records the methodological and engineering choices that could be
defended differently, plus what was decided for v0.1 and why.  Each item is
something a reviewer, or future-you, might reasonably push back on.  The
goal is that none of these are "accidental": every one is either a deliberate
decision, a known deviation, or a flagged open question.

Companion docs: `Polarization Lib Design Spec.md` (methodology),
`Engineering Spec for Code Schematization.md` (implementation), and
`Tool vs Paper Strategy Discussion.md` (why this is a separate tool from the
climate/COP26 paper).

---

## 1. `latent-ideology` is actually on PyPI — but netpol vendors its own

The design spec assumed the reference implementation ("latent-ideology", Fede
Moss, MIT) was not published.  **It is on PyPI** (`latent-ideology==0.0.8.2`,
MIT).  Two options were on the table:

- (a) depend on it (optionally), or
- (b) vendor/rewrite the algorithm inside netpol.

**Decision:** (b).  netpol ships its own `LatentIdeologyScorer` in
`netpol/ideology.py`, maintained here and expected to be extended over time.
The `IdeologyScorer` `Protocol` still lets anyone plug in the PyPI package or
their own code, so (a) remains a one-class swap away.

- **Why this is debatable:** relying on the upstream package would reduce
  maintenance and guarantee fidelity to the original.  Vendoring means netpol
  now *owns* the method's bugs and deviations (see §2, §3).
- **Risk to the paper:** a reviewer who knows the original method may compare
  netpol's numbers against `latent-ideology`'s.  The two must agree up to the
  deliberate, documented deviations below.

## 2. Deterministic SVD vs. `randomized_svd` (reproducibility)

The reference implementation uses `sklearn.utils.extmath.randomized_svd` with
`random_state=None`, so scores are **non-deterministic** run-to-run (global
sign flip / tiny numerical differences).  netpol uses `numpy.linalg.svd`
(deterministic LAPACK).

- **Why:** the `random_seed` config field in the engineering spec *cannot*
  seed `randomized_svd` from the outside.  Reproducibility of the paper's
  exact numbers requires a deterministic factorization.
- **Cost:** `numpy.linalg.svd` is exact (not randomized).  For a
  `users x influencers` matrix with `influencers ~ 30-100`, this is cheap
  (the matrix is tall-and-skinny).  Only matters at scale; re-profile before
  running on huge layers.
- **Fidelity risk:** `randomized_svd` and `linalg.svd` can differ in the sign
  of a component.  The dip test is invariant to a global sign flip, but the
  *reported scores* will differ.  If the paper reports raw score values, this
  deviation must be stated.

## 3. The meaning of `n` (the `min_sources` filter) vs. dimensionality

This is the single most confusing point in the original code.

- In `latent_ideology.apply_method(n=2, targets='user', sources='influencer')`,
  **`n` is not the number of dimensions.**  It is the *minimum number of
  distinct influencers a user must have retweeted* to be kept.  The original
  script calls `apply_method(n=2)` and `n=3` and then runs the dip test on a
  **single** `df1['score']` column — i.e. the ideology score is **1-D**, and
  `n` is a data-filtering threshold.
- `apply_method` never exposes dimensionality; multi-dim scores only exist via
  `make_adjacency()` + `calculate_scores(dimension=k)`.

**Decision:** netpol separates the two cleanly:

- `LatentIdeologyScorer(min_sources=2)` — the `n` filter, living on the scorer
  (scoring-method parameter), default 2 to match the original.
- `PolarizationConfig.ideology_dimensions=1` — the real dimensionality, default
  1 (bipolar single axis).

**Why this is debatable:** the engineering spec's `IdeologyScorer.score(edges,
n_dimensions)` conflated these two under one name.  `ideology_dimensions=2`
does **not** reproduce the original pipeline — it changes what's computed.

## 4. Default `ideology_dimensions` is 1 (a single bipolar axis)

The design spec said default 2 ("corrected per discussion").  Clarified during
implementation: **"2" meant bipolarity along one dimension** (scores on a
single left-right axis in `[-1, 1]`), not a 2-D embedding.  The source method
(Falkenberg, Flamino) uses a 1-D score, and the original script's dip test runs
on 1-D scores.

- **Decision:** `ideology_dimensions=1`.
- **Still open** (design spec §6): if `ideology_dimensions > 1`, the dip test
  only runs on `score_1` today.  A proper multivariate modality test (or
  per-dimension testing with its own multiple-comparisons handling) is not
  implemented.  This is deferred, not decided.

## 5. Default influencer strategy: `in_degree`, not total `degree`

The original script ranks influencers by **total degree** (`net.degree()`),
which conflates "retweets a lot" (hub) with "gets retweeted a lot" (authority)
in a retweet network.

- **Decision:** default `in_degree` (authority), per the engineering spec's
  `[REVISIT]`-flagged default.
- **Debatable:** this changes the influencer set and therefore the results
  vs. the original script.  If the paper wants to claim continuity with prior
  COP runs, it must either use `influencer_strategy="degree"` or explicitly
  justify the switch.
- **Open:** a citation justifying the default (design spec §3a) is still
  missing.  Authority/HITS ranking is explicitly deferred.

## 6. Self-loops are excluded from scoring

The engineering spec says exclude self-loops in `build_influencer_edges`.  The
original script *did not* remove them before scoring (it only removed them
later, when drawing).  A self-loop appears when an influencer retweets their
own content — rare but not impossible.

- **Decision:** exclude (spec).  **Debatable:** a pure-fidelity port would keep
  them; the practical effect on the dip test is expected to be negligible.

## 7. Dip test runs on user scores only

The original runs the dip test on `df1['score']` — the *users* (targets), not
the influencers.  Influencer scores (mean of their retweeters' scores) are
computed in the original but never dip-tested.

- **Decision:** reproduce this — dip test on user scores (`score_1`).
- **Debatable:** whether influencers should enter the distribution, and
  whether the *influencer* score distribution is itself a meaningful
  polarization signal, is an open question for the paper.

## 8. FDR correction changes which layers count as polarized

The original script declared a layer polarized iff raw dip-test `p < 0.05`
(and not layer `-1`), with **no** multiple-comparisons correction across the
~20-30 topic layers.

- **Decision:** `analyze_layers` applies Benjamini-Hochberg by default
  (`fdr_correction=True`), and `is_polarized` is re-evaluated against the
  **adjusted** p-value.
- **Consequence:** with FDR on, some layers that were "polarized" under the
  raw test will flip to not-polarized.  This is statistically more defensible
  (and PLOS ONE reviewers scrutinize exactly this), but it means the paper's
  headline "most polarized topics" list may differ from earlier drafts.

## 9. `min_edges=10` guardrail is arbitrary

The engineering spec adds a `min_edges` guard so tiny layers skip scoring
instead of crashing the scorer.  The original had no such guard and relied on
a bare `except:` to swallow failures.

- **Decision:** `min_edges=10`, with a human-readable `skip_reason`.
- **Debatable:** 10 is a made-up number.  A layer-size- or data-driven
  threshold (or the scorer's own `min_sources` filtering) is arguably more
  principled.  Needs a decision before the paper run.

## 10. Silent `except:` and the `l != -1` hack are removed

The original wrapped scoring in `try: ... except: continue` (swallowing all
errors) and hard-coded `l != -1` to drop a "no topic" layer.

- **Decision:** every failure path sets a specific `skip_reason`; the `-1`
  layer is excluded via `PolarizationConfig.exclude_layers=(-1,)` (a visible,
  configurable choice instead of an inline magic number).

## 11. Deferred (not designed, not just unimplemented)

Carried over verbatim from the engineering spec §12:

- Influencer-selection scope beyond per-layer (global/hybrid).
- Adaptive/proportional influencer pool sizing.
- Authority/HITS-based influencer ranking.
- Effect-size / separation measure alongside the dip test.
- Score normalization across layers.
- Packaging/release ceremony (CI, CITATION.cff, docs site, JOSS prep).

## Open research TODOs (unchanged from the design spec §10)

1. Cite literature for the influencer-selection default (§5).
2. Cite literature for influencer pool sizing.
3. Profile scope option C at real scale.
4. Cite the paper grounding "bimodality of latent ideology score = polarization".
5. Choose the effect-size measure to pair with the dip test.
6. Resolve per-dimension vs. multivariate modality testing for >1 dimension.
7. Choose normalization method for cross-layer comparison.
