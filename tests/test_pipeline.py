"""Eseguire con: python -m unittest discover -s tests -v"""
import csv
import hashlib
import sqlite3
import unittest
from collections import Counter
from pathlib import Path

from generate_data import DATA_DIR, generate
from etl import DB_FILE, build


class TestPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DB_FILE.exists():
            generate()
            build()
        cls.conn = sqlite3.connect(DB_FILE)
        cls.conn.execute("PRAGMA foreign_keys = ON")

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_volumi_richiesti(self):
        for tabella in ("dim_cliente", "dim_fornitore", "dim_operatore", "fact_richieste"):
            numero = self.conn.execute(f"SELECT COUNT(*) FROM {tabella}").fetchone()[0]
            self.assertGreaterEqual(numero, 300)
            self.assertLessEqual(numero, 600)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM fact_richieste").fetchone()[0], 550)

    def test_integrita_relazionale(self):
        self.assertEqual(self.conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(self.conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(self.conn.execute("SELECT COUNT(DISTINCT richiesta_id) FROM fact_richieste").fetchone()[0], 550)

    def test_richieste_complete_e_annullate(self):
        statuses = Counter(dict(self.conn.execute(
            "SELECT stato,COUNT(*) FROM fact_richieste GROUP BY stato"
        )))
        self.assertGreater(statuses["Completata"], 0)
        self.assertGreater(statuses["Annullata"], 0)
        self.assertGreater(self.conn.execute("SELECT SUM(in_ritardo) FROM fact_richieste").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("""
            SELECT COUNT(*) FROM fact_richieste
            WHERE stato = 'Annullata' AND
                 (importo_eur <> 0 OR tempo_erogazione_min IS NOT NULL OR in_ritardo <> 0)
        """).fetchone()[0], 0)

    def test_zone_e_categorie_coerenti(self):
        self.assertEqual(self.conn.execute("""
            SELECT COUNT(*) FROM fact_richieste r
            JOIN dim_cliente c ON c.cliente_key=r.cliente_key
            JOIN dim_fornitore f ON f.fornitore_key=r.fornitore_key
            JOIN dim_operatore o ON o.operatore_key=r.operatore_key
            WHERE c.zona<>r.zona_servizio OR f.zona<>r.zona_servizio
               OR o.zona<>r.zona_servizio OR f.categoria<>o.tipo_attivita
        """).fetchone()[0], 0)

    def test_periodo_e_registrazione(self):
        self.assertEqual(self.conn.execute("""
            SELECT COUNT(*) FROM fact_richieste r
            JOIN dim_tempo t ON t.tempo_key=r.tempo_key
            JOIN dim_cliente c ON c.cliente_key=r.cliente_key
            WHERE t.data < c.data_iscrizione OR t.data NOT BETWEEN '2026-01-01' AND '2026-10-31'
        """).fetchone()[0], 0)

    def test_pulizia_spazi(self):
        with (DATA_DIR / "richieste.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertTrue(any(r["zona_servizio"] != r["zona_servizio"].strip() for r in rows))
        self.assertEqual(self.conn.execute("""
            SELECT COUNT(*) FROM fact_richieste
            WHERE zona_servizio != trim(zona_servizio)
        """).fetchone()[0], 0)

    def test_dataset_riproducibile(self):
        target = DATA_DIR / "richieste.csv"
        before = hashlib.sha256(target.read_bytes()).hexdigest()
        generate()
        after = hashlib.sha256(target.read_bytes()).hexdigest()
        self.assertEqual(before, after)

    def test_nomi_fornitori_faker_univoci(self):
        from generate_data import SEED, genera_nomi_fornitori
        nomi = [row[0] for row in self.conn.execute(
            "SELECT nome FROM dim_fornitore ORDER BY fornitore_id"
        ).fetchall()]
        self.assertEqual(len(nomi), 320)
        self.assertEqual(len({nome.casefold() for nome in nomi}), 320)
        self.assertEqual(nomi, genera_nomi_fornitori(SEED))
        self.assertTrue(all(len(nome) <= 30 for nome in nomi))
        self.assertFalse(any("Partner sintetico" in nome for nome in nomi))

    def test_nomi_faker_riproducibili_e_csv_coerente(self):
        from generate_data import SEED, genera_nomi_fornitori
        expected = genera_nomi_fornitori(SEED)
        self.assertEqual(expected, genera_nomi_fornitori(SEED))
        with (DATA_DIR / "fornitori.csv").open(encoding="utf-8-sig", newline="") as handle:
            names = [row["nome"] for row in csv.DictReader(handle)]
        self.assertEqual(names, expected)

    def test_nessuna_colonna_personale(self):
        forbidden = {"email", "telefono", "indirizzo", "cognome", "data_nascita", "ip"}
        for path in DATA_DIR.glob("*.csv"):
            with path.open(encoding="utf-8-sig", newline="") as handle:
                headers = csv.DictReader(handle).fieldnames or []
            self.assertTrue(forbidden.isdisjoint(headers), path.name)


if __name__ == "__main__":
    unittest.main()
