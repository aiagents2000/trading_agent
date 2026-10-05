# ADR 0001 — Architettura ibrida: LLM per il giudizio, codice per rischio ed esecuzione

- Stato: accettato (bozza iniziale, da confermare in review)
- Data: 2026-10-05

## Contesto

Vogliamo un team di agenti che riproduca il processo decisionale di una trading desk, per testare
il processo stesso e validare strategie. La letteratura (TradingAgents, survey 2026 sull'agentic
trading) e i benchmark live (Alpha Arena) mostrano tre problemi ricorrenti: overtrading, size
eccessive e assenza di disciplina sul rischio quando l'LLM ha l'ultima parola; leakage temporale nei
backtest; output degli analisti non allineati a ciò che serve a valle.

## Decisione

1. Gli LLM producono **giudizi** (report, tesi, proposte, decisioni) come oggetti Pydantic tipizzati.
2. Feature, limiti di rischio, sizing massimo, esecuzione e journal sono **codice deterministico**.
   Il Risk Engine è un nodo del grafo che nessun agente può bypassare; gli agenti possono solo
   ridurre la size.
3. Orchestrazione con **LangGraph**: grafo esplicito, checkpoint, routing per ruolo su modelli
   diversi, indipendenza dal provider.
4. Default LLM: Claude Sonnet 5.5 (tier rapido) e Claude Opus 5.5 (tier profondo).
5. Valutazione del team LLM **solo in forward** (paper), perché i modelli conoscono il passato fino
   al loro cutoff. Il backtest storico è riservato alle strategie rule-based del Strategy Lab.

## Conseguenze

- Più codice "noioso" da scrivere (risk, broker, journal), ma il comportamento peggiore possibile
  di un LLM è limitato a priori.
- Il track record del team si accumula lentamente (serve tempo reale): pianifichiamo 8-12 settimane
  di paper prima di qualunque conclusione.
- Cambiare provider LLM richiede solo un nuovo adapter in `llm/client.py`.

## Template per i prossimi ADR

Titolo · Stato · Data · Contesto · Decisione · Alternative considerate · Conseguenze
