import numpy as np

from trading_agent.lab import deflated_sharpe_ratio, sharpe_ratio


def test_dsr_penalises_many_trials() -> None:
    rng = np.random.default_rng(0)
    returns = rng.normal(0.001, 0.02, 500)
    few = deflated_sharpe_ratio(returns, n_trials=2, sharpe_variance=0.002)
    many = deflated_sharpe_ratio(returns, n_trials=500, sharpe_variance=0.002)
    assert many < few


def test_sharpe_zero_for_constant_series() -> None:
    assert sharpe_ratio(np.zeros(10)) == 0.0
