from datetime import UTC, datetime, timedelta
from pathlib import Path

from trading_agent.agents import TradingTeam
from trading_agent.cli import main, synthetic_ohlcv
from trading_agent.config import load_agents_config, load_risk_limits
from trading_agent.data import build_snapshot
from trading_agent.domain import ReflectionNote
from trading_agent.execution import PaperBroker
from trading_agent.llm.rule_based import rule_based_llm
from trading_agent.memory import TradeJournal
from trading_agent.orchestration import CycleDeps, run_cycle
from trading_agent.risk import RiskEngine


def make_deps(tmp_path: Path) -> CycleDeps:
    return CycleDeps(
        team=TradingTeam.from_config(load_agents_config(), rule_based_llm()),
        risk=RiskEngine(load_risk_limits()),
        broker=PaperBroker(10_000),
        journal=TradeJournal(tmp_path / "journal.jsonl"),
    )


def test_full_cycle_runs_and_respects_limits(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    snapshot = build_snapshot("BTC/USDT", "4h", synthetic_ohlcv(300))
    state = run_cycle(deps, snapshot)

    assert "thesis" in state
    decision = state.get("decision")
    if decision is not None:
        assert decision.size_pct_equity <= load_risk_limits().max_position_pct_equity + 1e-9
    assert deps.journal.records("cycle"), "Ogni ciclo deve finire nel journal"


def test_lessons_are_point_in_time(tmp_path: Path) -> None:
    journal = TradeJournal(tmp_path / "j.jsonl")
    t0 = datetime(2026, 10, 1, tzinfo=UTC)
    journal.add_lesson(
        ReflectionNote(
            symbol="BTC/USDT",
            written_at=t0,
            decision_as_of=t0 - timedelta(days=3),
            outcome_pnl_pct=-0.02,
            what_worked=[],
            what_failed=["entrato su breakout senza volume"],
            lesson="Niente breakout con volume z-score negativo.",
        )
    )
    assert journal.lessons_before(t0 - timedelta(hours=1)) == []
    assert len(journal.lessons_before(t0 + timedelta(hours=1))) == 1


def test_cli_offline_dry_run(tmp_path: Path) -> None:
    assert main(["cycle", "--dry-run", "--offline", "--journal", str(tmp_path / "j.jsonl")]) == 0
