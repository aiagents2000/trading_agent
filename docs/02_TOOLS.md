# 02 · Strumenti da collegare per automatizzare tutto

_Ultimo aggiornamento: 5 ottobre 2026. Prezzi e free tier cambiano spesso: ricontrollare prima di
attivare un servizio a pagamento._

## Stack minimo per partire (Fase 1, costo ≈ solo token LLM)

| Esigenza | Scelta | Costo | Chiave serve? |
|---|---|---|---|
| LLM | Claude API: Sonnet 5.5 (tier rapido) + Opus 5.5 (tier profondo) | a consumo | sì |
| Orchestrazione | LangGraph | gratis (OSS) | no |
| Dati crypto | ccxt, endpoint pubblici dell'exchange | gratis | no |
| Esecuzione | `PaperBroker` interno (fee + slippage) | gratis | no |
| Memoria / log | JSONL in `data/` | gratis | no |
| CI | GitHub Actions | gratis | no |

Con questo il ciclo gira end-to-end. Tutto il resto si aggiunge per fasi (vedi piano).

## 1. Modelli LLM

| Modello | API ID | Prezzo (input / output per MTok) | Ruoli |
|---|---|---|---|
| Claude Opus 5.5 | `claude-opus-5-5` | $4 / $20 | Research Manager, Trader, Portfolio Manager, Reflection, Strategy Researcher |
| Claude Sonnet 5.5 | `claude-sonnet-5-5` | $2 / $10 | 4 analisti, Bull, Bear, Risk Committee |
| Claude Fable 5.1 | `claude-fable-5-1` | $10 / $50 | Solo per esperimenti "Config C" sul PM, se le eval lo giustificano |

Come usarli:
- **Structured outputs** (`client.messages.parse(..., output_format=Model)`): output già validato
  contro lo schema Pydantic. È ciò che usa `llm/client.py`.
- **Effort** (`output_config={"effort": "low" | "medium" | "high"}`): leva principale costo/qualità
  per ruolo, già configurabile in `config/agents.yaml`.
- **Prompt caching**: i prompt di sistema sono stabili tra i cicli, quindi vengono marcati come
  cacheable; le letture da cache costano una frazione dell'input.
- **Batch API** (-50%): per il Strategy Lab e le reflection, che non hanno fretta.
- **Evitare Claude Haiku 4.5** per un sistema nuovo: il ritiro è previsto non prima del 15 ottobre
  2026, cioè potenzialmente a giorni.

Il codice resta provider-agnostic: un nuovo provider = un nuovo adapter che implementa `LLMClient`.

## 2. Orchestrazione degli agenti

| Opzione | Pro | Contro | Verdetto |
|---|---|---|---|
| **LangGraph** | Grafo esplicito con edge condizionali, checkpoint su SQLite/Postgres, replay, multi-provider, human-in-the-loop | Più boilerplate | **Scelto** per il ciclo di trading (già nello scaffolding) |
| Claude Agent SDK | Loop agentico pronto con tool (bash, file, web), sessioni | Solo modelli Claude, flusso deciso dal modello | Buono per il **Strategy Researcher** nel Lab, dove serve esplorazione autonoma |
| CrewAI / AG2 | Ruoli "a squadra" rapidi da prototipare | Meno controllo sul flusso e sullo stato | Non necessario |
| Fork di TradingAgents | Ruoli già implementati | Pensato per equity US, nessuno slippage/fee/latency, difficile da adattare a regole di rischio hard | Usarlo come **riferimento**, non come base |

## 3. Esecuzione in paper (broker / exchange)

Tutto passa dall'interfaccia `Broker` in `execution/broker.py`, quindi si cambia sede senza toccare
gli agenti.

