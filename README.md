# OnDemand Analytics

Applicazione per l'analisi dei dati di una startup digitale di servizi on-demand.

Un prototipo **locale e riproducibile**: genera dati sintetici, li pulisce e carica in un data warehouse SQLite a stella, poi li presenta in una dashboard interattiva con Streamlit.

**Non sono utilizzati dati personali, API esterne, servizi cloud o credenziali.** I nomi dei 320 fornitori sono generati automaticamente con la libreria **Faker** (`it_IT`) e non derivano da un archivio di fornitori coinvolti nel progetto. La categoria di servizio è memorizzata separatamente; possibili coincidenze casuali tra un nome generato e una società esistente non possono essere escluse.

## 1. Requisiti

- Computer Windows, macOS o Linux.
- **Python 3.11–3.15** installato (su Windows: selezionare «Add Python to PATH» durante l'installazione).
- Connessione a Internet **soltanto per la prima installazione** delle librerie da PyPI; dopo l'installazione il prototipo gira in locale.
- Un browser moderno.

La rigenerazione del dataset e del database richiede normalmente pochi secondi su un computer corrente; l'installazione iniziale di Python e delle librerie può richiedere più tempo in base al computer e alla connessione.

## 2. Avvio semplice su Windows

1. Estrarre **tutto il file ZIP** in una cartella, ad esempio `Documenti\OnDemand_Analytics`.
2. Aprire la cartella e fare doppio clic su **`AVVIA_WINDOWS.bat`**.
3. La prima esecuzione crea un ambiente Python locale, installa Streamlit, pandas e Faker, genera i CSV e il database, quindi apre la dashboard nel browser.
4. Se il browser non si apre da solo, visitare **http://localhost:8501**.
5. Per interrompere l'applicazione, tornare alla finestra dei comandi e premere `Ctrl+C`.

Nota: se Windows mostra un avviso sul file `.bat` scaricato, aprire il file con Blocco note per verificarne il contenuto. Non richiede privilegi di amministratore né installa servizi.

### Metodo manuale (Windows PowerShell)

Aprire PowerShell nella cartella del progetto ed eseguire:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe prepare.py
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Se `py` non è disponibile, usare `python`. Per i successivi avvii, dopo l'installazione e la preparazione basta l'ultima riga.

### macOS e Linux

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python prepare.py
python -m streamlit run app.py
```

In alternativa, eseguire lo script `./AVVIA_MAC_LINUX.sh` (ricrea il dataset). Se la porta 8501 è occupata, Streamlit comunica l'indirizzo effettivo da aprire.

## 3. Rigenerare e verificare in pochi minuti

Da terminale nella cartella del progetto:

```bash
python prepare.py
python check_project.py
python -m unittest discover -s tests -v
```

`prepare.py` usa un seme fisso (**20261115**): ogni esecuzione riproduce i medesimi file CSV e gli stessi risultati. I nomi dei fornitori vengono creati con **Faker 40.1.2**, `Faker("it_IT")` e `seed_instance(20261115)`; il numero di versione è bloccato in `requirements.txt`, poiché l’elenco di nomi potrebbe variare aggiornando Faker. Il generatore Faker è indipendente da quello usato per richieste, importi e tempi. Le denominazioni sono limitate a 30 caratteri, per restare leggibili nel grafico dei fornitori. Il database viene ricreato in un file temporaneo e sostituito soltanto dopo il controllo di integrità. La procedura non duplica le righe.

**Importante:** `python prepare.py` sovrascrive i CSV e il database dimostrativi. Non modificarli se si desidera preservare una versione personalizzata.

## 4. Struttura dei file

```text
OnDemand_Analytics/
├── AVVIA_WINDOWS.bat           Avvio guidato per Windows
├── AVVIA_MAC_LINUX.sh          Avvio guidato per macOS e Linux
├── README.md                    Guida di avvio, modello e definizioni
├── requirements.txt            Librerie indispensabili
├── generate_data.py            Generatore riproducibile dei 4 CSV
├── etl.py                      Pulizia, validazione e caricamento
├── prepare.py                  Orchestrazione generazione + ETL
├── check_project.py            Verifica rapida e indicatori
├── app.py                      Dashboard Streamlit
├── data/
│   ├── clienti.csv              360 record
│   ├── fornitori.csv            320 record
│   ├── operatori.csv            300 record
│   └── richieste.csv            550 record
├── warehouse/
│   └── startup_on_demand.sqlite Database SQLite già popolato
├── sql/
│   ├── schema.sql               Definizione tabelle, chiavi e indici
│   └── queries.sql              Sette query SQL esemplificative
├── docs/
│   ├── schema_stella.md         Modello e spiegazione dei legami
│   └── relazione_tecnica.md     Relazione tecnica e risultati ottenuti
├── tests/
│   └── test_pipeline.py         10 controlli automatici
└── .streamlit/
    └── config.toml              Configurazione grafica dell'interfaccia
```

## 5. Dati sintetici

| Tipologia | Numero di record | Campi più significativi |
|:--|--:|:--|
| Clienti | 360 | ID fittizio, zona, data di iscrizione |
| Fornitori | 320 | ID fittizio, denominazione commerciale di fantasia, categoria, zona |
| Operatori | 300 | ID fittizio, zona, attività |
| Richieste | 550 | ID, tre riferimenti, data e ora, zona, importo, tempo, stato, ritardo |

Le richieste coprono il periodo **01/01/2026–31/10/2026**. Il generatore modella orari di punta, differenze tra giorni feriali e fine settimana, una quota di annullamenti e di ritardi, tariffe variabili e clienti che richiedono più servizi. Un fornitore e l'operatore associato sono sempre coerenti con la zona e la categoria della richiesta.

Il dataset **non** contiene nomi di persone, numeri telefonici, email, indirizzi o altri dati personali. La zona è una categoria sintetica («Centro», «Nord», «Sud», «Est», «Ovest»), non una geolocalizzazione individuale.

## 6. Data warehouse a stella

Il modello comprende una tabella di fatti, `fact_richieste`, al centro e quattro dimensioni collegate mediante chiavi esterne:

- `dim_cliente`
- `dim_fornitore`
- `dim_operatore`
- `dim_tempo`

La **granularità** è una richiesta di servizio. Ogni richiesta si riferisce a un solo cliente, fornitore, operatore e giorno. La dimensione Tempo contiene una riga per ogni giorno che appare nel dataset; per questo può avere meno di 300 righe. La richiesta conserva l'ora in `timestamp_richiesta`.

La zona della prestazione è memorizzata nel fatto (`zona_servizio`) per poterla aggregare direttamente; la zona anagrafica è presente anche nelle dimensioni e viene verificata per coerenza. Questa è una **denormalizzazione intenzionale** utile all'analisi.

Gli identificativi di origine (`C0001`, ecc.) sono conservati nelle dimensioni; il fatto utilizza le rispettive chiavi surrogate intere.

## 7. Procedura ETL

`etl.py` svolge le tre fasi fondamentali:

1. **Estrazione:** legge con `csv.DictReader` i quattro file, compatibili con UTF-8 e UTF-8 con BOM.
2. **Trasformazione:** elimina spazi esterni e doppi, uniforma zone e categorie, controlla date, decimali, tempi, stati e coerenza tra cliente, fornitore e operatore. Gli importi vengono verificati tramite `Decimal`.
3. **Caricamento:** crea lo schema SQLite, carica prima le dimensioni e poi la tabella dei fatti, costruisce la dimensione Tempo dalle date delle richieste, crea indici e applica `PRAGMA foreign_key_check` e `PRAGMA integrity_check`.

In presenza di errori, la preparazione fallisce **senza sostituire il database precedente**.

## 8. Dashboard e regole di conteggio

### Indicatori

- **Richieste totali:** tutte le richieste, comprese le annullate.
- **Incassi:** somma degli importi delle **sole richieste completate**; le annullate hanno importo zero.
- **Tempo medio di erogazione:** media dei minuti delle **sole richieste completate**.
- **Clienti attivi:** clienti distinti con almeno una richiesta completata nella selezione.
- **Clienti che ritornano:** clienti con **almeno 2 richieste completate nella selezione**, divisi per tutti i clienti con almeno una richiesta completata nella stessa selezione.
- **Annullamenti e ritardi:** indicatori integrativi utili a interpretare il servizio.

### Grafici

- andamento mensile/giornaliero delle richieste;
- 5 fornitori con maggiori incassi da servizi completati;
- richieste per zona;
- richieste per categoria di servizio.

Filtri simultanei per **periodo, zona e categoria**, applicati in tutte le interrogazioni. È possibile scaricare il riepilogo filtrato in CSV dalla dashboard.

Le query SQL non filtrate, utili per una verifica indipendente, sono disponibili in `sql/queries.sql`.

## 9. Limiti e possibili sviluppi

I dati sono simulati e non permettono conclusioni sull'andamento di un'impresa reale. In particolare, mancano variazioni storiche delle dimensioni, dati di costo o di margine e procedure di aggiornamento incrementale. L'ETL attuale **ricarica l'intero dataset**, per garantire semplicità e riproducibilità. In un sistema operativo reale sarebbe opportuno prevedere caricamenti incrementali, tracciamento degli errori, test automatizzati estesi e gestione dello storico delle modifiche (**SCD di tipo 2**).

## 10. Acquisire le schermate per il report

Per documentare il funzionamento della dashboard con immagini **effettive**, acquisire le schermate sul computer su cui è in esecuzione Streamlit:

1. avviare l'app e lasciare tutti i filtri sulle impostazioni iniziali;
2. usare `Win + Shift + S` su Windows per catturare **la schermata degli indicatori**;
3. acquisire **la schermata dei quattro grafici** (eventualmente in due immagini);
4. salvare le immagini e inserirle nella sezione «Risultati» della relazione.

Le immagini devono essere ottenute dalla dashboard reale, **non disegnate o simulate**. Un modello del testo del report si trova in `docs/relazione_tecnica.md`.

## 11. Risoluzione dei problemi

- `python` o `py` non riconosciuto: installare Python 3.11–3.15 e aggiungerlo al PATH.
- `No module named streamlit`: installare le dipendenze con `python -m pip install -r requirements.txt` usando lo stesso interprete che avvia l'app.
- Database non trovato: eseguire `python prepare.py` nella cartella principale.
- Porta 8501 già occupata: chiudere un'altra istanza o seguire l'indirizzo mostrato in terminale.
- File ZIP aperto senza estrazione: estrarlo interamente prima di avviare gli script.

**Verifiche:** la generazione dei dati, il caricamento ETL e i 10 test automatici sono stati eseguiti. La dashboard Streamlit è stata avviata e visualizzata in un browser su Windows nella versione precedente; sono stati verificati i filtri geografico, temporale e per categoria, nonché l’esportazione CSV. Nella nuova versione con Faker, la pipeline, il database e i test sono stati verificati; rimane da controllare visivamente la dashboard dopo l’aggiornamento dei nomi.
