# Porca MaDovbyk AI

Agente automatico gratuito per la gestione della squadra di Fantacalcio **Porca MaDovbyk**.

## Versione stabile

**Dashboard V5.1 · FIA V3 decision engine**

La parte di explainability FIA V5.2 è stata accantonata dal percorso stabile. Il FIA V3 resta attivo nei motori decisionali già collaudati.

## Funzioni principali

- Formazione consigliata per Campionato e Battle Royale.
- Trade Analyzer per scambi specifici.
- Talent Scout degli svincolati con storico e trend.
- Asta di riparazione di febbraio con tagli, budget e target.
- Simulatore asta contro le altre 7 squadre.
- Control Center riepilogativo.
- Storico FIA allenatore × ruolo.
- Notifiche automatiche Telegram in uscita.
- Automazioni GitHub Actions per report e scouting.

## Regole lega

- Modalità Classic.
- 8 partecipanti.
- Rosa: 3 P, 8 D, 8 C, 6 A.
- Moduli: 3-4-3, 3-5-2, 4-4-2, 4-3-3, 4-5-1, 5-4-1, 5-3-2.
- 5 sostituzioni.
- Bonus: assist +1, clean sheet +1, rigore parato +3, gol +3, rigore segnato +3.
- Malus: gol subito -1, rigore sbagliato -3, autogol -2, espulsione -1, ammonizione -0.5.
- Modificatore difesa con portiere incluso: +1 / +3 / +6 in base alla media dei voti puri.
- Soglie gol: 66, 71, poi +1 gol ogni 5 punti.

## Avvio quotidiano

Dalla cartella `porca-madovbyk-ai`:

- `Porca MaDovbyk AI.vbs` → avvio silenzioso, senza finestra nera.
- `Avvia Porca MaDovbyk AI.bat` → avvio diagnostico, utile se qualcosa non funziona.
- `Chiudi Porca MaDovbyk AI.bat` → chiude la Dashboard locale sulla porta 8501.

La Dashboard viene aperta su:

`http://localhost:8501`

## Aggiornamento

Se Git non è disponibile nel PATH, aggiornare con GitHub Desktop:

1. Fetch origin.
2. Pull origin, se disponibile.
3. Avviare nuovamente la Dashboard.

## Automazioni

- **Agente Automatico**: controlla le finestre pre-giornata e invia il report Telegram quando previsto.
- **Talent Scout**: aggiorna quotidianamente gli svincolati e lo storico scouting.
- **FIA History**: aggiorna lo storico FIA quando sono disponibili nuove giornate.
- **Dashboard V5.1 Smoke Test**: verifica che il runtime stabile venga generato e compilato correttamente.

## Dati

Il progetto usa dati pubblici Fantacalcio/Serie A, file di lega locali e dataset storici costruiti dalle stagioni precedenti. I file generati localmente, l'ambiente `.venv` e le cache Python non vengono versionati.

## Sicurezza

Token Telegram, chiavi API e password non devono essere inseriti nel codice o nei file del repository. I segreti operativi restano nei GitHub Actions Secrets.
