"""Astrazione minima sul provider LLM.

Gli agenti chiedono sempre un output strutturato (Pydantic). Così il resto del sistema non
deve mai fare parsing di testo libero, e cambiare provider vuol dire scrivere un solo adapter.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
Effort = Literal["low", "medium", "high"]


class LLMClient(Protocol):
    def structured(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: type[T],
        effort: Effort | None = None,
        max_tokens: int = 2048,
    ) -> T: ...


class AnthropicLLM:
    """Adapter per la Claude API con structured outputs (`messages.parse`)."""

    def __init__(self, api_key: str | None = None) -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)

    def structured(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: type[T],
        effort: Effort | None = None,
        max_tokens: int = 2048,
    ) -> T:
        extra: dict[str, object] = {}
        if effort is not None:
            extra["output_config"] = {"effort": effort}
        # Il prompt di sistema è stabile tra i cicli: cache_control lo rende quasi gratuito.
        response = self._client.messages.parse(
            model=model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_format=schema,
            **extra,  # type: ignore[arg-type]
        )
        parsed = response.parsed_output
        if parsed is None:
            raise RuntimeError(
                f"Il modello {model} non ha restituito un output valido per {schema}"
            )
        return parsed


Responder = Callable[[str, str, type[BaseModel]], BaseModel]


class FakeLLM:
    """LLM finto per test e dry-run: risponde con una funzione deterministica per schema."""

    def __init__(self, responders: dict[type[BaseModel], Responder]) -> None:
        self._responders = responders
        self.calls: list[tuple[str, type[BaseModel]]] = []

    def structured(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: type[T],
        effort: Effort | None = None,
        max_tokens: int = 2048,
    ) -> T:
        self.calls.append((model, schema))
        responder = self._responders.get(schema)
        if responder is None:
            raise KeyError(f"Nessuna risposta finta registrata per {schema.__name__}")
        result = responder(system, user, schema)
        if not isinstance(result, schema):
            raise TypeError(f"Il responder per {schema.__name__} ha restituito {type(result)}")
        return result
