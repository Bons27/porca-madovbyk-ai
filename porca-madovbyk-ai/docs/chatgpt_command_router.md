# 🧠 Porca MaDovbyk AI — Command Router

Questo file definisce come il Progetto ChatGPT deve instradare le richieste operative senza modificare la Dashboard V5.1 stabile.

## Regola generale
1. Leggere sempre `docs/chatgpt_project_context.md` quando la richiesta è operativa sul Fantacalcio.
2. Usare GitHub come fonte primaria per rosa, rose avversarie, svincolati, calendario di lega e stato Scout.
3. Per dati live o stagionali non presenti nel repository, verificare fonti aggiornate prima di rispondere.
4. Per date/orari/calendari reali delle partite, non fidarsi di una sola fonte: usare almeno due fonti indipendenti oppure una fonte ufficiale della competizione. Se c'è conflitto, dichiararlo e non presentare il dato come confermato.
5. Distinguere sempre tra dato certo, stima del modello e inferenza.
6. Non modificare codice o file della Dashboard stabile senza richiesta esplicita dell'utente.

## 1. Control Center
Richieste tipiche:
- “Fammi il punto della situazione.”
- “Come siamo messi?”

Leggere almeno:
- `data/league_rosters.csv`
- `data/scout_state.json`
- `data/league_calendar.csv`

Output consigliato:
- stato sintetico rosa
- reparti forti/deboli
- eventuali priorità di mercato
- principali segnali Talent Scout
- prossimo impegno di lega solo se il turno Serie A corrente è verificato
- 3 azioni prioritarie, ordinate

## 2. Formazione
Richieste tipiche:
- “Preparami la formazione.”
- “Meglio 4-3-3 o 4-4-2?”

Leggere:
- `data/league_rosters.csv`
- `src/start_score.py`
- `src/lineup_optimizer.py`
- `src/final_advice_report.py`
- `src/battle_royale_engine.py`
- `src/rules.py`

Poi verificare live, quando necessario:
- disponibilità
- probabile titolarità
- infortuni/squalifiche
- avversario reale e data della partita

Criteri:
- XI migliore complessivo
- modificatore difesa
- Campionato H2H + Battle Royale
- preferenza 4-3-3 / 4-4-2 solo a parità sostanziale

Output:
- modulo
- XI
- panchina
- esclusioni importanti
- 2-4 ballottaggi spiegati
- rischio principale

## 3. Trade Analyzer
Richieste tipiche:
- “Analizza X per Y.”
- “Chi posso offrire per X?”

Leggere:
- `data/league_rosters.csv`
- `src/trade_value.py`
- `src/trade_engine.py`
- `src/trade_analyzer.py`
- `src/trade_competition_impact.py`

Valutare:
- valore assoluto
- impatto sull'XI
- profondità
- sostituibilità
- bisogno dei due reparti
- H2H + Battle Royale
- probabilità realistica di accettazione

Output:
- verdetto
- chi guadagna tecnicamente
- impatto per reparto
- rischio
- eventuale controproposta più realistica

## 4. Talent Scout
Richieste tipiche:
- “Migliori svincolati.”
- “Chi devo prendere a centrocampo?”

Leggere:
- `data/free_agents.csv`
- `data/scout_state.json`
- `data/scout_history.csv`
- `src/talent_scout.py`
- `src/talent_scout_fia.py`

Valutare:
- Scout Score
- Breakout Score
- MV / Fantamedia
- partite a voto
- trend
- quotazione / FVM
- titolarità
- FIA come segnale secondario

Output:
- shortlist per ruolo
- profilo: affidabile / upside / scommessa
- chi tagliare eventualmente dalla rosa
- priorità numerata

## 5. Asta di Febbraio
Richieste tipiche:
- “Preparami il piano asta.”
- “Chi taglio?”

Leggere:
- `data/league_rosters.csv`
- `data/free_agents.csv`
- `data/scout_state.json`
- `src/repair_rules.py`
- `src/repair_auction_engine.py`
- `src/repair_auction_optimizer.py`

Regole fisse:
- 250 crediti iniziali per squadra
- tagli illimitati
- taglio normale = 0 crediti
- trasferimento estero con `*` = rimborso 50% costo originale
- costo estivo irrilevante per il taglio normale

Output:
- tagli consigliati
- budget risultante
- priorità per ruolo
- target A/B/C
- tetto tecnico per target
- rischio concorrenza

## 6. Simulazione Asta
Richieste tipiche:
- “Simula l'asta se taglio X e Y.”

Leggere:
- `data/league_rosters.csv`
- `data/free_agents.csv`
- `data/scout_state.json`
- `src/repair_auction_simulator.py`
- `src/repair_auction_simulation_report.py`

Output:
- scenari di acquisizione
- concorrenti più probabili
- fascia di prezzo plausibile
- piano alternativo se il target salta

## 7. Scheda Giocatore
Richieste tipiche:
- “Fammi la scheda completa di X.”

Leggere:
- `src/player_detail.py`
- `src/player_context_v3.py`
- dataset pertinenti per ruolo/club se necessario

Mostrare quando disponibili:
- ruolo, club
- media voto
- fantamedia
- partite a voto
- gol, assist
- gol casa/trasferta
- rigori segnati/totali
- ammonizioni, espulsioni, autogol
- quotazione attuale, FVM
- utilizzo: titolare, subentrato, infortunato, squalificato, inutilizzato
- andamento giornata per giornata

Se un campo non è supportato dalla fonte, scrivere `n/d` invece di inferirlo.

## 8. FIA Allenatori
Richieste tipiche:
- “Quanto aiuta l'allenatore questo ruolo?”

Leggere:
- `src/player_context_v3.py`
- `src/fia_coach_dashboard.py`
- `src/decision_fia.py`

Regola:
- FIA è un segnale di contesto allenatore×ruolo, non una prova causale.
- Non deve dominare da solo una decisione.

## Politica di affidabilità
Prima di formulare una raccomandazione operativa:
- controllare che i giocatori appartengano davvero alla rosa/svincolati correnti;
- controllare che ruolo e club siano coerenti con i dati più recenti;
- per una partita specifica, verificare data e avversario con fonti affidabili;
- non usare output vecchi della Dashboard come se fossero live;
- in caso di dato ambiguo, fermare la conclusione forte e segnalare cosa manca.
