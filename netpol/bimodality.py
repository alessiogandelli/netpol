"""Bimodality / multimodality statistics.

Hartigan's dip test detects deviations from unimodality; this is the
"polarization signal" used by the pipeline.  Multiple-comparisons handling
(Benjamini-Hochberg) is kept here as a dependency-free helper so it can be
applied across layers at the orchestration level.
"""

from __future__ import annotations

import numpy as np
import diptest


def dip_test(scores: np.ndarray) -> tuple[float, float]:
    """Hartigan's dip test on a 1-D score distribution.

    Args:
        scores: 1-D array of ideology scores.

    Returns:
        ``(dip_statistic, p_value)``.

    Raises:
        ValueError: if ``len(scores) < 4`` (too little data for a meaningful
            dip test).
    """
    scores = np.asarray(scores, dtype=float).ravel()
    if len(scores) < 4:
        raise ValueError(
            f"dip test requires at least 4 scores, got {len(scores)}"
        )
    dip, p_value = diptest.diptest(scores)
    return float(dip), float(p_value)


def apply_fdr_correction(pvalues: dict) -> dict:
    """Benjamini-Hochberg FDR correction, dependency-free.

    Args:
        pvalues: Mapping ``key -> raw p-value``.

    Returns:
        Mapping ``key -> adjusted p-value``.  Handles ``{}`` and single-entry
        inputs without error.
    """
    if not pvalues:
        return {}

    keys = list(pvalues.keys())
    values = np.asarray([pvalues[k] for k in keys], dtype=float)

    n = len(values)
    order = np.argsort(values)
    adjusted = np.empty(n, dtype=float)
    running_min = np.inf
    for rank in range(n - 1, -1, -1):
        idx = order[rank]
        q = values[idx] * n / (rank + 1)
        running_min = min(running_min, q)
        adjusted[idx] = running_min
    adjusted = np.minimum(adjusted, 1.0)

    return {k: float(a) for k, a in zip(keys, adjusted)}
