"""Interfaccia broker comune: paper interno, exchange demo via ccxt, Alpaca paper."""

from __future__ import annotations

import hashlib
from typing import Protocol

from trading_agent.domain import (
    Direction,
    Fill,
    Order,
    OrderSide,
    PortfolioState,
    TradeDecision,
)


class LiveTradingDisabledError(RuntimeError):
    """Sollevata se qualcuno prova a usare chiavi/endpoint live. Il live non è nello scope."""


class Broker(Protocol):
    def portfolio(self) -> PortfolioState: ...

    def submit(self, order: Order, market_price: float) -> Fill: ...

    def mark_to_market(self, prices: dict[str, float]) -> PortfolioState: ...


def decision_to_order(
    decision: TradeDecision, portfolio: PortfolioState, price: float
) -> Order | None:
    """Converte una decisione in ordine. Id deterministico → re-run idempotenti."""
    if decision.action != "execute" or decision.direction is Direction.FLAT:
        return None
    notional = portfolio.equity * decision.size_pct_equity
    quantity = notional / price
    if quantity <= 0:
        return None
    side = OrderSide.BUY if decision.direction is Direction.LONG else OrderSide.SELL
    key = f"{decision.symbol}|{decision.as_of.isoformat()}|{side}|{decision.size_pct_equity:.6f}"
    client_order_id = "ta-" + hashlib.sha256(key.encode()).hexdigest()[:16]
    return Order(
        client_order_id=client_order_id,
        symbol=decision.symbol,
        side=side,
        quantity=quantity,
        stop_loss=decision.stop_loss,
        take_profit=decision.take_profit,
    )
