"""Configurazione: segreti da env (.env), parametri di trading da YAML versionati in config/."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


class Secrets(BaseSettings):
    """Chiavi API. Mai committarle: vivono solo in .env o nei secret del runner."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str | None = None
    exchange_id: str = "binance"
    exchange_api_key: str | None = None
    exchange_api_secret: str | None = None
    alpaca_api_key: str | None = None
    alpaca_secret_key: str | None = None
    finnhub_api_key: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None

    trading_mode: Literal["backtest", "paper", "live"] = "paper"


class RiskLimits(BaseModel):
    max_position_pct_equity: float = Field(0.10, ge=0, le=1)
    max_gross_exposure_pct: float = Field(0.50, ge=0, le=3)
    max_risk_per_trade_pct: float = Field(0.01, ge=0, le=0.1)
    max_daily_trades: int = Field(5, ge=0)
    max_drawdown_kill_switch: float = Field(0.15, ge=0, le=1)
    require_stop_loss: bool = True
    allow_short: bool = False
    symbol_whitelist: list[str] = Field(default_factory=list)


class AgentModelConfig(BaseModel):
    model: str
    effort: Literal["low", "medium", "high"] | None = None
    max_tokens: int = 2048
    prompt: str


class AgentsConfig(BaseModel):
    debate_rounds: int = Field(2, ge=0, le=5)
    risk_debate_rounds: int = Field(1, ge=0, le=5)
    agents: dict[str, AgentModelConfig]


class RunConfig(BaseModel):
    symbols: list[str]
    timeframe: str = "4h"
    lookback_bars: int = 300
    initial_equity: float = 10_000.0
    fee_rate: float = 0.001
    slippage_bps: float = 5.0


def _load_yaml(name: str) -> dict[str, object]:
    with (CONFIG_DIR / name).open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{name} deve contenere un mapping YAML")
    return data


def load_risk_limits() -> RiskLimits:
    return RiskLimits.model_validate(_load_yaml("risk_limits.yaml"))


def load_agents_config() -> AgentsConfig:
    return AgentsConfig.model_validate(_load_yaml("agents.yaml"))


def load_run_config() -> RunConfig:
    return RunConfig.model_validate(_load_yaml("run.yaml"))
