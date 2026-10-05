# 03 · Piano di implementazione

_Versione 1 · 5 ottobre 2026_

## Obiettivo

Un desk multi-agente che gira **da solo** in paper trading, registra ogni decisione, e permette di
rispondere con numeri a due domande:

1. Il processo decisionale multi-agente batte una baseline rule-based e il buy & hold, al netto di
   fee e costo LLM?
2. Le nuove strategie proposte e testate nel Strategy Lab sopravvivono a una validazione onesta?

**Fuori scope:** trading con soldi veri. Se un giorno servirà, sarà un piano separato con criteri
di accesso propri.

## Stato attuale (Fase 0 · completata)

Nello scaffolding iniziale ci sono già:

- Contratti Pydantic per tutti gli scambi tra agenti (`domain/models.py`)
- 11 ruoli configurati con modello, effort e prompt versionato (`config/agents.yaml`, `prompts/`)
- Grafo LangGraph del ciclo con guard, cortocircuito sui flat, risk engine, PM, esecuzione, journal
- Risk engine deterministico con 7 controlli e kill switch su drawdown
- Paper broker con fee, slippage e ordini idempotenti
- Feature registry con test di non-lookahead
- Journal JSONL con lezioni visibili solo nel futuro
- Deflated Sharpe e trial ledger per il Lab
- Dry-run completo senza API key (`trading-agent cycle --dry-run --offline`)
- CI (ruff, mypy strict, pytest, smoke test), pre-commit con gitleaks, template PR, CONTRIBUTING

## Suddivisione del lavoro in due

Due track con confine netto: si toccano solo attraverso i contratti in `domain/models.py`.

| Track | Ownership | Cartelle |
|---|---|---|
| **A · Agenti & LLM** | prompt, ruoli, grafo, reflection, osservabilità, valutazione | `agents/`, `prompts/`, `orchestration/`, `llm/`, `memory/` |
| **B · Dati, rischio & infra** | dati, feature, broker, scheduler, storage, Strategy Lab | `data/`, `execution/`, `risk/`, `lab/`, `.github/`, infra |

Ogni modifica a un contratto condiviso (`domain/`) o ai limiti di rischio richiede review dell'altro
track. Le task sotto riportano la track suggerita; ridistribuitele liberamente.

---

## Fase 1 · MVP end-to-end con LLM reali (settimane 1–2)

Obiettivo: il ciclo completo gira su BTC/USDT ed ETH/USDT con Claude, dati reali e stato persistente.

| ID | Task | Track | Dettaglio |
|---|---|---|---|
| F1.1 | Test di contratto LLM | A | Un test per schema che chiama davvero Claude (marker `@pytest.mark.llm`, escluso dalla CI) e verifica che `messages.parse` + effort funzionino per ogni ruolo |
| F1.2 | Dati reali ccxt + cache | B | Verificare `CcxtMarketData` su Binance/Kraken, cache OHLCV su parquet, gestione rate limit e retry |
| F1.3 | **Gestione posizioni aperte** | B | Monitor deterministico che a ogni ciclo controlla stop e take profit sulle barre chiuse e chiude la posizione. Oggi il broker apre ma non chiude |
| F1.4 | **Stato persistente del broker** | B | Il `PaperBroker` oggi vive in memoria per un singolo run: persistere cash, posizioni e fill (SQLite) così i cicli si sommano nel tempo |
| F1.5 | Regole sulle posizioni esistenti | A | Se esiste già una posizione sul simbolo, il ciclo valuta hold / riduci / chiudi invece di aprire da zero (nuovo campo nel `TradeProposal`) |
| F1.6 | Tracing Langfuse | A | Una trace per ciclo, span per ruolo, token e costo per ruolo |
| F1.7 | Notifiche Telegram | B | Execute, kill switch, errori, riepilogo giornaliero |
| F1.8 | Reflection alla chiusura | A | Alla chiusura di un trade il Reflection Analyst legge il record del ciclo e scrive una `ReflectionNote` |
| F1.9 | Baseline D | B | Strategia rule-based (es. trend-following o una Donchian/ADX già validata) che passa dallo stesso risk engine e broker, con journal separato |

**Criteri di uscita**
- 7 giorni di cicli eseguiti (anche lanciati a mano) senza errori non gestiti
- Ogni ciclo è ricostruibile dal journal: input, report, dibattito, decisione, fill
- Costo LLM medio per ciclo misurato per ruolo (Langfuse)
- Baseline D gira in parallelo

## Fase 2 · Automazione e dati completi (settimane 3–4)

Obiettivo: nessun intervento manuale, tutti gli analisti con dati veri, più varianti del desk in
parallelo.

| ID | Task | Track | Dettaglio |
|---|---|---|---|
| F2.1 | Scheduler | B | GitHub Actions `schedule` ogni 4h (a minuto sfalsato, es. `7 */4 * * *`) con stato su storage esterno; alternativa VPS se il runner stateless crea attrito |
| F2.2 | News ingest | B | Finnhub / CryptoPanic / RSS normalizzati con `published_at`, deduplica, filtro `<= as_of` |
| F2.3 | Macro & derivati | B | FRED, CoinGecko (dominance), funding rate e open interest via ccxt nel feature registry |
| F2.4 | Analisti in parallelo | A | Fan-out LangGraph sui 4 analisti, fan-in prima del dibattito |
| F2.5 | Adapter broker demo | B | Binance Spot Demo Mode o Kraken CLI paper dietro l'interfaccia `Broker`; Alpaca paper per equity |
| F2.6 | Checkpointer LangGraph | A | SQLite: un ciclo interrotto riprende senza rifare chiamate LLM già pagate |
| F2.7 | Varianti del desk | A | Config A (lean), B (standard), D (baseline) in parallelo su portafogli paper separati, stessi simboli e stessi orari |
| F2.8 | Budget guard | A | Tetto di spesa LLM giornaliero: superato il tetto, i cicli passano in modalità solo-journal |

