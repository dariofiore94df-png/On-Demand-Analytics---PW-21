"""Verifica risultati principali senza dipendenze esterne."""
import sqlite3
from etl import DB_FILE


def main():
    with sqlite3.connect(DB_FILE) as conn:
        sql = """
            SELECT COUNT(*) AS richieste,
                   SUM(stato = 'Completata') AS completate,
                   SUM(stato = 'Annullata') AS annullate,
                   ROUND(SUM(CASE WHEN stato='Completata' THEN importo_eur ELSE 0 END),2) AS incassi,
                   ROUND(AVG(CASE WHEN stato='Completata' THEN tempo_erogazione_min END),1) AS tempo_medio,
                   COUNT(DISTINCT CASE WHEN stato='Completata' THEN cliente_key END) AS clienti_attivi,
                   SUM(in_ritardo) AS ritardi
            FROM fact_richieste;
        """
        labels = ["Richieste", "Completate", "Annullate", "Incassi EUR", "Tempo medio minuti", "Clienti attivi", "Ritardi"]
        for label, value in zip(labels, conn.execute(sql).fetchone()):
            print(f"{label:20}: {value}")
        returns = conn.execute("""
            WITH per_cliente AS (
              SELECT cliente_key, COUNT(*) AS n FROM fact_richieste
              WHERE stato='Completata' GROUP BY cliente_key
            )
            SELECT COUNT(*), SUM(n>=2), ROUND(100.0*SUM(n>=2)/COUNT(*),1)
            FROM per_cliente
        """).fetchone()
        print("Clienti attivi / ritorno / %:", returns)
        print("Controllo chiavi esterne:", conn.execute("PRAGMA foreign_key_check").fetchall())


if __name__ == "__main__":
    main()
