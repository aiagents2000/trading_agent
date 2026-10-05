"""Journal append-only (JSONL) di decisioni e lezioni.

La memoria è time-aware: una lezione è visibile solo ai cicli con `as_of` successivo alla sua
scrittura. Senza questo vincolo un backtest "ricorda il futuro" (Oracle Fallacy).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_agent.domain import ReflectionNote


class TradeJournal:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, kind: str, payload: dict[str, Any]) -> None:
        record = {"kind": kind, **payload}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str, ensure_ascii=False) + "\n")

    def records(self, kind: str | None = None) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out = []
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rec = json.loads(line)
                    if kind is None or rec.get("kind") == kind:
                        out.append(rec)
        return out

    def add_lesson(self, note: ReflectionNote) -> None:
        self.append("lesson", note.model_dump(mode="json"))

    def lessons_before(
        self, as_of: datetime, symbol: str | None = None, limit: int = 5
    ) -> list[str]:
        visible = []
        for rec in self.records("lesson"):
            written = datetime.fromisoformat(rec["written_at"])
            if written < as_of and (symbol is None or rec.get("symbol") == symbol):
                visible.append((written, rec["lesson"]))
        visible.sort(key=lambda x: x[0], reverse=True)
        return [lesson for _, lesson in visible[:limit]]
