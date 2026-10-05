"""Paper broker interno: fee e slippage configurabili, nessuna chiave, nessun rischio.

È il broker di default della Fase 1. Gli adapter verso exchange demo (Binance Demo Mode,
Kraken CLI paper) e Alpaca paper arrivano in Fase 2 dietro la stessa interfaccia.
"""

from __future__ import annotations

from datetime import UTC, datetime

from trading_agent.domain import Fill, Order, OrderSide, PortfolioState, Position


class PaperBroker:
    def __init__(self, initial_equity: float, fee_rate: float = 0.001, slippage_bps: float = 5.0):
        self._cash = initial_equity
        self._peak = initial_equity
        self._positions: dict[str, Position] = {}
        self._prices: dict[str, float] = {}
        self._fills: dict[str, Fill] = {}
        self._trades_today = 0
        self.fee_rate = fee_rate
        self.slippage_bps = slippage_bps

    @property
    def fills(self) -> list[Fill]:
        return list(self._fills.values())

    def _equity(self) -> float:
        value = sum(
            p.quantity * self._prices.get(sym, p.avg_price) for sym, p in self._positions.items()
        )
        return self._cash + value

    def portfolio(self) -> PortfolioState:
        equity = self._equity()
        self._peak = max(self._peak, equity)
        return PortfolioState(
            cash=self._cash,
            equity=equity,
            peak_equity=self._peak,
            positions=dict(self._positions),
            trades_today=self._trades_today,
        )

    def mark_to_market(self, prices: dict[str, float]) -> PortfolioState:
        self._prices.update(prices)
        return self.portfolio()

    def reset_daily_counter(self) -> None:
        self._trades_today = 0

    def submit(self, order: Order, market_price: float) -> Fill:
        if order.client_order_id in self._fills:  # idempotenza
            return self._fills[order.client_order_id]

        slip = self.slippage_bps / 10_000
        sign = 1 if order.side is OrderSide.BUY else -1
        price = market_price * (1 + sign * slip)
        notional = order.quantity * price
        fee = notional * self.fee_rate

        if order.side is OrderSide.BUY and notional + fee > self._cash:
            raise ValueError("Cash insufficiente per l'ordine paper")

        current = self._positions.get(
            order.symbol, Position(symbol=order.symbol, quantity=0, avg_price=price)
        )
        new_qty = current.quantity + sign * order.quantity
        if order.side is OrderSide.BUY:
            total_cost = current.quantity * current.avg_price + order.quantity * price
            avg = total_cost / new_qty if new_qty else price
        else:
            avg = current.avg_price

        self._cash -= sign * notional + fee
        if abs(new_qty) < 1e-12:
            self._positions.pop(order.symbol, None)
        else:
            self._positions[order.symbol] = Position(
                symbol=order.symbol, quantity=new_qty, avg_price=avg
            )
        self._prices[order.symbol] = market_price
        self._trades_today += 1

        fill = Fill(
            client_order_id=order.client_order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=price,
            fee=fee,
            filled_at=datetime.now(UTC),
        )
        self._fills[order.client_order_id] = fill
        return fill
