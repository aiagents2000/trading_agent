"""Dati di mercato. Default: dati pubblici via ccxt (nessuna chiave necessaria)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

import pandas as pd

from trading_agent.data.features import compute_features
from trading_agent.domain import MarketSnapshot


class MarketDataProvider(Protocol):
    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """OHLCV indicizzato per timestamp UTC di apertura barra, solo barre CHIUSE."""
        ...


class CcxtMarketData:
    def __init__(self, exchange_id: str = "binance") -> None:
        import ccxt

        self._exchange = getattr(ccxt, exchange_id)({"enableRateLimit": True})

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        raw = self._exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit + 1)
        df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        df = df.set_index("ts")
        # L'ultima barra restituita dall'exchange è ancora aperta: la scartiamo.
        return df.iloc[:-1]


def build_snapshot(
    symbol: str,
    timeframe: str,
    ohlcv: pd.DataFrame,
    news: list[str] | None = None,
) -> MarketSnapshot:
    last_ts = ohlcv.index[-1]
    as_of = last_ts.to_pydatetime() if isinstance(last_ts, pd.Timestamp) else datetime.now(UTC)
    features = compute_features(ohlcv)
    return MarketSnapshot(
        symbol=symbol,
        timeframe=timeframe,
        as_of=as_of,
        last_price=features["close"],
        features=features,
        news=news or [],
    )
