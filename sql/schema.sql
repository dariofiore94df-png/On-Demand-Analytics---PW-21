PRAGMA foreign_keys = ON;

-- Data warehouse a stella: la granularità della tabella centrale è una richiesta.
CREATE TABLE dim_cliente (
    cliente_key INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id TEXT NOT NULL UNIQUE,
    zona TEXT NOT NULL,
    data_iscrizione TEXT NOT NULL
);

CREATE TABLE dim_fornitore (
    fornitore_key INTEGER PRIMARY KEY AUTOINCREMENT,
    fornitore_id TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    categoria TEXT NOT NULL,
    zona TEXT NOT NULL
);

CREATE TABLE dim_operatore (
    operatore_key INTEGER PRIMARY KEY AUTOINCREMENT,
    operatore_id TEXT NOT NULL UNIQUE,
    zona TEXT NOT NULL,
    tipo_attivita TEXT NOT NULL
);

CREATE TABLE dim_tempo (
    tempo_key INTEGER PRIMARY KEY,  -- YYYYMMDD
    data TEXT NOT NULL UNIQUE,      -- YYYY-MM-DD
    anno INTEGER NOT NULL,
    mese INTEGER NOT NULL,
    trimestre INTEGER NOT NULL,
    giorno_settimana INTEGER NOT NULL,
    fine_settimana INTEGER NOT NULL CHECK (fine_settimana IN (0, 1))
);

CREATE TABLE fact_richieste (
    richiesta_id TEXT PRIMARY KEY,
    cliente_key INTEGER NOT NULL,
    fornitore_key INTEGER NOT NULL,
    operatore_key INTEGER NOT NULL,
    tempo_key INTEGER NOT NULL,
    timestamp_richiesta TEXT NOT NULL,
    zona_servizio TEXT NOT NULL,
    importo_eur NUMERIC NOT NULL CHECK (importo_eur >= 0),
    tempo_erogazione_min INTEGER CHECK (tempo_erogazione_min >= 0),
    stato TEXT NOT NULL CHECK (stato IN ('Completata', 'Annullata')),
    ritardo_min INTEGER NOT NULL DEFAULT 0 CHECK (ritardo_min >= 0),
    in_ritardo INTEGER NOT NULL CHECK (in_ritardo IN (0, 1)),
    FOREIGN KEY (cliente_key) REFERENCES dim_cliente(cliente_key),
    FOREIGN KEY (fornitore_key) REFERENCES dim_fornitore(fornitore_key),
    FOREIGN KEY (operatore_key) REFERENCES dim_operatore(operatore_key),
    FOREIGN KEY (tempo_key) REFERENCES dim_tempo(tempo_key),
    CHECK (
        (stato = 'Annullata' AND importo_eur = 0 AND tempo_erogazione_min IS NULL AND in_ritardo = 0)
        OR (stato = 'Completata' AND tempo_erogazione_min IS NOT NULL)
    )
);

CREATE INDEX ix_fact_tempo ON fact_richieste(tempo_key);
CREATE INDEX ix_fact_zona ON fact_richieste(zona_servizio);
CREATE INDEX ix_fact_cliente ON fact_richieste(cliente_key);
CREATE INDEX ix_fact_fornitore ON fact_richieste(fornitore_key);
