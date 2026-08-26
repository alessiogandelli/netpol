# Strategy discussion — polarization tool + climate/COP26 paper (PLOS ONE)

Summary of a planning conversation. No code or final decisions here — this
is meant to be re-read with a fresh mind, not acted on immediately.

---

## The core reframing

Originally treated as one thing ("build a library, then write a paper
using it"). Reframed into **two separate deliverables with two separate
bars**:

1. **The tool** — a general-purpose, faithful, configurable implementation
   of an *established* polarization-measurement method (latent-ideology
   scoring + bimodality/dip test). Not a new method. Its job is to be
   correct, flexible, well-tested, and well-documented — not to make an
   empirical claim.
2. **The climate/COP26 paper** — uses the tool with **one specific,
   justified configuration** and reports empirical findings about
   polarization in climate discourse. Its contribution is the *finding*,
   not the pipeline.

Keeping these separate means the climate paper doesn't get "polluted"
with tool-design debates (influencer selection strategy, pool sizing,
scope A/B/C, etc.), and the tool doesn't need to carry the burden of
proving a novel scientific claim.

## Why this split matters practically

- **Tool's methods section problem disappears for the paper.** The
  climate paper's methods section can be short: "we used [tool] vX.Y
  (Author, year), configured with [specific settings], following
  [original method's paper]; full parameter listing in Appendix A." All
  the open design questions (see the design-spec doc) stay in the tool's
  own documentation/robustness tests, not in the paper's main text.
- **The tool doesn't need self-validation of the polarization construct**
  (i.e., proving "bimodality = polarization") — that's inherited from
  whichever original paper the method comes from, as long as it's cited
  and faithfully reproduced. Big reduction in scope versus treating this
  as a novel-methods paper.
- **The tool benefits from more configurability, not less** — flexibility
  across use cases is a strength for a general package, even though the
  paper itself only uses one configuration.

## Suggested publication path for the tool

- **JOSS (Journal of Open Source Software)** fits well: short
  peer-reviewed papers evaluating documentation, test coverage, and API
  design rather than methodological novelty.
- Get a **Zenodo DOI** on release so the tool is citable and versionable
  — this materially strengthens the climate paper's data/code
  availability section later.

## Why PLOS ONE fits the climate paper

- PLOS ONE's review criteria explicitly do **not** require novelty or
  "impact" — only technical soundness: appropriate methods, valid
  conclusions given the data, sufficient detail to replicate. Good match
  for "apply an established method to a new domain" framing.
- The tool/paper split works *in favor* of this: a separately citable,
  tested, documented tool strengthens the technical-soundness case rather
  than needing everything folded into one manuscript.

### What PLOS ONE reviewers will specifically scrutinize

1. **Statistical rigor** — multiple-comparisons handling (FDR correction)
   and p-value interpretation are known sticking points for PLOS ONE
   review. Having FDR correction and a separate effect-size/separation
   measure (not just the dip-test p-value alone) built into the method
   from the start is a real advantage, since this is a known area of
   pushback.
2. **Data and code availability.** PLOS ONE requires a Data Availability
   Statement and pushes for code availability. A versioned, DOI'd,
   general-purpose tool (via JOSS/Zenodo) makes this section far
   stronger than "code available on request."
3. **Reproducibility of the exact configuration used in this study.**
   Even though the tool is general-purpose, the paper still needs to
   spell out the *exact* parameters used (ideally as an appendix). The
   config-parameter list already drafted in the tool's design spec is
   essentially the skeleton of that appendix.
4. **Ethics for social-media data.** X/Twitter data draws scrutiny post-
   API-changes. Needs: data collection method, current shareability given
   API terms, and an anonymization/aggregation approach for any
   user-identifying information.

## The main reviewer-risk item identified

Not novelty (PLOS ONE doesn't require it) — the real risk is **fidelity
to the original method**. If the tool's default parameters (influencer
selection strategy, pool size, dimensionality, etc.) differ from the
canonical choices in whatever paper the latent-ideology + dip-test
approach originally comes from, a reviewer familiar with that original
method is likely to notice and question it. "We used the tool's
defaults" is not sufficient justification on its own — the defaults
themselves need to trace back to, or explicitly and defensibly deviate
from, the source method's own choices.

## Next concrete step identified (not yet done)

**Find the specific paper(s)** that the `latent_ideology` module + dip
test combination is based on, and confirm their canonical parameter
choices (influencer selection method, pool sizing, dimensionality,
significance handling). Use that to:

- Set the *tool's* sensible defaults to match the original method.
- Justify the *paper's* specific configuration against that source,
  which becomes the main defensible part of the methods section and the
  main pre-emption of likely reviewer pushback.

This is more consequential right now than resolving the open
implementation questions (influencer scope A/B/C, normalization method,
etc.) already logged in the tool design-spec document — those matter for
the tool's long-term flexibility, but the paper's core methodological
defense hinges on matching the original method, not on exploring the
full design space.

## Related, still-open items (carried over from the design spec, not re-litigated here)

- Citation for "bimodality of a latent-ideology score = polarization" as
  a construct.
- Effect-size/separation measure to pair with the dip test.
- Per-dimension vs. multivariate modality testing when using >1
  ideology dimension.
- Normalization method for cross-layer score comparison.
- Full parameter listing for the paper's Appendix A (draft skeleton
  already exists in the tool design-spec's "config parameters" section).

See `polarization_lib_design_spec.md` for the full parameter-level
design discussion this summary sits on top of.
