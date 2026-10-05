# Istruzioni per Claude Code su questa repo

Progetto: team di agenti LLM per paper trading e validazione strategie. Leggi prima
`docs/01_ROLES.md` e `docs/03_IMPLEMENTATION_PLAN.md`.

## Vincoli
- Mai introdurre trading live, chiavi live o endpoint di produzione di exchange/broker.
- Non modificare `config/risk_limits.yaml` né `src/trading_agent/risk/` senza che l'utente lo chieda
  esplicitamente nel messaggio corrente.
- Ogni contratto tra agenti è un modello Pydantic in `src/trading_agent/domain/models.py`.
- Ogni nuova feature di mercato va in `data/features.py` con un test di non-lookahead.

## Comandi
- Test: `pytest`
- Lint/format: `ruff check src tests && ruff format src tests`
- Tipi: `mypy`
- Smoke test: `trading-agent cycle --dry-run --offline`

## Stile
- Python 3.12, type hints completi, funzioni piccole.
- Commenti e docs in italiano, identificatori e prompt in inglese.
- Conventional Commits.