| Sede | Mercati | Modalità test | Note | Fase |
|---|---|---|---|---|
| **PaperBroker interno** | qualunque (prezzi da ccxt/API) | simulazione locale | Fee e slippage configurabili, idempotente, zero dipendenze | 1 |
| **Binance Spot Demo Mode** | crypto spot | `demo-api.binance.com`, chiavi da demo.binance.com | Dati "realistici" e limiti identici al live; saldo resettabile da UI. Diverso dallo Spot Testnet (dati indipendenti, reset mensile) | 2 |
| **Kraken CLI** | crypto spot, perpetual, stock tokenizzati, forex | motore paper integrato (spot e futures, con fee/slippage e liquidazioni simulate) | Binario unico, output JSON, **server MCP integrato**. Comodo se si vuole restare su Kraken | 2 |
| **Alpaca Paper** | azioni/ETF USA, crypto, opzioni | conto paper di default | SDK `alpaca-py` + **MCP server ufficiale v2** (ordini, dati, news). Da verificare l'apertura del conto paper per residenti UE in fase di signup | 2 |
| Kraken Futures Demo | futures crypto | ambiente demo separato | Solo se si vogliono testare derivati | 3+ |

Regola: le chiavi in `.env` devono essere **solo** di ambienti demo/paper. Il codice blocca
`TRADING_MODE=live`.

## 4. Dati di mercato

| Fonte | Copertura | Free tier | Uso nel progetto |
|---|---|---|---|
| **ccxt** (pubblico) | OHLCV, order book, funding, open interest di 100+ exchange | gratis | Feed principale crypto (già integrato) |
| **Alpaca Market Data** | azioni USA, crypto, opzioni, news | incluso col conto | Feed equity in Fase 2 |
| **Finnhub** | quote, news con sentiment, insider, calendari | 60 chiamate/min | News e sentiment equity |
| **Financial Modeling Prep** | bilanci, ratio, filing SEC | 250 chiamate/giorno | Fundamental Analyst (equity) |
| **FRED** (Fed St. Louis) | tassi, inflazione, dollaro, spread | gratis | Macro Analyst |
| **CoinGecko** | market cap, dominance, supply | free tier | Macro/regime crypto |
| Massive (ex Polygon.io) | tick e intraday USA a bassa latenza | delayed gratis, da $29/mese | Solo se si va su timeframe intraday |
| EODHD | 60+ borse mondiali, server MCP | 20 chiamate/giorno | Se servono mercati non USA |
| Alpha Vantage | 50+ indicatori tecnici | 25 chiamate/giorno | Sconsigliato: gli indicatori li calcoliamo noi, il limite è troppo basso |

## 5. News e sentiment

| Fonte | Note |
|---|---|
| Finnhub news | Con sentiment score; buona per equity |
| Alpaca news | Inclusa nel conto, via API e MCP |
| CryptoPanic | Aggregatore crypto con voti della community; verificare piano e limiti attuali dell'API |
| Feed RSS (CoinDesk, The Block, Reuters markets) | Gratis, da normalizzare e timestampare noi |

Requisito comune: ogni notizia entra nel sistema con **timestamp di pubblicazione** e viene mostrata
agli agenti solo se `published_at <= as_of`. È il punto in cui i backtest LLM perdono più spesso
la correttezza.

## 6. Backtest e validazione

| Strumento | Ruolo | Note |
|---|---|---|
| `lab/validation.py` (nostro) | Trial ledger, Sharpe, Deflated Sharpe | Già nello scaffolding |
| **vectorbt** (OSS) | Sweep veloci di parametri sulle strategie rule-based | La versione OSS è in manutenzione; le novità sono in PRO (a pagamento) |
| backtesting.py | Backtest semplici, curva di apprendimento minima | Alternativa leggera |
| **NautilusTrader** | Motore event-driven con parità backtest↔paper↔live | Fase 4, se si vuole portare una strategia validata su un motore di produzione |
| Backtrader | — | Non più sviluppato dal 2023: da evitare |

Nessun framework fornisce da solo walk-forward, Monte Carlo e PBO: li costruiamo nel Lab.

## 7. Stato, storage e memoria

| Fase | Scelta | Perché |
|---|---|---|
| 1 | JSONL in `data/` | Zero setup, leggibile, diffabile |
| 2 | SQLite o DuckDB + checkpointer LangGraph su SQLite | Query su journal e metriche, ripresa dei cicli |
| 3 | **Postgres su Supabase** | Stato condiviso tra i due collaboratori e il runner; base per la dashboard |

## 8. Osservabilità

| Strumento | Uso |
|---|---|
| **Langfuse** (open source, cloud o self-hosted) | Trace di ogni ciclo: prompt, output, token e costo **per ruolo**, latenza. Indispensabile per capire quale agente vale il suo costo |
| loguru | Log applicativi (già in uso) |
| Sentry (opzionale) | Errori del runner schedulato |

