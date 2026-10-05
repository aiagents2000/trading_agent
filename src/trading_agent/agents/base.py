"""Base comune: un agente = ruolo + modello + prompt versionato + schema di output."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from trading_agent.config import CONFIG_DIR, AgentModelConfig
from trading_agent.llm import LLMClient

T = TypeVar("T", bound=BaseModel)
REPO_ROOT = CONFIG_DIR.parent


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    return value


@dataclass
class Agent:
    role: str
    config: AgentModelConfig
    llm: LLMClient

    @property
    def system_prompt(self) -> str:
        return (REPO_ROOT / Path(self.config.prompt)).read_text(encoding="utf-8")

    def ask(self, schema: type[T], task: str, context: dict[str, Any]) -> T:
        user = (
            f"## Task\n{task}\n\n## Context (JSON)\n"
            f"{json.dumps(_to_jsonable(context), ensure_ascii=False, indent=2, default=str)}"
        )
        return self.llm.structured(
            model=self.config.model,
            system=self.system_prompt,
            user=user,
            schema=schema,
            effort=self.config.effort,
            max_tokens=self.config.max_tokens,
        )