**Criteri di uscita**
- 14 giorni consecutivi di run schedulati senza intervento
- Nessuna notizia o feature con timestamp successivo ad `as_of` (test automatico sul journal)
- Tre varianti del desk confrontabili sullo stesso periodo

## Fase 3 · Strategy Lab (settimane 5–8)

Obiettivo: proporre, testare e scartare strategie in modo che l'overfitting venga intercettato.

| ID | Task | Track | Dettaglio |
|---|---|---|---|
| F3.1 | Motore di backtest | B | Vettoriale, fee e slippage, esecuzione alla barra successiva, walk-forward con finestre rolling |
| F3.2 | Strategy spec | B | Formato JSON/YAML che compone **solo** feature del registry + regole (entry, exit, sizing). Niente codice arbitrario che legge dati |
| F3.3 | Strategy Researcher | A | Agente che legge catalogo feature e ledger, propone spec nuove, le lancia nel backtest. Candidato naturale: Claude Agent SDK o un sottografo LangGraph; Batch API per abbattere i costi |
| F3.4 | Validator | B | Deflated Sharpe sul numero reale di trial, PBO con CSCV, intervalli di confidenza bootstrap, holdout finale "chiuso a chiave" usato una sola volta |
| F3.5 | Test del validator | B | Il validator deve **bocciare** una strategia oracolo con leakage piantato apposta e una strategia casuale |
| F3.6 | Promozione | A | Una strategia che passa entra in paper forward come segnale per il Technical Analyst o come desk dedicato. Il backtest non basta mai: serve il forward |
| F3.7 | Storage condiviso + dashboard | B | Postgres su Supabase; dashboard Streamlit o Next.js su Vercel |

**Criteri di uscita**
- Pipeline Lab end-to-end con trial ledger completo
- Oracolo e random bocciati in automatico
- Almeno una strategia candidata in paper forward (anche se poi fallisce)

## Fase 4 · Valutazione e iterazione (settimane 9–12, poi continua)

| ID | Task | Track | Dettaglio |
|---|---|---|---|
| F4.1 | Report settimanale automatico | A | Per variante: rendimento, Sharpe, max drawdown, turnover, hit rate, fee pagate, costo LLM per trade, confronto vs baseline D e buy & hold |
| F4.2 | Ablation | A | Togliere un ruolo alla volta (es. senza dibattito, senza risk committee) per misurarne il contributo reale |
| F4.3 | A/B sui prompt | A | Versioni dei prompt tracciate nel journal; un prompt cambiato inizia un nuovo track record |
| F4.4 | Robustezza | B | Stress test: gap, exchange down, dati mancanti, risposte LLM invalide |
| F4.5 | Motore di produzione (opzionale) | B | Portare la strategia migliore su NautilusTrader per parità backtest/paper |

## Protocollo di valutazione

- **Il desk LLM si valuta solo in forward.** I modelli conoscono il mercato fino a giugno 2026: un
  backtest storico del team è contaminato e non conta.
- **Benchmark sempre presenti:** baseline rule-based (D) e buy & hold sugli stessi simboli.
- **Metriche:** Sharpe e Sortino, max drawdown, turnover, numero di trade, fee, slippage stimato,
  costo LLM totale e per trade, percentuale di cicli flat.
- **Orizzonte minimo prima di trarre conclusioni:** 8–12 settimane di forward; meno di 30 trade per
  variante non permette conclusioni statistiche.
- **Successo di un esperimento** (da confermare insieme): la variante batte la baseline D al netto
  dei costi LLM con max drawdown non peggiore, su almeno due simboli.

## Stima costi (da verificare in Fase 1)

Config B, 2 simboli, un ciclo ogni 4h, ipotesi ~3–4k token in input e ~1k in output per chiamata:

| Voce | Ordine di grandezza |
|---|---|
| Costo per ciclo (8 chiamate Sonnet 5.5 + 4 Opus 5.5) | ~$0.20–0.30 |
| Cicli al giorno | 12 |
| Costo mensile LLM | ~$70–110 |

Riduzioni già previste: cortocircuito sui flat (salta trader, rischio e PM), prompt caching,
effort basso sugli analisti, Batch API per il Lab. Misurare prima di aggiungere simboli.

## Rischi principali

| Rischio | Mitigazione |
|---|---|
| Leakage temporale (news, memoria, conoscenza del modello) | Feature registry, filtri `as_of`, lezioni time-aware, valutazione solo forward |
| Overfitting nel Lab | Trial ledger completo, Deflated Sharpe, PBO, holdout chiuso, test con oracolo |
| Overtrading / size eccessive | Limiti hard nel risk engine, max trade/giorno, clamp della size dopo il PM |
| Costi LLM fuori controllo | Budget guard, metriche di costo per ruolo, config lean |
| Output LLM invalidi o allucinati | Structured outputs, validatori Pydantic (es. stop dal lato giusto), fallback a hold |
| Divergenza tra i due collaboratori | Track separate, contratti condivisi, CI obbligatoria, ADR per le decisioni |
| Fragilità del runner | Retry, idempotenza ordini, checkpointer, notifiche errori |

## Prossimi passi immediati

1. Proteggere `main` (PR + CI obbligatorie) e aggiungere il collaboratore alla repo.
2. Creare le issue F1.1–F1.9 e assegnarle alle due track.
3. Creare la API key Anthropic con limite di spesa e lanciare il primo ciclo reale:
   `trading-agent cycle --symbol BTC/USDT`.
