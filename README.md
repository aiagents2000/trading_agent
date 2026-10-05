# trading_agent

Un team di agenti LLM che simula una trading desk: analisti, ricercatori bull/bear, trader,
comitato rischio e portfolio manager prendono decisioni insieme, mentre un **risk engine
deterministico** e un **paper broker** tengono tutto sotto controllo. Serve a due cose:

1. **Testare** il processo decisionale multi-agente in paper trading, in forward e senza rischio.
2. **Validare nuove strategie** con una pipeline anti-overfitting (trial ledger, Deflated Sharpe).

> ⚠️ Progetto di ricerca. Solo paper trading. `TRADING_MODE=live` è bloccato nel codice.
> Niente di questo repo è consulenza finanziaria.

## Documentazione

| Documento | Contenuto |
|---|---|
| [docs/01_ROLES.md](docs/01_ROLES.md) | Ruoli degli agenti, suddivisione consigliata, flusso decisionale |
| [docs/02_TOOLS.md](docs/02_TOOLS.md) | Strumenti e servizi da collegare per automatizzare tutto |
| [docs/03_IMPLEMENTATION_PLAN.md](docs/03_IMPLEMENTATION_PLAN.md) | Piano di implementazione a fasi, con criteri di uscita |
| [docs/adr/](docs/adr/) | Decisioni architetturali registrate |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Come lavoriamo in due su questa repo |

## Quickstart

```bash
uv sync                      # crea .venv con dipendenze + gruppo dev
source .venv/bin/activate
pytest

# Ciclo completo senza API key né rete (dati sintetici, agenti deterministici)
trading-agent cycle --dry-run --offline

# Dati reali da exchange (pubblici, nessuna chiave), agenti deterministici
trading-agent cycle --dry-run --symbol BTC/USDT

# Agenti LLM veri (richiede ANTHROPIC_API_KEY in .env)
cp .env.example .env
trading-agent cycle --symbol BTC/USDT
```

## Architettura in breve

```
dati (ccxt / API) ─► feature registry (deterministico, point-in-time)
                          │
          ┌───────────────┴──────────────┐
          ▼                              ▼
   Analyst team (4)               Strategy Lab (offline)
          │                       candidate → backtest → ledger → DSR
          ▼
   Bull ⇄ Bear debate ─► Research Manager ─► Trader
                                               │
                         Risk Engine (codice) ◄┘   ← limiti hard da config/risk_limits.yaml
                                │
                         Risk Committee (LLM, può solo ridurre)
                                │
                         Portfolio Manager ─► Execution (paper broker) ─► Journal ─► Reflection
```

## Struttura

```
config/            limiti di rischio, ruoli→modelli, parametri di run (versionati)
prompts/           un prompt per ruolo (versionato, review via PR)
src/trading_agent/
  domain/          contratti Pydantic scambiati tra agenti
  agents/          ruoli e compiti del desk
  llm/             adapter Claude API + LLM finto per test/dry-run
  data/            market data (ccxt) e feature registry
  risk/            risk engine deterministico
  execution/       broker paper e interfaccia per exchange/broker demo
  orchestration/   grafo LangGraph del ciclo decisionale
  memory/          journal JSONL e lezioni time-aware
  lab/             validazione strategie (trial ledger, Deflated Sharpe)
tests/
```
