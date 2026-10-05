"""Risk Engine deterministico: l'ultima parola prima dell'esecuzione è codice, non un LLM.

Regola d'oro: gli agenti possono solo RIDURRE il rischio rispetto a questi limiti, mai aumentarlo.
"""

from __future__ import annotations

from trading_agent.config import RiskLimits
from trading_agent.domain import Direction, PortfolioState, RiskVerdict, TradeProposal


class RiskEngine:
    def __init__(self, limits: RiskLimits) -> None:
        self.limits = limits

    def kill_switch_active(self, portfolio: PortfolioState) -> bool:
        return portfolio.drawdown >= self.limits.max_drawdown_kill_switch

    def evaluate(self, proposal: TradeProposal, portfolio: PortfolioState) -> RiskVerdict:
        limits = self.limits
        violations: list[str] = []
        notes: list[str] = []

        if proposal.direction is Direction.FLAT:
            return RiskVerdict(approved=True, approved_size_pct_equity=0.0, notes=["Nessun trade"])

        if self.kill_switch_active(portfolio):
            violations.append(
                f"Kill switch: drawdown {portfolio.drawdown:.1%} >= "
                f"{limits.max_drawdown_kill_switch:.1%}"
            )
        if limits.symbol_whitelist and proposal.symbol not in limits.symbol_whitelist:
            violations.append(f"{proposal.symbol} non è in whitelist")
        if proposal.direction is Direction.SHORT and not limits.allow_short:
            violations.append("Short non consentiti")
        if limits.require_stop_loss and proposal.stop_loss is None:
            violations.append("Stop loss obbligatorio")
        if portfolio.trades_today >= limits.max_daily_trades:
            violations.append(f"Raggiunto il limite di {limits.max_daily_trades} trade giornalieri")

        if violations:
            return RiskVerdict(approved=False, approved_size_pct_equity=0.0, violations=violations)

        size = proposal.size_pct_equity
        caps: list[tuple[str, float]] = [
            ("max_position_pct_equity", limits.max_position_pct_equity)
        ]

        gross_now = sum(abs(p.quantity) * p.avg_price for p in portfolio.positions.values()) / max(
            portfolio.equity, 1e-9
        )
        caps.append(("gross_exposure_residua", max(0.0, limits.max_gross_exposure_pct - gross_now)))

        if proposal.stop_loss is not None:
            stop_distance = abs(proposal.entry_price - proposal.stop_loss) / proposal.entry_price
            if stop_distance > 0:
                caps.append(("risk_per_trade", limits.max_risk_per_trade_pct / stop_distance))

        for name, cap in caps:
            if size > cap:
                notes.append(f"Size ridotta da {size:.2%} a {cap:.2%} ({name})")
                size = cap

        size = max(0.0, min(size, 1.0))
        if size == 0:
            return RiskVerdict(
                approved=False,
                approved_size_pct_equity=0.0,
                violations=["Nessuna capacità di rischio residua"],
                notes=notes,
            )
        return RiskVerdict(approved=True, approved_size_pct_equity=size, notes=notes)
