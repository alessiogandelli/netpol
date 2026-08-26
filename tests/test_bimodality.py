import numpy as np
import pytest

from netpol.bimodality import apply_fdr_correction, dip_test

from .fixtures import bimodal_scores, unimodal_scores


def test_dip_test_bimodal_rejects_unimodality():
    _, p = dip_test(bimodal_scores())
    assert p < 0.05


def test_dip_test_unimodal_fails_to_reject():
    _, p = dip_test(unimodal_scores())
    assert p >= 0.05


def test_dip_test_too_few_scores_raises():
    with pytest.raises(ValueError):
        dip_test(np.array([1.0, 2.0, 3.0]))


def test_fdr_empty():
    assert apply_fdr_correction({}) == {}


def test_fdr_single():
    assert apply_fdr_correction({"a": 0.03}) == {"a": 0.03}


def test_fdr_known_case():
    # classic BH example: p = [0.01, 0.04, 0.03, 0.005]
    # adjusted (m=4): 0.005*4/1=0.02; 0.01*4/2=0.02; 0.03*4/3=0.04; 0.04*4/4=0.04
    pvalues = {"a": 0.01, "b": 0.04, "c": 0.03, "d": 0.005}
    adj = apply_fdr_correction(pvalues)
    assert adj["d"] == pytest.approx(0.02)
    assert adj["a"] == pytest.approx(0.02)
    assert adj["c"] == pytest.approx(0.04)
    assert adj["b"] == pytest.approx(0.04)
