"""Contratti tipizzati scambiati tra gli agenti.

Ogni agente legge e scrive solo questi oggetti: niente testo libero che passa di mano in mano
(evita il "telephone effect"). Le opinioni in linguaggio naturale restano nei campi `rationale`.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Rating(StrEnum):
    STRONG_SELL = "strong_sell"
    SELL = "sell"
    HOLD = "hold"
    BUY = "buy"
    STRONG_BUY = "strong_buy"


class Direction(StrEnum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class MarketSnapshot(BaseModel):
    """Tutto ciò che un agente può vedere in un ciclo. `as_of` è il confine point-in-time."""

    symbol: str
    timeframe: str
    as_of: datetime
    last_price: float = Field(gt=0)
    features: dict[str, float] = Field(default_factory=dict)
    news: list[str] = Field(default_factory=list)


class AnalystReport(BaseModel):
    analyst: str
    symbol: str
    as_of: datetime
    rating: Rating
    confidence: float = Field(ge=0, le=1)
    key_points: list[str] = Field(max_length=6)
    rationale: str
    data_used: list[str] = Field(
        default_factory=list, description="Fonti/feature usate: serve per l'audit di leakage."
    )


class ResearchThesis(BaseModel):
    symbol: str
    as_of: datetime
    direction: Direction
    conviction: float = Field(ge=0, le=1)
    bull_case: str
    bear_case: str
    verdict_rationale: str
    debate_rounds: int = Field(ge=0)


class DebateArgument(BaseModel):
    side: Literal["bull", "bear"]
    round: int = Field(ge=1)
    claims: list[str] = Field(max_length=5)
    rebuttals: list[str] = Field(default_factory=list, max_length=5)
    strength: float = Field(
        ge=0, le=1, description="Quanto l'agente ritiene forte la propria tesi."
    )


class RiskCommitteeView(BaseModel):
    """Opinione qualitativa: può solo ridurre la size (multiplier <= 1)."""

    size_multiplier: float = Field(ge=0, le=1)
    concerns: list[str] = Field(default_factory=list, max_length=6)
    rationale: str


class ReflectionNote(BaseModel):
    symbol: str
    written_at: datetime
    decision_as_of: datetime
    outcome_pnl_pct: float
    what_worked: list[str] = Field(max_length=4)
    what_failed: list[str] = Field(max_length=4)
    lesson: str = Field(description="Una regola operativa riutilizzabile, max 2 frasi.")


class TradeProposal(BaseModel):
    symbol: str
    as_of: datetime
    direction: Direction
    entry_price: float = Field(gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit: float | None = Field(default=None, gt=0)
    size_pct_equity: float = Field(ge=0, le=1, description="Size richiesta in % dell'equity.")
    horizon: Literal["intraday", "swing", "position"] = "swing"
    rationale: str

    @model_validator(mode="after")
    def _stop_on_the_right_side(self) -> TradeProposal:
        if self.stop_loss is None or self.direction is Direction.FLAT:
            return self
        if self.direction is Direction.LONG and self.stop_loss >= self.entry_price:
            raise ValueError("Per un long lo stop deve stare sotto il prezzo d'ingresso")
        if self.direction is Direction.SHORT and self.stop_loss <= self.entry_price:
            raise ValueError("Per uno short lo stop deve stare sopra il prezzo d'ingresso")
        return self


class RiskVerdict(BaseModel):
    approved: bool
    approved_size_pct_equity: float = Field(ge=0, le=1)
    violations: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class TradeDecision(BaseModel):
    symbol: str
    as_of: datetime
    action: Literal["execute", "reject", "hold"]
    direction: Direction
    size_pct_equity: float = Field(ge=0, le=1)
    stop_loss: float | None = None
    take_profit: float | None = None
    rationale: str


class Order(BaseModel):
    client_order_id: str
    symbol: str
    side: OrderSide
    quantity: float = Field(gt=0)
    order_type: Literal["market", "limit"] = "market"
    limit_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None


class Fill(BaseModel):
    client_order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    fee: float
    filled_at: datetime


class Position(BaseModel):
    symbol: str
    quantity: float
    avg_price: float

    @property
    def direction(self) -> Direction:
        if self.quantity > 0:
            return Direction.LONG
        if self.quantity < 0:
            return Direction.SHORT
        return Direction.FLAT


class PortfolioState(BaseModel):
    cash: float
    equity: float
    peak_equity: float
    positions: dict[str, Position] = Field(default_factory=dict)
    trades_today: int = 0

    @property
    def drawdown(self) -> float:
        if self.peak_equity <= 0:
            return 0.0
        return max(0.0, 1 - self.equity / self.peak_equity)
