from datetime import UTC, datetime

import pytest

from trading_agent.config import RiskLimits
from trading_agent.domain import Direction, PortfolioState, TradeProposal
from trading_agent.risk import RiskEngine

NOW = datetime(2026, 10, 5, tzinfo=UTC)


def proposal(**kw: object) -> TradeProposal:
    base = dict(
        symbol="BTC/USDT",
        as_of=NOW,
        direction=Direction.LONG,
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        size_pct_equity=0.5,
        rationale="test",
    )
    base.update(kw)
    return TradeProposal.model_validate(base)


def portfolio(equity: float = 10_000, peak: float = 10_000) -> PortfolioState:
    return PortfolioState(cash=equity, equity=equity, peak_equity=peak)


@pytest.fixture
def engine() -> RiskEngine:
    return RiskEngine(RiskLimits(symbol_whitelist=["BTC/USDT"]))


def test_size_is_capped_by_risk_per_trade(engine: RiskEngine) -> None:
    # stop al 5% e rischio max 1% -> size max 20%, poi cap posizione al 10%
    verdict = engine.evaluate(proposal(), portfolio())
    assert verdict.approved
    assert verdict.approved_size_pct_equity == pytest.approx(0.10)


def test_missing_stop_is_rejected(engine: RiskEngine) -> None:
    verdict = engine.evaluate(proposal(stop_loss=None), portfolio())
    assert not verdict.approved
    assert any("Stop" in v for v in verdict.violations)


def test_kill_switch_blocks_new_trades(engine: RiskEngine) -> None:
    verdict = engine.evaluate(proposal(), portfolio(equity=8_000, peak=10_000))
    assert not verdict.approved


def test_symbol_outside_whitelist(engine: RiskEngine) -> None:
    verdict = engine.evaluate(proposal(symbol="DOGE/USDT"), portfolio())
    assert not verdict.approved


def test_short_disabled_by_default(engine: RiskEngine) -> None:
    verdict = engine.evaluate(
        proposal(direction=Direction.SHORT, stop_loss=105.0, take_profit=90.0), portfolio()
    )
    assert not verdict.approved


def test_stop_on_wrong_side_fails_validation() -> None:
    with pytest.raises(ValueError):
        proposal(stop_loss=101.0)
