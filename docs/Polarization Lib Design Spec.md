# polarization-lib — design spec (pre-implementation)

Status: **spec only, no code yet.** This document exists so the reasoning
behind each design choice is captured before implementation starts, since
several of these choices are methodological and will need to be defended
in a paper's methods section, not just in code comments.

---

## 1. Scope and packaging

- Standalone package, intended for PyPI.
- Core dependency: `networkx` only for graph representation. The package
  does **not** depend on `uunet` or any specific multilayer-network
  library — callers are responsible for converting their multilayer
  network into a plain `dict[layer_id, networkx.Graph]` before calling in.
  This keeps the dependency footprint light and decouples the package from
  any one multilayer-network tool's data model.
- `latent_ideology` (the correspondence-analysis step) is not published on
  PyPI. Two options, decide before implementation:
  - (a) vendor a copy of the algorithm into this package, or
  - (b) make ideology scoring **pluggable**: accept any callable matching a
    fixed signature (edges in, per-node scores out), so users without that
    exact dependency can supply their own implementation.
  - Leaning toward (b) for a public package — lower maintenance burden,
    avoids redistributing someone else's unpublished code.

## 2. API contract: single graph vs. multilayer

Two-layer design, not an auto-detecting function:

1. **Primitive**: one function that takes a single graph and returns a
   single result. This is the real unit of work — testable in isolation,
   usable standalone by someone with just one retweet network and no
   topic/layer structure at all.
2. **Orchestration**: a thin layer that takes `dict[layer_id, Graph]`,
   calls the primitive per layer, and additionally performs the one thing
   that is genuinely cross-layer: multiple-comparisons (FDR) correction
   across all layers' p-values. This cannot be computed layer-by-layer in
   isolation, so it belongs at the orchestration level only.

## 3. Influencer selection

Two **orthogonal** config axes — do not couple them:

### 3a. Selection strategy (how "influencer" is scored)
Pluggable, at least three options at launch:
- naive degree (in + out) — current/baseline behavior
- in-degree only — better proxy for "gets retweeted a lot" (authority)
  vs. "retweets a lot" (hub); in-degree and out-degree conflate two
  different roles in a retweet network
- authority score (e.g. HITS, or in-degree weighted by the retweeter's own
  reach) — more robust to inflation by high-volume/bot-like accounts
- **TODO (research, before implementation):** cite literature justifying
  the chosen default among these (retweet-network influence measures,
  HITS vs. degree centrality in polarization studies).

### 3b. Selection scope (stability of the influencer set across layers)
Three candidate designs, discussed and compared:

| Option | Description | Pro | Con |
|---|---|---|---|
| **A. Topic-relative** (current behavior) | Recompute top-N independently per layer | Captures who's actually central *within* that specific discourse; simple to defend methodologically | "Influencer" isn't a stable identity across topics — can't track a specific account's ideology across topics, only aggregate polarization per topic |
| **B. Global pool** | Rank once on the full/aggregate network, use the same fixed set inside every layer's subgraph | Stable identity — enables tracking the same accounts' scores moving across topics | Globally huge accounts may have near-zero presence in a niche topic, wasting influencer slots; global influencers may not be who actually drives a niche topic |
| **C. Hybrid** | Larger global candidate pool (e.g. top 200), then within each layer keep only candidates present there, ranked by in-layer degree | Stable identity, doesn't burn slots on absent accounts, effective per-layer count adapts naturally | Two thresholds to justify (candidate pool size + per-layer presence), more complex to describe in a methods section |