## 9. Scheduling e runtime

| Opzione | Pro | Contro | Fase |
|---|---|---|---|
| **GitHub Actions `schedule`** | Gratis, già dove sta il codice, secret gestiti | Runner stateless (lo stato deve stare fuori, es. Supabase), orari non garantiti al minuto | 2 |
| **VPS piccola + Docker + systemd timer** (es. Hetzner, ~5 €/mese) | Stato locale, controllo completo, websocket possibili | Da mantenere | 3 |
| Scheduled task di Claude | Comodo per report e reflection periodiche | Non adatto come motore del ciclo di trading | opzionale |

Un ciclo ogni 4h su barre chiuse non richiede infrastruttura a bassa latenza.

## 10. Notifiche e dashboard

- **Telegram bot**: messaggio per ogni decisione `execute`, kill switch, errori del runner, riepilogo
  giornaliero. Gratis, 10 minuti di setup con @BotFather.
- **Dashboard**: Streamlit (rapido, Python) oppure una pagina Next.js su Vercel che legge da Supabase.
  Metriche: equity curve per config, drawdown, numero trade, hit rate, costo LLM per trade.

## 11. Collaborazione e qualità

| Strumento | Uso |
|---|---|
| GitHub (Issues, Projects, PR, branch protection su `main`) | Ogni task del piano = un'issue; review incrociata obbligatoria |
| GitHub Actions CI | ruff, mypy strict, pytest, smoke test dry-run (già configurato) |
| pre-commit + **gitleaks** | Blocca commit con segreti |
| Claude Code + `CLAUDE.md` | Contesto e vincoli condivisi per entrambi quando lavorate con Claude |
| GitHub Actions Secrets | Chiavi per il runner schedulato |

## 12. Server MCP utili in sviluppo

Utili per esplorare dati e ambienti da Claude Code/Desktop durante lo sviluppo. **Il ciclo di
trading in produzione usa gli SDK direttamente** (più deterministico, testabile, loggabile).

- Alpaca MCP Server (ufficiale, `uvx alpaca-mcp-server`, paper di default)
- Kraken CLI (MCP integrato, include i comandi paper)
- `mcp-ccxt` (100+ exchange, sandbox attiva di default)
- Financial Datasets / EODHD / FMP MCP per dati fondamentali

## Account da creare (checklist)

- [ ] Anthropic Console → API key con limite di spesa mensile impostato
- [ ] GitHub: branch protection su `main`, secrets del repo
- [ ] Binance Demo Trading **oppure** Kraken CLI (paper locale, nessun account necessario per il paper)
- [ ] Alpaca (conto paper) se si testano anche equity
- [ ] Finnhub (free), FRED (free API key)
- [ ] Langfuse (cloud free tier o self-host)
- [ ] Telegram bot
- [ ] Supabase (Fase 3)

## Fonti

- [Claude models overview](https://platform.claude.com/docs/en/models/overview) · [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) · [Effort](https://platform.claude.com/docs/en/build-with-claude/effort)
- [Claude Agent SDK vs LangGraph](https://www.developersdigest.tech/blog/claude-agent-sdk-vs-langgraph)
- [Alpaca MCP Server](https://github.com/alpacahq/alpaca-mcp-server) · [Alpaca fuori dagli USA](https://alpaca.markets/support/is-alpaca-available-outside-the-us)
- [Binance Spot Demo Mode](https://developers.binance.com/docs/binance-spot-api-docs/demo-mode/general-info)
- [Kraken CLI](https://github.com/krakenfx/kraken-cli) · [mcp-ccxt](https://pypi.org/project/mcp-ccxt/)
- [Best stock market APIs for AI agents 2026](https://medium.com/codex/the-7-best-stock-market-apis-for-ai-agents-in-2026-6a890a159531) · [Financial MCP servers compared](https://chartlibrary.io/blog/financial-mcp-servers-compared)
- [Python backtesting frameworks 2026](https://quanttradingtools.com/python-backtesting-frameworks/)
- [Langfuse](https://langfuse.com/docs/observability/overview)
