import pandas as pd

from trading_agent.cli import synthetic_ohlcv
from trading_agent.data import compute_features


def test_features_do_not_depend_on_future_bars() -> None:
    """Le feature al tempo t devono restare identiche se aggiungiamo barre future."""
    full = synthetic_ohlcv(300)
    cut = 200
    past_only = compute_features(full.iloc[:cut])

    shocked = full.copy()
    shocked.iloc[cut:, shocked.columns.get_loc("close")] *= 3  # futuro stravolto
    with_future_hidden = compute_features(shocked.iloc[:cut])

    pd.testing.assert_series_equal(pd.Series(past_only), pd.Series(with_future_hidden))


def test_core_features_present() -> None:
    feats = compute_features(synthetic_ohlcv(120))
    for key in ("rsi_14", "macd_hist", "atr_14", "dist_sma_50_pct"):
        assert key in feats
