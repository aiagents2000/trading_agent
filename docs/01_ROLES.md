# 01 · Ruoli degli agenti e suddivisione consigliata

_Ultimo aggiornamento: 5 ottobre 2026_

## In una riga

Un desk con **11 ruoli LLM** organizzati in 5 livelli, più **5 componenti deterministici** che gli
LLM non possono scavalcare. Gli LLM esprimono giudizi; il codice decide quanto rischio è ammesso e
cosa arriva al broker.

## Da dove viene questa struttura

| Fonte | Cosa ne prendiamo |
|---|---|
| **TradingAgents** (Tauric Research, arXiv 2412.20138, v0.2.x) | Analyst team specializzato → dibattito bull/bear con facilitatore → trader → risk team (aggressivo/neutrale/conservativo) → fund manager. Report strutturati nello stato condiviso invece di catene di messaggi; due tier di modelli (quick/deep). |
| **"Toward Expert Investment Teams"** (arXiv 2602.23330, feb 2026) | Compiti *fine-grained* battono i ruoli generici ("analizza questo titolo"). L'allineamento tra ciò che producono gli analisti e ciò che serve a chi decide è il fattore che pesa di più sul risultato. |
| **Survey "Agentic Trading"** (arXiv 2605.19337, mag 2026) | Separare stato deterministico (audit-truth) dal contesto generativo; memoria time-aware; log ispezionabili di prompt, tool call e motivazioni. |
| **Alpha Arena S1** (nof1, crypto perp con soldi veri) | Gli LLM che hanno perso di più hanno fatto troppi trade e size eccessive. Previsione, esecuzione, sizing e controllo del rischio vanno valutati insieme. |
| **Studi su leakage e valutazione onesta** (arXiv 2608.27734 e simili) | Il Deflated Sharpe da solo non basta: il leakage va reso *inesprimibile* (feature registry), e ogni tentativo va registrato. Nei test, quasi nessuna strategia scoperta da LLM sopravvive a una valutazione onesta. |

## Mappa del desk

```
LIVELLO 0  Dati & feature (codice)        Market Data · Feature Registry · News Ingest
              │
LIVELLO 1  Analyst team (LLM rapido)      Technical · Sentiment/News · Fundamental/On-chain · Macro/Regime
              │   report strutturati nello stato condiviso
LIVELLO 2  Research (LLM)                 Bull ⇄ Bear  (N round)  →  Research Manager
              │   ResearchThesis {direction, conviction}
LIVELLO 3  Trading (LLM profondo)         Trader → TradeProposal {entry, stop, target, size}
              │
LIVELLO 4  Rischio                        Risk Engine (codice, limiti hard)  →  Risk Committee (LLM, solo riduce)
              │
LIVELLO 5  Decisione (LLM profondo)       Portfolio Manager → TradeDecision
              │
           Esecuzione & post-trade (codice)  Execution · Journal · Performance Auditor  →  Reflection (LLM)

OFFLINE    Strategy Lab                   Strategy Researcher (LLM) → Backtest → Trial Ledger → Validator (codice)
```

## I ruoli LLM

| # | Ruolo | Tier / modello | Input | Output (schema) | Compito fine-grained |
|---|---|---|---|---|---|
| 1 | **Technical Analyst** | rapido · Sonnet 5.5, effort low | feature del registry | `AnalystReport` | Prima il regime (trend/range/chop), poi il segnale; elenca le feature usate. Non calcola indicatori a memoria. |
| 2 | **Sentiment & News Analyst** | rapido | headline con timestamp, score di sentiment | `AnalystReport` | Separa notizie nuove da rumore riciclato; segnala event risk (macro, hack, regolamentazione, listing). |
| 3 | **Fundamental / On-chain Analyst** | rapido | equity: bilanci, insider, earnings · crypto: funding, open interest, flussi exchange, unlock | `AnalystReport` | Fornisce un *prior* lento; confidenza bassa su orizzonti brevi. HOLD se mancano dati. |
| 4 | **Macro & Regime Analyst** | rapido | tassi, dollaro, VIX/vol crypto, dominance BTC, trend indice | `AnalystReport` | Dice se l'ambiente favorisce il rischio, non sceglie l'asset. |
| 5 | **Bull Researcher** | rapido, effort medium | i 4 report + dibattito | `DebateArgument` | Caso long più forte *onesto*: ogni claim cita un punto di un report. Ribatte il bear. |
| 6 | **Bear Researcher** | rapido, effort medium | i 4 report + dibattito | `DebateArgument` | Caso contrario: evidenza debole, trade affollati, reward/risk scarso, regime sbagliato. |
| 7 | **Research Manager** | profondo · Opus 5.5 | report + trascrizione | `ResearchThesis` | Giudica la qualità dell'evidenza, non la retorica. `flat` quando il dibattito è in equilibrio. |
| 8 | **Trader** | profondo | tesi, snapshot, portafoglio | `TradeProposal` | Entry, stop su ATR dove la tesi è invalidata, target con R:R ≥ 1.5, size proporzionale alla conviction. Flat se conviction < 0.55. |
| 9 | **Risk Committee** | rapido, effort medium | proposta già filtrata dai limiti hard | `RiskCommitteeView` | Tre prospettive (aggressiva/neutrale/conservativa) → un unico `size_multiplier` ∈ [0,1]. Correlazioni, event risk, liquidità. |
| 10 | **Portfolio Manager** | profondo, effort high | proposta, verdetto, comitato, portafoglio | `TradeDecision` | Execute / reject / hold. Preferisce pochi trade di qualità. La size è comunque clampata dal codice. |
| 11 | **Reflection Analyst** | profondo | record completo della decisione + esito | `ReflectionNote` | Distingue sfortuna da processo sbagliato; scrive una sola lezione riutilizzabile, visibile solo ai cicli successivi. |