**Decision:** default to **A** for the initial implementation (simpler to
defend, matches current script behavior, sufficient if the paper's central
claim is "how polarized is each topic" rather than "does this specific
actor's ideology shift across topics"). Make the scope pluggable so **B**
and **C** are a config flag away, to run as a robustness check once the
paper's actual research question is finalized.

**Open, not yet decided:** preference leans toward **C** long-term, but
this needs a computational-cost evaluation first (global ranking cost +
per-layer filtering cost, at the scale of the real dataset) before
committing it as anything more than an opt-in alternative. Revisit after
profiling.

### 3c. Pool size (how many influencers)
- Currently a flat constant (`n_influencers=30`) applied uniformly
  regardless of layer size — a 500-node topic and a 50,000-node topic both
  get exactly 30 influencers.
- Alternatives to evaluate: proportional sizing (e.g. top 1% of layer
  nodes), or a data-driven cutoff (elbow/knee detection on the degree or
  authority-score distribution) instead of a fixed top-k.
- **TODO (research, before implementation):** cite literature on
  choosing influencer-set size / cutoff methods in social-network
  polarization studies; this is independent of which strategy (3a) is
  used and independent of scope (3b).

## 4. Edge construction

- **Fixed convention:** `a retweets b` → directed edge `a → b`. Decided
  and not up for debate.
- No special-casing of influencer–influencer edges: if both `a` and `b`
  happen to be selected influencers, the edge is still built as a normal
  edge. Influencer selection and edge construction are fully decoupled —
  the edge-building step doesn't need to know how influencers were
  chosen, only which node IDs are influencers.
- This holds regardless of which influencer-selection strategy (3a) or
  scope (3b) is active upstream.

## 5. Polarization signal

- Hartigan's dip test alone is **not sufficient**: a distribution with one
  large cluster and one tiny outlier cluster is technically non-unimodal
  but isn't what "polarized" should mean substantively. Pair the dip
  test's significance result with a separation/effect-size measure (e.g.
  a bimodality coefficient, or cluster-separation from a 2-means fit) so
  "statistically not-unimodal" and "substantively polarized" are reported
  as two distinct things, not conflated into one p-value.
- **TODO (research, before implementation):** find and cite a paper that
  supports "bimodality of a latent ideology score = polarization" as a
  construct — this is a foundational methodological claim for the paper
  and needs a citation, not just an implementation assumption.
- **Write down for the paper (not just as a TODO — a required
  methods-section note):** every decision in this document that shapes
  what counts as "polarized" — selection strategy, selection scope, pool
  size, effect-size threshold, normalization method — is a methodological
  choice that affects the result, not an implementation detail. These
  need to be stated explicitly and justified in the paper, and ideally
  accompanied by a robustness check showing the finding holds (or how it
  changes) under the alternative options listed in this document.

## 6. Dimensionality

- `compute_ideology_scores` supports `n_dimensions` as a parameter.
- **Default: 2** (not 1). Previous draft used 1D by default; corrected
  per discussion.
- Open question, not yet resolved: when `n_dimensions > 1`, does the dip
  test run per-dimension independently, or does polarization need a
  proper multivariate modality test across all dimensions at once? Revisit
  once the effect-size measure (§5) is chosen, since the two are related.

## 7. Normalization

- Scores must be normalized before any cross-layer comparison (e.g.
  ranking "most polarized" topics), since raw dip statistics are
  sample-size sensitive and layers vary widely in node count. Confirmed
  as a requirement; exact normalization method (z-score per layer,
  rank-based, size-adjusted dip statistic, etc.) still to be chosen.

## 8. Statistical rigor (carried over, already agreed)

- Benjamini-Hochberg FDR correction applied across all layers' p-values at
  the orchestration level (§2), not per-layer in isolation. Default on.
- `min_edges` guardrail before attempting ideology scoring on a layer, with
  an explicit `skip_reason` on failure/skip rather than silently swallowing
  errors.

## 9. Config parameters (draft list, to formalize once decisions above are finalized)

- `influencer_strategy`: degree | in_degree | authority (pluggable)
- `influencer_scope`: per_layer (A) | global (B) | hybrid (C)
- `influencer_pool_size`: fixed int | proportional | adaptive-cutoff
- `ideology_dimensions`: int, default 2
- `significance_level`: float, default 0.05
- `fdr_correction`: bool, default True
- `min_edges`: int
- `exclude_layers`: tuple of layer ids
- `normalization_method`: TBD once §7 is resolved

## 10. Outstanding TODOs before implementation

1. Cite literature for influencer selection strategy default (§3a).
2. Cite literature for influencer pool sizing method (§3c).
3. Profile computational cost of scope option C (global candidate pool +
   per-layer filtering) at real dataset scale, to decide whether it can
   become the default later (§3b).
4. Find and cite the paper grounding "bimodality of latent ideology score
   = polarization" (§5).
5. Choose the effect-size/separation measure to pair with the dip test
   (§5).
6. Resolve per-dimension vs. multivariate modality testing for
   `ideology_dimensions > 1` (§6).
7. Choose normalization method for cross-layer comparison (§7).
8. Decide vendoring vs. pluggable-callable for `latent_ideology` (§1).
