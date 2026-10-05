"""Feature registry: indicatori calcolati in modo deterministico, solo su barre già chiuse.

Gli agenti LLM ricevono questi numeri, non li calcolano. Ogni feature nuova va aggiunta qui
(e coperta da un test di non-lookahead), così il leakage resta "inesprimibile".
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    true_range = pd.concat(
        [df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False).mean()


def compute_features(ohlcv: pd.DataFrame) -> dict[str, float]:
    """Feature dell'ultima barra di `ohlcv`, che deve contenere solo barre chiuse."""
    missing = [c for c in REQUIRED_COLUMNS if c not in ohlcv.columns]
    if missing:
        raise ValueError(f"Colonne mancanti: {missing}")
    if len(ohlcv) < 50:
        raise ValueError("Servono almeno 50 barre per calcolare le feature")

    close = ohlcv["close"]
    ema_fast = close.ewm(span=12, adjust=False).mean()
    ema_slow = close.ewm(span=26, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=9, adjust=False).mean()
    sma_20 = close.rolling(20).mean()
    std_20 = close.rolling(20).std()
    sma_50 = close.rolling(50).mean()
    atr = _atr(ohlcv)
    log_ret = np.log(close).diff()

    last = close.iloc[-1]
    features = {
        "close": last,
        "return_1": close.pct_change(1).iloc[-1],
        "return_20": close.pct_change(20).iloc[-1],
        "rsi_14": _rsi(close).iloc[-1],
        "macd": macd.iloc[-1],
        "macd_signal": signal.iloc[-1],
        "macd_hist": (macd - signal).iloc[-1],
        "sma_20": sma_20.iloc[-1],
        "sma_50": sma_50.iloc[-1],
        "dist_sma_50_pct": (last / sma_50.iloc[-1]) - 1,
        "bb_zscore_20": (last - sma_20.iloc[-1]) / std_20.iloc[-1],
        "atr_14": atr.iloc[-1],
        "atr_pct": atr.iloc[-1] / last,
        "realized_vol_20": log_ret.rolling(20).std().iloc[-1],
        "volume_zscore_20": (
            (ohlcv["volume"].iloc[-1] - ohlcv["volume"].rolling(20).mean().iloc[-1])
            / ohlcv["volume"].rolling(20).std().iloc[-1]
        ),
    }
    return {k: float(v) for k, v in features.items() if pd.notna(v)}
