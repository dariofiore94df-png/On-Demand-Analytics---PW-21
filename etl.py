"""ETL CSV -> SQLite con controlli e caricamento atomico."""
from __future__ import annotations

import csv
import os
import re
import sqlite3
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from generate_data import CATEGORIE, DATA_DIR, ZONE

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "warehouse" / "startup_on_demand.sqlite"
SCHEMA_FILE = BASE_DIR / "sql" / "schema.sql"
ZONE_CANONICHE = {x.casefold(): x for x in ZONE}
CATEGORIE_CANONICHE = {x.casefold(): x for x in CATEGORIE}


def pulisci(valore: str) -> str:
    return re.sub(r"\s+", " ", valore.strip())


def categoria_norm(valore: str) -> str:
    v = pulisci(valore)
    if v.casefold() not in CATEGORIE_CANONICHE:
        raise ValueError(f"Categoria sconosciuta: {valore!r}")
    return CATEGORIE_CANONICHE[v.casefold()]


def zona_norm(valore: str) -> str:
    v = pulisci(valore)
    if v.casefold() not in ZONE_CANONICHE:
        raise ValueError(f"Zona sconosciuta: {valore!r}")
    return ZONE_CANONICHE[v.casefold()]


def leggi_csv(nome_file: str) -> list[dict[str, str]]:
    with (DATA_DIR / nome_file).open(newline="", encoding="utf-8-sig") as file:
        righe = list(csv.DictReader(file))
    if not righe:
        raise ValueError(f"File CSV vuoto: {nome_file}")
    return righe


def importo_decimal(valore: str) -> Decimal:
    try:
        n = Decimal(pulisci(valore))
    except InvalidOperation as exc:
        raise ValueError(f"Importo non valido: {valore!r}") from exc
    if not n.is_finite() or n < 0 or n.as_tuple().exponent < -2:
        raise ValueError(f"Importo negativo, non finito o con più di 2 decimali: {valore!r}")
    return n


