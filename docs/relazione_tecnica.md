# OnDemand Analytics — Relazione tecnica

Analisi dei dati per una startup digitale di servizi on-demand.

Questo documento descrive l'architettura, le elaborazioni e i risultati della simulazione. Le immagini della dashboard possono essere acquisite durante l'esecuzione locale dell'applicazione.

## 1. Descrizione del contesto

Il caso analizzato riguarda una startup digitale immaginaria che mette in relazione clienti, fornitori e operatori incaricati di erogare servizi su richiesta. La piattaforma registra le richieste ricevute e la loro esecuzione, ma le informazioni operative sono distribuite tra archivi separati. Il problema gestionale consiste nel ricondurre questi dati a un quadro unitario, in modo da osservare volumi, incassi, tempi di erogazione, distribuzione territoriale e frequenza con cui i clienti utilizzano nuovamente il servizio.

Il prototipo sviluppato non rappresenta un'impresa reale. Tutti i dati sono generati con procedure deterministiche, mediante identificativi artificiali, senza email, numeri di telefono, nomi di clienti o informazioni personali. Il progetto ha quindi carattere dimostrativo: permette di verificare che una sequenza completa di generazione, trasformazione, caricamento e analisi possa essere riprodotta su un normale computer.

## 2. Origine e caratteristiche delle fonti simulate

La base informativa comprende quattro file CSV indipendenti. I primi tre descrivono **360 clienti**, **320 fornitori** e **300 operatori**. Il quarto contiene **550 richieste**, collegate alle altre tre tipologie mediante identificativi fittizi. Le richieste si distribuiscono tra gennaio e ottobre 2026, in cinque zone convenzionali e cinque categorie di servizio. La procedura di generazione prevede differenze tra fasce orarie e giorni della settimana, una quota di annullamenti e casi di ritardo. Alcuni clienti effettuano richieste multiple e alcuni fornitori ricevono un volume maggiore di incarichi. I nomi dei fornitori sono prodotti automaticamente dalla libreria Python Faker, con localizzazione italiana e seme fisso; non sono estratti da un archivio di fornitori reali. La categoria di attività è assegnata e conservata in un campo distinto dal nome. Non si può escludere che una denominazione generata coincida casualmente con quella di un’impresa esistente.

Le relazioni sono costruite in modo coerente: in ciascuna richiesta, la zona del cliente coincide con quella del servizio, del fornitore e dell'operatore; la tipologia di attività dell'operatore coincide con la categoria del fornitore. Il generatore impiega un seme fisso (`20261115`) e una versione bloccata di Faker (`40.1.2`), così da replicare nomi e osservazioni quantitative anche dopo la rigenerazione. I nomi sono generati da un’istanza casuale distinta da quella utilizzata per richieste, importi e tempi.

## 3. Scelte architetturali e schema a stella

Per realizzare il data warehouse è stato adottato SQLite, sistema relazionale leggero che conserva l'intero archivio in un singolo file. La struttura è organizzata secondo uno **schema a stella**, con una tabella centrale dei fatti (`fact_richieste`) e quattro dimensioni (`dim_cliente`, `dim_fornitore`, `dim_operatore`, `dim_tempo`). Il livello di dettaglio della tabella dei fatti corrisponde a una singola richiesta. Le misure registrate sono l'importo, il tempo di erogazione e l'entità dell'eventuale ritardo; gli attributi descrittivi sono conservati nelle dimensioni collegate.

La scelta dello schema a stella evita un modello inutilmente complesso e rende più immediate le aggregazioni richieste. Le chiavi surrogate presenti nelle dimensioni vengono utilizzate per i collegamenti, mentre il database applica vincoli di chiave esterna e controlli di integrità. La dimensione del tempo raggruppa le date delle richieste e ne espone anno, mese, trimestre e giorno della settimana; la singola ora rimane disponibile nel fatto.

## 4. Procedura di caricamento ETL

La procedura ETL è sviluppata in Python e suddivisa in estrazione, trasformazione e caricamento. Nella prima fase il programma legge i quattro file CSV. Nella seconda normalizza gli spazi nei campi testuali, uniforma zone e categorie, interpreta date e importi, verifica che gli identificativi di origine siano esistenti e controlla la compatibilità tra le relazioni. In particolare, una richiesta annullata non genera incassi e non possiede un tempo di erogazione. Una richiesta completata, invece, deve indicare il tempo necessario per svolgere il servizio.

Nella terza fase viene creato il database con la struttura descritta e sono inserite prima le dimensioni, poi le richieste. Il caricamento avviene in un file temporaneo: soltanto dopo il completamento dei controlli il programma sostituisce l'archivio precedente. Tale soluzione riduce il rischio di lasciare un database parzialmente caricato. I controlli automatici verificano consistenza delle chiavi, volumi delle tabelle, stati delle richieste, coerenza tra zone e categorie, assenza di campi personali e riproducibilità dei CSV.

## 5. Dashboard e indicatori

