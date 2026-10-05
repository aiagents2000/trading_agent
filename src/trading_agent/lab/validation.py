"""Strategy Lab: validazione onesta delle strategie candidate.

Ogni backtest provato finisce nel TrialLedger, anche quelli scartati: il Deflated Sharpe Ratio
va calcolato sul numero REALE di tentativi, altrimenti il data-snooping passa inosservato.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np

EULER_GAMMA = 0.5772156649015329
_N = NormalDist()


def sharpe_ratio(returns: np.ndarray, periods_per_year: int = 365) -> float:
    returns = np.asarray(returns, dtype=float)
    if returns.size < 2 or returns.std(ddof=1) == 0:
        return 0.0
    return float(returns.mean() / returns.std(ddof=1) * math.sqrt(periods_per_year))


def expected_max_sharpe(n_trials: int, sharpe_variance: float) -> float:
    """Sharpe massimo atteso per puro caso su n_trials (Bailey & López de Prado, 2014)."""
    if n_trials < 2:
        return 0.0
    a = _N.inv_cdf(1 - 1 / n_trials)
    b = _N.inv_cdf(1 - 1 / (n_trials * math.e))
    return math.sqrt(sharpe_variance) * ((1 - EULER_GAMMA) * a + EULER_GAMMA * b)


def deflated_sharpe_ratio(returns: np.ndarray, n_trials: int, sharpe_variance: float) -> float:
    """Probabilità che lo Sharpe (per periodo, non annualizzato) sia reale dati n_trials."""
    r = np.asarray(returns, dtype=float)
    t = r.size
    if t < 3 or r.std(ddof=1) == 0:
        return 0.0
    sr = r.mean() / r.std(ddof=1)
    centered = r - r.mean()
    std = r.std(ddof=0)
    skew = float((centered**3).mean() / std**3)
    kurt = float((centered**4).mean() / std**4)
    sr0 = expected_max_sharpe(n_trials, sharpe_variance)
    denom = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4 * sr**2))
    return _N.cdf((sr - sr0) * math.sqrt(t - 1) / denom)


class TrialLedger:
    """Registro append-only di ogni strategia/parametrizzazione testata."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, strategy_id: str, params: dict[str, Any], metrics: dict[str, float]) -> None:
        row = {
            "at": datetime.now(UTC).isoformat(),
            "strategy_id": strategy_id,
            "params": params,
            "metrics": metrics,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")

    def n_trials(self) -> int:
        if not self.path.exists():
            return 0
        with self.path.open(encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())