Nel Strategy Lab (offline) si aggiunge un dodicesimo ruolo:

| 12 | **Strategy Researcher** | profondo | catalogo feature del registry, risultati passati del ledger | spec di strategia (regole + parametri) | Propone ipotesi componendo **solo** feature già auditate; non scrive codice che legge dati direttamente. |

## I componenti deterministici (non LLM)

| Componente | Perché non è un LLM |
|---|---|
| **Feature Registry** (`data/features.py`) | I numeri li calcola il codice su barre chiuse. Così il leakage è inesprimibile e gli LLM non "inventano" indicatori. |
| **Risk Engine** (`risk/engine.py`) | Limiti hard da `config/risk_limits.yaml`: size max per posizione, esposizione lorda, rischio max per trade allo stop, trade/giorno, whitelist, kill switch su drawdown, stop obbligatorio. |
| **Execution** (`execution/`) | Id ordine deterministico (idempotenza), fee e slippage modellati, nessun accesso live. |
| **Journal** (`memory/journal.py`) | Registro append-only di ogni ciclo: è la fonte di verità per audit e reflection. |
| **Validator** (`lab/validation.py`) | Walk-forward, trial ledger, Deflated Sharpe, PBO: la statistica non si delega a un LLM. |

## Flusso di un ciclo (ogni 4h per simbolo, configurabile)

1. **Guard**: se il kill switch è attivo il ciclo finisce nel journal senza chiamare LLM.
2. **Analisti** (in parallelo in Fase 2): 4 report brevi (max 6 punti chiave) con fonti dichiarate.
3. **Dibattito**: `debate_rounds` round bull/bear (default 2), poi tesi del Research Manager.
4. **Trader**: se la tesi è `flat` il grafo salta direttamente al journal (zero costi a valle).
5. **Risk Engine**: taglia la size ai limiti o boccia la proposta.
6. **Risk Committee**: può solo ridurre ancora.
7. **Portfolio Manager**: decisione finale entro `size ≤ size_approvata × multiplier`.
8. **Execution** sul paper broker → **Journal**.
9. A posizione chiusa: **Reflection** scrive una lezione con `written_at`; i cicli futuri la vedono
   solo se `written_at < as_of`.

## Configurazioni consigliate

Le configurazioni servono anche come esperimenti: ognuna è una "variante del desk" da confrontare
in paper sullo stesso periodo.

| Config | Ruoli attivi | Chiamate LLM / ciclo | Quando usarla |
|---|---|---|---|
| **A · Lean** | Technical + Sentiment → Trader → Risk Engine → PM | ~4 | Primo giro end-to-end; baseline economica. |
| **B · Standard** (default) | 4 analisti, dibattito 2 round, Research Manager, Trader, Risk Committee, PM | ~12 | Configurazione principale di test. |
| **C · Deep** | come B con dibattito 3 round, Risk Committee 3 voci separate, PM effort high | ~18 | Per capire se più deliberazione migliora davvero (spesso no). |
| **D · Baseline senza LLM** | strategia rule-based + Risk Engine | 0 | Obbligatoria: se il desk LLM non batte questa e il buy & hold, non aggiunge valore. |

Stima indicativa per la Config B con prompt caching attivo: ~12 chiamate × 2 simboli × 6 cicli/giorno
≈ 150 chiamate al giorno. Il costo va misurato davvero in Fase 1 (Langfuse traccia token per ruolo)
prima di aggiungere simboli.

## Principi di design che il codice già applica

1. **Contratti tipizzati, non chiacchiere.** Ogni agente produce un modello Pydantic via structured
   outputs; il testo libero resta nei campi `rationale`.
2. **Gli LLM possono solo ridurre il rischio.** Clamp della size nel codice dopo il PM.
3. **Flat è un risultato valido.** I prompt lo dicono esplicitamente a ogni ruolo; il grafo
   cortocircuita sui flat.
4. **Point-in-time ovunque.** `as_of` in ogni snapshot, ultima barra aperta scartata, lezioni
   filtrate per data, istruzione esplicita di ignorare ciò che il modello "ricorda" dopo `as_of`.
5. **Ogni ruolo è sostituibile.** Modello, effort e prompt per ruolo stanno in `config/agents.yaml`:
   si fa A/B cambiando una riga.

## Un limite da avere chiaro

I modelli Claude attuali conoscono i mercati fino a giugno 2026. Un backtest del team LLM su dati
precedenti è contaminato: il modello può "ricordare" cosa è successo. Per questo **il team LLM si
valuta solo in forward**, in paper, da ottobre 2026 in avanti. Il backtest storico vale solo per le
strategie rule-based del Strategy Lab.

## Fonti

- [TradingAgents (arXiv 2412.20138)](https://arxiv.org/abs/2412.20138) · [repo e overview v0.2.4](https://dev.to/sangrokjung/tradingagents-v024-a-multi-agent-llm-framework-that-simulates-an-entire-trading-firm-g2e)
- [Toward Expert Investment Teams (arXiv 2602.23330)](https://arxiv.org/abs/2602.23330)
- [Agentic Trading: When LLM Agents Meet Financial Markets (arXiv 2605.19337)](https://arxiv.org/html/2605.19337v1)
- [What survives honest evaluation? (arXiv 2608.27734)](https://arxiv.org/html/2608.27734v1)
- [Alpha Arena Season 1: risultati e lezioni](https://www.iweaver.ai/blog/alpha-arena-ai-trading-season-1-results/)