La dashboard è sviluppata in Streamlit e interroga direttamente il database SQLite. L'interfaccia presenta richieste totali, incassi relativi ai servizi completati, tempo medio di erogazione e clienti attivi. Sono inoltre visualizzati la percentuale di clienti che hanno richiesto almeno due servizi completati, il numero di richieste annullate e il numero di servizi erogati in ritardo.

La schermata comprende un grafico dell'andamento delle richieste per mese o giorno, una classifica dei primi cinque fornitori per incassi, una distribuzione delle richieste per zona e una per categoria di servizio. Filtri simultanei per intervallo temporale, zona e categoria permettono di aggiornare tutte le analisi. Gli incassi sono calcolati soltanto sulle richieste completate, mentre le richieste totali includono anche le annullate. I clienti attivi sono distinti e comprendono chi ha almeno una richiesta completata nel periodo selezionato.

## 6. Risultati della simulazione

I risultati seguenti sono stati calcolati interrogando il database SQLite effettivamente prodotto dal generatore con seme `20261115`, senza filtri, sul periodo **1 gennaio–31 ottobre 2026**.

| Indicatore | Risultato |
|:--|--:|
| Richieste totali | 550 |
| Richieste completate | 497 |
| Richieste annullate | 53 |
| Incassi da servizi completati | € 24.469,55 |
| Tempo medio di erogazione | 82,4 minuti |
| Clienti attivi | 245 |
| Clienti con almeno 2 richieste completate | 119 |
| Percentuale clienti che ritornano | 48,6% |
| Servizi completati in ritardo | 117 |

**Prima osservazione.** La zona Centro presenta il volume più elevato, con **146 richieste**, seguita dalla zona Nord con **139 richieste**. La distribuzione non è uniforme e suggerisce come la segmentazione territoriale sia utile a identificare aree con diversa intensità della domanda. Trattandosi di dati inventati, queste differenze non descrivono un mercato reale.

**Seconda osservazione.** La categoria «Consegne» ha il maggior numero di richieste (**170**), ma non il maggior ammontare di incassi. La categoria «Manutenzione», con **95 richieste**, genera **€ 8.092,04**, contro **€ 2.805,21** delle consegne. Il confronto mostra la necessità di considerare insieme volumi e valore economico, poiché le categorie simulate presentano importi medi differenti.

**Terza osservazione.** Tra i **245 clienti attivi**, **119** hanno effettuato almeno due richieste completate, corrispondenti al **48,6%**. La percentuale è coerente con il comportamento di ripetizione introdotto intenzionalmente nel generatore. Non costituisce quindi una stima empirica della fidelizzazione di una startup reale.

### Schermate da inserire nel documento finale

Per documentare i risultati, inserire **schermate autentiche ottenute dall'app Streamlit in esecuzione**:

**Figura 1.** Dashboard — indicatori principali e filtri interattivi (schermata da acquisire).

**Figura 2.** Dashboard — andamento temporale e primi cinque fornitori per incassi (schermata da acquisire).

**Figura 3 (facoltativa).** Dashboard — distribuzione delle richieste per zona e categoria (schermata da acquisire).

Le schermate non sono incluse in questa versione perché richiedono l'esecuzione dell'interfaccia grafica nell'ambiente di destinazione; non sostituirle con immagini simulate.

## 7. Limiti e sviluppi futuri

Il primo limite è l'origine completamente sintetica dei dati. Le distribuzioni di domanda, gli importi e i ritardi dipendono dalle ipotesi presenti nel generatore; i risultati dimostrano il funzionamento delle elaborazioni ma non possono essere utilizzati per formulare valutazioni di mercato. Un secondo limite è l'assenza di una gestione dello storico delle modifiche nelle dimensioni. Se un fornitore modificasse categoria o zona, una futura estensione dovrebbe conservarne le versioni storiche, per esempio attraverso una strategia Slowly Changing Dimension di tipo 2. Il caricamento, inoltre, avviene interamente da zero: un'applicazione reale richiederebbe aggiornamenti incrementali, controlli più approfonditi sui duplicati e strumenti di monitoraggio della qualità.

L'impostazione minimale consente di illustrare con chiarezza ogni passaggio dell'elaborazione. La pipeline può essere ricostruita tramite un singolo comando e l'analisi può essere ripetuta senza connettersi a servizi remoti, rendendo visibili i passaggi tra dati sorgente, modello a stella, interrogazioni SQL e rappresentazione grafica.

## 8. Istruzioni di riproduzione

Dopo aver installato Python 3.11–3.15, estrarre il progetto e installare le dipendenze riportate in `requirements.txt`. Eseguire `python prepare.py` per rigenerare i file CSV e il database, quindi `python -m streamlit run app.py` per visualizzare la dashboard nel browser. La guida completa si trova nel file `README.md`. Il controllo indipendente degli indicatori è possibile con `python check_project.py` e con le interrogazioni presenti in `sql/queries.sql`. La suite `python -m unittest discover -s tests -v` verifica dieci proprietà della pipeline.
