"""Risposte deterministiche per il dry-run: fanno girare l'intero grafo senza API key.

Non è una strategia: serve solo a verificare il wiring end-to-end e a fare da baseline banale.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel

from trading_agent.domain import (
    AnalystReport,
    DebateArgument,
    Direction,
    Rating,
    ResearchThesis,
    RiskCommitteeView,
    TradeDecision,
    TradeProposal,
)
from trading_agent.llm.client import FakeLLM, Responder


def _context(user: str) -> dict[str, Any]:
    _, _, raw = user.partition("## Context (JSON)\n")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Context non valido")
    return data


def _snapshot(ctx: dict[str, Any]) -> dict[str, Any]:
    snap = ctx.get("snapshot") or {}
    return snap if isinstance(snap, dict) else {}


def _score(features: dict[str, float]) -> float:
    """Trend-following elementare: +1 sopra SMA50 con MACD positivo, -1 all'opposto."""
    score = 0.0
    score += 0.5 if features.get("dist_sma_50_pct", 0) > 0 else -0.5
    score += 0.5 if features.get("macd_hist", 0) > 0 else -0.5
    return score


def _analyst(_s: str, user: str, _t: type[BaseModel]) -> BaseModel:
    snap = _snapshot(_context(user))
    score = _score(snap.get("features", {}))
    rating = Rating.BUY if score > 0 else Rating.SELL if score < 0 else Rating.HOLD
    return AnalystReport(
        analyst="rule_based",
        symbol=snap["symbol"],
        as_of=snap["as_of"],
        rating=rating,
        confidence=abs(score),
        key_points=[f"trend score {score:+.1f}"],
        rationale="Dry-run deterministico basato su SMA50 e MACD.",
        data_used=["dist_sma_50_pct", "macd_hist"],
    )


def _debate(_s: str, user: str, _t: type[BaseModel]) -> BaseModel:
    ctx = _context(user)
    side: Literal["bull", "bear"] = "bull" if len(ctx.get("debate", [])) % 2 == 0 else "bear"
    return DebateArgument(
        side=side, round=len(ctx.get("debate", [])) // 2 + 1, claims=["dry-run"], strength=0.5
    )


def _thesis(_s: str, user: str, _t: type[BaseModel]) -> BaseModel:
    snap = _snapshot(_context(user))
    score = _score(snap.get("features", {}))
    direction = Direction.LONG if score > 0 else Direction.FLAT
    return ResearchThesis(
        symbol=snap["symbol"],
        as_of=snap["as_of"],
        direction=direction,
        conviction=abs(score),
        bull_case="trend up",
        bear_case="trend down",
        verdict_rationale="dry-run",
        debate_rounds=0,
    )


def _proposal(_s: str, user: str, _t: type[BaseModel]) -> BaseModel:
    ctx = _context(user)
    snap = _snapshot(ctx)
    thesis = ctx["thesis"]
    price = float(snap["last_price"])
    atr = float(snap.get("features", {}).get("atr_14", price * 0.02))
    direction = Direction(thesis["direction"])
    return TradeProposal(
        symbol=snap["symbol"],
        as_of=snap["as_of"],
        direction=direction,
        entry_price=price,
        stop_loss=price - 2 * atr if direction is Direction.LONG else None,
        take_profit=price + 4 * atr if direction is Direction.LONG else None,
        size_pct_equity=0.2 if direction is Direction.LONG else 0.0,
        rationale="dry-run: stop a 2 ATR, target a 4 ATR",
    )


def _committee(_s: str, _u: str, _t: type[BaseModel]) -> BaseModel:
    return RiskCommitteeView(size_multiplier=1.0, rationale="dry-run")


def _decision(_s: str, user: str, _t: type[BaseModel]) -> BaseModel:
    ctx = _context(user)
    proposal, verdict = ctx["proposal"], ctx["risk_verdict"]
    approved = bool(verdict["approved"])
    return TradeDecision(
        symbol=proposal["symbol"],
        as_of=proposal.get("as_of", datetime.now(UTC).isoformat()),
        action="execute" if approved else "reject",
        direction=Direction(proposal["direction"]),
        size_pct_equity=float(verdict["approved_size_pct_equity"]) if approved else 0.0,
        stop_loss=proposal.get("stop_loss"),
        take_profit=proposal.get("take_profit"),
        rationale="dry-run",
    )


def rule_based_llm() -> FakeLLM:
    responders: dict[type[BaseModel], Responder] = {
        AnalystReport: _analyst,
        DebateArgument: _debate,
        ResearchThesis: _thesis,
        TradeProposal: _proposal,
        RiskCommitteeView: _committee,
        TradeDecision: _decision,
    }
    return FakeLLM(responders)
