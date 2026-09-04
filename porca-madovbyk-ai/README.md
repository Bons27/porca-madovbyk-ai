# Porca MaDovbyk AI

Agente automatico per la gestione della squadra di Fantacalcio **Porca MaDovbyk**.

## Stato del progetto

V1 — Step 1 completato:

- rosa importata dal CSV di Leghe Fantacalcio;
- configurazione della lega salvata nel codice;
- soglie gol 66 / 71 / 76 / ... implementate;
- modificatore difesa implementato;
- test automatici GitHub Actions predisposti.

## Regole principali

- Modalità: Classic
- 8 partecipanti
- Moduli: 3-4-3, 3-5-2, 4-4-2, 4-3-3, 4-5-1, 5-4-1, 5-3-2
- 5 sostituzioni
- Modificatore difesa con portiere incluso
- Gol: 1° a 66, 2° a 71, poi +1 gol ogni 5 punti

### Modificatore difesa

Si applica solo se dopo le sostituzioni restano almeno 4 difensori e almeno 4 difensori hanno un voto valido.
Con il portiere incluso, la media usa:

- voto puro del portiere;
- migliori 3 voti puri dei difensori.

Bonus:

- media < 6: 0
- 6 <= media < 6.5: +1
- 6.5 <= media < 7: +3
- media >= 7: +6

## Avvio locale

Dalla cartella del progetto:

```bash
python -m src.main
```

## Test

```bash
python -m unittest discover -s tests -v
```

## Sicurezza

Non caricare mai token Telegram, chiavi API o password direttamente nel repository.
Useremo **GitHub Actions Secrets** nei prossimi passaggi.
