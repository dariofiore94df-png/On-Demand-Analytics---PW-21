"""Generazione riproducibile di quattro CSV interamente sintetici, senza PII."""
from __future__ import annotations

import csv
import random
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

from faker import Faker

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SEED = 20261115
ZONE = ("Centro", "Nord", "Sud", "Est", "Ovest")
CATEGORIE = (
    "Consegne", "Pulizie", "Manutenzione", "Spesa a domicilio", "Assistenza domestica"
)
PREZZO_BASE = {
    "Consegne": 19, "Pulizie": 69, "Manutenzione": 89,
    "Spesa a domicilio": 35, "Assistenza domestica": 55,
}
TEMPO_BASE = {
    "Consegne": 35, "Pulizie": 95, "Manutenzione": 110,
    "Spesa a domicilio": 60, "Assistenza domestica": 80,
}
SLA_MIN = {
    "Consegne": 55, "Pulizie": 120, "Manutenzione": 145,
    "Spesa a domicilio": 80, "Assistenza domestica": 105,
}

def genera_nomi_fornitori(seed: int, numero: int = 320) -> list[str]:
    """Denominazioni di prova da Faker it_IT, uniche e stabili a versione fissata.

    Un'istanza Faker indipendente non altera la sequenza casuale utilizzata
    per generare clienti, richieste, tempi e importi.
    """
    fake = Faker("it_IT")
    fake.seed_instance(seed)
    # Evita denominazioni troppo lunghe da leggere nel grafico orizzontale.
    nomi = []
    while len(nomi) < numero:
        nome = fake.unique.company()
        if len(nome) <= 30:
            nomi.append(nome)
    if len({nome.casefold() for nome in nomi}) != numero:
        raise ValueError("Le denominazioni dei fornitori non sono tutte distinte")
    return nomi


def export_csv(filename: str, fieldnames: list[str], rows: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR / filename).open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def choose_date(rng: random.Random) -> date:
    """Più richieste nel fine settimana, con distribuzione su 10 mesi fissi."""
    start, end = date(2026, 1, 1), date(2026, 10, 31)
    days = (end - start).days + 1
    weighted_days = [start + timedelta(days=i) for i in range(days)]
    weights = [1.8 if d.weekday() >= 5 else (1.3 if d.weekday() == 4 else 1) for d in weighted_days]
    return rng.choices(weighted_days, weights=weights, k=1)[0]


def generate(seed: int = SEED) -> dict[str, int]:
    rng = random.Random(seed)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    clienti = []
    for i in range(1, 361):
        giorno = date(2025, 4, 1) + timedelta(days=rng.randrange(270))
        clienti.append({
            "cliente_id": f"C{i:04d}",
            "zona": rng.choices(ZONE, weights=[28, 21, 17, 19, 15], k=1)[0],
            "data_iscrizione": giorno.isoformat(),
        })

    fornitori = []
    nomi_aziende = genera_nomi_fornitori(seed)
    for i in range(1, 321):
        # Zone e categorie distribuite ciclicamente, ma con ordine mescolato.
        zona, categoria = ZONE[(i - 1) % 5], CATEGORIE[((i - 1) // 5) % 5]
        nome = nomi_aziende[i - 1]
        fornitori.append({
            "fornitore_id": f"F{i:04d}",
            "nome": nome,
            "categoria": categoria,
            "zona": zona,
        })

    operatori = []
    for i in range(1, 301):
        zona, attivita = ZONE[(i - 1) % 5], CATEGORIE[((i - 1) // 5) % 5]
        operatori.append({
            "operatore_id": f"O{i:04d}",
            "zona": zona,
            "tipo_attivita": attivita,
        })

    fornitori_per_zona_categoria = defaultdict(list)
    operatori_per_zona_categoria = defaultdict(list)
    for f in fornitori:
        fornitori_per_zona_categoria[(f["zona"], f["categoria"])].append(f)
    for op in operatori:
        operatori_per_zona_categoria[(op["zona"], op["tipo_attivita"])].append(op)

    # Una parte dei clienti è più propensa a ripetere le richieste.
    popolarita_clienti = [4 if (i % 5 == 0) else 1 for i in range(len(clienti))]
    richieste = []
    for i in range(1, 551):
        cliente = rng.choices(clienti, weights=popolarita_clienti, k=1)[0]
        categoria = rng.choices(CATEGORIE, weights=[32, 19, 16, 22, 11], k=1)[0]
        zona = cliente["zona"]
        candidates_f = fornitori_per_zona_categoria[(zona, categoria)]
        candidates_o = operatori_per_zona_categoria[(zona, categoria)]
        # Alcuni partner raccolgono più prenotazioni, producendo una top 5 leggibile.
        f_weights = [5 if j < 3 else 1 for j in range(len(candidates_f))]
        fornitore = rng.choices(candidates_f, weights=f_weights, k=1)[0]
        operatore = rng.choice(candidates_o)
        giorno = choose_date(rng)
        ora = rng.choices(
            list(range(8, 23)),
            weights=[1, 1, 2, 3, 6, 7, 5, 3, 2, 3, 7, 9, 8, 5, 2],
            k=1,
        )[0]
        dt = datetime.combine(giorno, time(ora, rng.randrange(60), rng.randrange(60)))
        annullata = rng.random() < 0.085
        if annullata:
            stato, tempo, ritardo, importo = "Annullata", "", 0, 0
        else:
            stato = "Completata"
            # Su circa il 20% delle richieste completate imponiamo un ritardo.
            ritardo_previsto = rng.random() < 0.20
            if ritardo_previsto:
                tempo = SLA_MIN[categoria] + rng.randint(5, 50)
            else:
                tempo = max(8, int(rng.gauss(TEMPO_BASE[categoria], 9)))
                tempo = min(tempo, SLA_MIN[categoria])
            ritardo = max(0, tempo - SLA_MIN[categoria])
            importo = round(max(7, rng.gauss(PREZZO_BASE[categoria], PREZZO_BASE[categoria] * .21)), 2)

        # Una quota limitata presenta spazi esterni nei CSV grezzi: l'ETL li pulirà.
        zona_grezza = f" {zona} " if i % 23 == 0 else zona
        richieste.append({
            "richiesta_id": f"R{i:05d}", "cliente_id": cliente["cliente_id"],
            "fornitore_id": fornitore["fornitore_id"],
            "operatore_id": operatore["operatore_id"],
            "data_ora": dt.isoformat(timespec="seconds"),
            "zona_servizio": zona_grezza,
            "importo_eur": f"{importo:.2f}",
            "tempo_erogazione_min": tempo,
            "stato": stato, "ritardo_min": ritardo,
        })

    export_csv("clienti.csv", ["cliente_id", "zona", "data_iscrizione"], clienti)
    export_csv("fornitori.csv", ["fornitore_id", "nome", "categoria", "zona"], fornitori)
    export_csv("operatori.csv", ["operatore_id", "zona", "tipo_attivita"], operatori)
    export_csv("richieste.csv", [
        "richiesta_id", "cliente_id", "fornitore_id", "operatore_id",
        "data_ora", "zona_servizio", "importo_eur", "tempo_erogazione_min",
        "stato", "ritardo_min",
    ], richieste)
    return {"clienti": len(clienti), "fornitori": len(fornitori),
            "operatori": len(operatori), "richieste": len(richieste)}


if __name__ == "__main__":
    print("CSV generati:", generate())
