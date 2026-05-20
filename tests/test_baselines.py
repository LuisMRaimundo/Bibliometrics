import numpy as np

from bibliometric_analysis.baselines.histograms import (
    baseline_errors_from_hist,
    distribution_from_counts,
    mean_from_hist,
    quantile_from_hist,
)


def test_mean_from_hist():
    v = np.array([0, 1, 2], dtype=float)
    c = np.array([2, 1, 1], dtype=float)
    assert np.isclose(mean_from_hist(v, c), 0.75)


def test_mean_empty():
    assert np.isnan(mean_from_hist(np.array([]), np.array([])))


def test_quantile_cdf_min():
    v = np.array([0, 1, 2, 3, 4], dtype=float)
    c = np.ones(5)
    assert quantile_from_hist(v, c, 0.80, method="cdf_min") == 3.0


def test_quantile_hazen():
    v = np.array([0, 1, 2, 3, 4], dtype=float)
    c = np.ones(5)
    q = quantile_from_hist(v, c, 0.80, method="hazen")
    assert q >= 3.0


def test_quantile_empty():
    assert np.isnan(quantile_from_hist(np.array([1.0]), np.array([0.0]), 0.9))


def test_distribution_from_counts():
    d = distribution_from_counts({0: 50, 1: 30, 2: 15, 5: 5})
    assert d["N"] == 100
    assert d["mean"] > 0
    assert d["q90"] >= d["q75"]


def test_distribution_empty():
    d = distribution_from_counts({})
    assert np.isnan(d["mean"])


def test_baseline_errors_reproducible():
    v = np.array([0, 1, 2, 3], dtype=float)
    c = np.array([40, 30, 20, 10], dtype=float)
    a = baseline_errors_from_hist(v, c, [0.75, 0.90], B=200, random_state=42)
    b = baseline_errors_from_hist(v, c, [0.75, 0.90], B=200, random_state=42)
    assert a == b
    assert "err_c0_pct" in a
