## Cosa cambia

<!-- Una o due frasi. Link all'issue / fase del piano (es. "Fase 1 · F1.3"). -->

## Tipo di modifica

- [ ] Codice (feature / fix / refactor)
- [ ] Prompt di un agente (`prompts/`)
- [ ] Limiti di rischio (`config/risk_limits.yaml`) ⚠️ richiede review esplicita
- [ ] Documentazione

## Checklist

- [ ] `pytest`, `ruff`, `mypy` passano in locale
- [ ] Nessun segreto, chiave o dato personale nel diff
- [ ] Nuove feature di mercato hanno un test di non-lookahead
- [ ] Se tocco un prompt: ho incrementato la versione nel commento in testa e annotato il motivo
- [ ] Se tocco il risk engine o i limiti: ho spiegato perché il rischio non aumenta senza motivo
