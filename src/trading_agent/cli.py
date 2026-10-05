"""Entry point: `trading-agent cycle` esegue un ciclo decisionale per ogni simbolo configurato."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

from trading_agent.agents import TradingTeam
from trading_agent.config import (
    Secrets,
    load_agents_config,
    load_risk_limits,
    load_run_config,
)
from trading_agent.data import CcxtMarketData, build_snapshot
from trading_agent.execution import LiveTradingDisabledError, PaperBroker
from trading_agent.llm import AnthropicLLM, LLMClient
from trading_agent.llm.rule_based import rule_based_llm
from trading_agent.memory import TradeJournal
from trading_agent.orchestration import CycleDeps, run_cycle
from trading_agent.risk import RiskEngine


def synthetic_ohlcv(bars: int = 300, seed: int = 7) -> pd.DataFrame:
    """Random walk per test offline e CI (nessuna rete)."""
    rng = np.random.default_rng(seed)
    close = 30_000 * np.exp(np.cumsum(rng.normal(0.0005, 0.01, bars)))
    idx = pd.date_range("2026-01-01", periods=bars, freq="4h", tz="UTC")
    return pd.DataFrame(
        {
            "open": close * (1 - rng.normal(0, 0.002, bars)),
            "high": close * (1 + abs(rng.normal(0, 0.005, bars))),
            "low": close * (1 - abs(rng.normal(0, 0.005, bars))),
            "close": close,
            "volume": rng.uniform(100, 1000, bars),
        },
        index=idx,
    )


def cmd_cycle(args: argparse.Namespace) -> int:
    secrets = Secrets()
    if secrets.trading_mode == "live":
        raise LiveTradingDisabledError("TRADING_MODE=live non è supportato in questa fase.")

    run_cfg = load_run_config()
    llm: LLMClient
    if args.dry_run:
        llm = rule_based_llm()
        logger.info("Dry-run: agenti sostituiti da risposte deterministiche, nessuna API call")
    else:
        llm = AnthropicLLM(api_key=secrets.anthropic_api_key)

    deps = CycleDeps(
        team=TradingTeam.from_config(load_agents_config(), llm),
        risk=RiskEngine(load_risk_limits()),
        broker=PaperBroker(run_cfg.initial_equity, run_cfg.fee_rate, run_cfg.slippage_bps),
        journal=TradeJournal(Path(args.journal)),
    )
    market = None if args.offline else CcxtMarketData(secrets.exchange_id)
    symbols = [args.symbol] if args.symbol else run_cfg.symbols

    for symbol in symbols:
        ohlcv = (
            synthetic_ohlcv(run_cfg.lookback_bars)
            if market is None
            else market.fetch_ohlcv(symbol, run_cfg.timeframe, run_cfg.lookback_bars)
        )
        snapshot = build_snapshot(symbol, run_cfg.timeframe, ohlcv)
        state = run_cycle(deps, snapshot)
        decision = state.get("decision")
        logger.info(
            "{} @ {:.2f} -> {} | fill={}",
            symbol,
            snapshot.last_price,
            decision.action if decision else (state.get("halted_reason") or "flat"),
            state.get("fill"),
        )
    logger.info("Equity paper: {:.2f}", deps.broker.portfolio().equity)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trading-agent")
    sub = parser.add_subparsers(dest="command", required=True)
    cycle = sub.add_parser("cycle", help="Esegue un ciclo decisionale (paper)")
    cycle.add_argument("--symbol", help="Override del simbolo (formato ccxt, es. BTC/USDT)")
    cycle.add_argument(
        "--dry-run", action="store_true", help="Niente LLM: risposte deterministiche"
    )
    cycle.add_argument("--offline", action="store_true", help="Dati sintetici, nessuna rete")
    cycle.add_argument("--journal", default="data/journal.jsonl")
    cycle.set_defaults(func=cmd_cycle)
    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