def build(db_path: Path = DB_FILE) -> dict[str, int]:
    """Ricrea il database senza duplicazioni e sostituisce il vecchio solo se valido."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = db_path.with_suffix(".tmp.sqlite")
    if temp_path.exists():
        temp_path.unlink()
    conn = sqlite3.connect(temp_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
        with conn:
            clienti = leggi_csv("clienti.csv")
            for r in clienti:
                data_iscrizione = date.fromisoformat(pulisci(r["data_iscrizione"]))
                conn.execute(
                    "INSERT INTO dim_cliente (cliente_id,zona,data_iscrizione) VALUES (?,?,?)",
                    (pulisci(r["cliente_id"]), zona_norm(r["zona"]), data_iscrizione.isoformat()),
                )

            fornitori = leggi_csv("fornitori.csv")
            for r in fornitori:
                conn.execute(
                    "INSERT INTO dim_fornitore (fornitore_id,nome,categoria,zona) VALUES (?,?,?,?)",
                    (pulisci(r["fornitore_id"]), pulisci(r["nome"]),
                     categoria_norm(r["categoria"]), zona_norm(r["zona"])),
                )

            operatori = leggi_csv("operatori.csv")
            for r in operatori:
                conn.execute(
                    "INSERT INTO dim_operatore (operatore_id,zona,tipo_attivita) VALUES (?,?,?)",
                    (pulisci(r["operatore_id"]), zona_norm(r["zona"]),
                     categoria_norm(r["tipo_attivita"])),
                )

            ids_clienti = dict(conn.execute("SELECT cliente_id,cliente_key FROM dim_cliente"))
            ids_fornitori = dict(conn.execute("SELECT fornitore_id,fornitore_key FROM dim_fornitore"))
            ids_operatori = dict(conn.execute("SELECT operatore_id,operatore_key FROM dim_operatore"))
            dim_clienti = {
                r[0]: (r[1], r[2]) for r in conn.execute(
                    "SELECT cliente_id,zona,data_iscrizione FROM dim_cliente"
                )
            }
            dim_fornitori = {
                r[0]: (r[1], r[2]) for r in conn.execute(
                    "SELECT fornitore_id,zona,categoria FROM dim_fornitore"
                )
            }
            dim_operatori = {
                r[0]: (r[1], r[2]) for r in conn.execute(
                    "SELECT operatore_id,zona,tipo_attivita FROM dim_operatore"
                )
            }

            richieste = leggi_csv("richieste.csv")
            for r in richieste:
                id_c, id_f, id_o = (pulisci(r[x]) for x in
                    ("cliente_id", "fornitore_id", "operatore_id"))
                if id_c not in ids_clienti or id_f not in ids_fornitori or id_o not in ids_operatori:
                    raise ValueError(f"Riferimento inesistente nella richiesta {r['richiesta_id']}")
                timestamp = datetime.fromisoformat(pulisci(r["data_ora"]))
                data = timestamp.date()
                zona = zona_norm(r["zona_servizio"])
                cat = dim_fornitori[id_f][1]
                if not (
                    dim_clienti[id_c][0] == dim_fornitori[id_f][0]
                    == dim_operatori[id_o][0] == zona
                ):
                    raise ValueError(f"Incoerenza zone nella richiesta {r['richiesta_id']}")
                if dim_operatori[id_o][1] != cat:
                    raise ValueError(f"Incoerenza categoria nella richiesta {r['richiesta_id']}")
                if data < date.fromisoformat(dim_clienti[id_c][1]):
                    raise ValueError(f"Richiesta antecedente all'iscrizione: {r['richiesta_id']}")
                amount = importo_decimal(r["importo_eur"])
                state = pulisci(r["stato"])
                if state not in {"Completata", "Annullata"}:
                    raise ValueError(f"Stato sconosciuto nella richiesta {r['richiesta_id']}")
                temp = int(pulisci(r["tempo_erogazione_min"])) if pulisci(r["tempo_erogazione_min"]) else None
                ritardo = int(pulisci(r["ritardo_min"]))
                if ritardo < 0 or (temp is not None and ritardo > temp):
                    raise ValueError(f"Ritardo non valido nella richiesta {r['richiesta_id']}")
                if state == "Annullata" and (amount != 0 or temp is not None or ritardo != 0):
                    raise ValueError("Le richieste annullate non devono generare ricavi né tempi")
                if state == "Completata" and temp is None:
                    raise ValueError("Il tempo di erogazione è obbligatorio per le richieste completate")

                time_key = int(data.strftime("%Y%m%d"))
                conn.execute(
                    """INSERT OR IGNORE INTO dim_tempo
                       (tempo_key,data,anno,mese,trimestre,giorno_settimana,fine_settimana)
                       VALUES (?,?,?,?,?,?,?)""",
                    (time_key, data.isoformat(), data.year, data.month,
                     (data.month - 1) // 3 + 1, data.weekday(), int(data.weekday() >= 5)),
                )
                conn.execute(
                    """INSERT INTO fact_richieste
                       (richiesta_id,cliente_key,fornitore_key,operatore_key,tempo_key,
                        timestamp_richiesta,zona_servizio,importo_eur,tempo_erogazione_min,
                        stato,ritardo_min,in_ritardo)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (pulisci(r["richiesta_id"]), ids_clienti[id_c], ids_fornitori[id_f],
                     ids_operatori[id_o], time_key, timestamp.isoformat(timespec="seconds"),
                     zona, str(amount), temp, state, ritardo, int(ritardo > 0)),
                )

            errors = conn.execute("PRAGMA foreign_key_check").fetchall()
            if errors:
                raise ValueError(f"Vincoli esterni violati: {errors}")
            ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if ok != "ok":
                raise ValueError(f"Integrità SQLite: {ok}")
        counts = {
            "dim_cliente": len(clienti), "dim_fornitore": len(fornitori),
            "dim_operatore": len(operatori), "fact_richieste": len(richieste),
            "dim_tempo": conn.execute("SELECT COUNT(*) FROM dim_tempo").fetchone()[0],
        }
    except Exception:
        conn.close()
        temp_path.unlink(missing_ok=True)
        raise
    else:
        conn.close()
        os.replace(temp_path, db_path)
        return counts


if __name__ == "__main__":
    print("Database creato:", build())
