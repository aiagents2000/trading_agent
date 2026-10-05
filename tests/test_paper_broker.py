import pytest

from trading_agent.domain import Order, OrderSide
from trading_agent.execution import PaperBroker


def test_buy_applies_fee_and_slippage() -> None:
    broker = PaperBroker(10_000, fee_rate=0.001, slippage_bps=10)
    fill = broker.submit(
        Order(client_order_id="a", symbol="BTC/USDT", side=OrderSide.BUY, quantity=0.1), 1000
    )
    assert fill.price == pytest.approx(1001)
    assert broker.portfolio().cash == pytest.approx(10_000 - 100.1 - 0.1001)


def test_submit_is_idempotent() -> None:
    broker = PaperBroker(10_000)
    order = Order(client_order_id="same", symbol="BTC/USDT", side=OrderSide.BUY, quantity=0.1)
    broker.submit(order, 1000)
    broker.submit(order, 1000)
    assert len(broker.fills) == 1


def test_insufficient_cash() -> None:
    broker = PaperBroker(100)
    with pytest.raises(ValueError):
        broker.submit(
            Order(client_order_id="x", symbol="BTC/USDT", side=OrderSide.BUY, quantity=1), 1000
        )
