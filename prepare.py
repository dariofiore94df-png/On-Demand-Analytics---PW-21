"""Una sola operazione riproduce CSV, schema a stella e database SQLite."""
from generate_data import generate
from etl import build

if __name__ == "__main__":
    print("1/2 Generazione dei dati sintetici (seed fisso)...")
    print(generate())
    print("2/2 Pulizia, validazione e caricamento nel data warehouse...")
    print(build())
    print("Preparazione completata. Avvia con: python -m streamlit run app.py")
