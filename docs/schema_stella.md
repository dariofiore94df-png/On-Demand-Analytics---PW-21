# Modello dimensionale: schema a stella

**Grana del fatto:** una riga corrisponde a una richiesta di servizio, identificata da `richiesta_id`.

```mermaid
flowchart TB
    C["dim_cliente\ncliente_key PK\ncliente_id\nzona\ndata_iscrizione"]
    F["dim_fornitore\nfornitore_key PK\nfornitore_id\nnome\ncategoria\nzona"]
    O["dim_operatore\noperatore_key PK\noperatore_id\nzona\ntipo_attivita"]
    T["dim_tempo\ntempo_key PK\ndata\nanno, mese, trimestre\ngiorno_settimana"]
    R["fact_richieste\nrichiesta_id PK\ncliente_key FK\nfornitore_key FK\noperatore_key FK\ntempo_key FK\ntimestamp_richiesta\nzona_servizio\nimporto_eur\ntempo_erogazione_min\nstato, ritardo_min, in_ritardo"]
    C --- R
    F --- R
    O --- R
    T --- R
```

Ciascuna delle quattro dimensioni ha una relazione **1 a molti** con la tabella centrale: un cliente, un fornitore, un operatore o una data possono essere associati a più richieste; ciascuna richiesta punta a una sola riga di ognuna delle quattro dimensioni.

## Perché uno schema a stella?

Semplifica le interrogazioni analitiche, separa le misure quantitative (`importo_eur`, `tempo_erogazione_min`) dagli attributi descrittivi (cliente, fornitore, operatore, tempo) ed evita di ripetere tutte le informazioni di questi soggetti in ogni richiesta. Per una dimostrazione con SQLite e poche centinaia di record è leggibile e sufficiente.

**Distinzione importante:** le colonne `cliente_id`, `fornitore_id`, `operatore_id` rappresentano identificativi fittizi generati dal programma e non permettono di identificare persone reali.
