# Come lavoriamo

Siamo in due. Tutto passa da questa repo: niente codice, prompt o config modificati fuori da git.

## Flusso

1. **Issue prima del codice.** Ogni task del [piano](docs/03_IMPLEMENTATION_PLAN.md) diventa un'issue
   con l'ID della fase (es. `F1.3`). Assegnatela prima di iniziare per non lavorare in doppio.
2. **Branch corti** da `main`: `feat/f1-3-news-ingest`, `fix/risk-gross-exposure`, `prompt/trader-v2`.
3. **Pull request piccole** (idealmente < 400 righe) con il template compilato.
4. **Review obbligatoria dell'altro** prima del merge. Squash merge su `main`.
5. `main` deve essere sempre verde: CI (ruff, mypy, pytest, smoke test dry-run) blocca il merge.

Consigliato: in GitHub → Settings → Branches, proteggere `main` con "Require a pull request" e
"Require status checks to pass".

## Regole che non si negoziano

- **Solo paper.** Nessuna PR introduce chiavi o endpoint live. `TRADING_MODE=live` resta bloccato.
- **Il rischio è codice.** I limiti stanno in `config/risk_limits.yaml` e li applica
  `risk/engine.py`. Un LLM non può mai aumentare una size, solo ridurla.
- **Point-in-time sempre.** Ogni dato che arriva a un agente ha un timestamp `<= as_of`. Ogni nuova
  feature ha un test di non-lookahead (vedi `tests/test_features_no_lookahead.py`).
- **Ogni tentativo si registra.** Ogni backtest del Strategy Lab finisce nel trial ledger, anche se
  va male: serve per il Deflated Sharpe.
- **Prompt = codice.** I prompt in `prompts/` si cambiano via PR, con motivazione. Un prompt cambiato
  azzera il track record di quel ruolo nel confronto A/B.
- **Segreti solo in `.env`** o nei secret del runner. Pre-commit con gitleaks attivo.

## Setup locale

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
pre-commit install
pytest && trading-agent cycle --dry-run --offline
```

## Convenzioni

- Python 3.12, type hints ovunque (`mypy --strict`), Pydantic per tutti i contratti tra agenti.
- Codice e identificatori in inglese, commenti e documentazione in italiano, prompt in inglese.
- Commit in stile Conventional Commits: `feat:`, `fix:`, `docs:`, `prompt:`, `risk:`, `test:`.
- Decisioni architetturali → nuovo file in `docs/adr/` (template nel primo ADR).
