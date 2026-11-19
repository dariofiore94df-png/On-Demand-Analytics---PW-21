"""Dashboard locale Streamlit: legge solo il data warehouse SQLite."""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "warehouse" / "startup_on_demand.sqlite"

st.set_page_config(
    page_title="OnDemand Analytics",
    page_icon="📊", layout="wide", initial_sidebar_state="expanded"
)

st.title("OnDemand Analytics", anchor=False)

if not DB_FILE.is_file():
    st.error("Archivio SQLite non trovato. Esegui prima **python prepare.py** nella cartella del progetto.")
    st.stop()


def read_sql(sql: str, parameters: list | tuple = ()) -> pd.DataFrame:
    # Connessione di sola lettura: l'app non modifica né genera dati.
    with sqlite3.connect(f"file:{DB_FILE.as_posix()}?mode=ro", uri=True) as conn:
        return pd.read_sql_query(sql, conn, params=parameters)


minmax = read_sql("SELECT MIN(data) AS inizio, MAX(data) AS fine FROM dim_tempo").iloc[0]
min_date, max_date = date.fromisoformat(minmax["inizio"]), date.fromisoformat(minmax["fine"])
zone = read_sql("SELECT DISTINCT zona_servizio FROM fact_richieste ORDER BY zona_servizio")["zona_servizio"].tolist()
categorie = read_sql("SELECT DISTINCT categoria FROM dim_fornitore ORDER BY categoria")["categoria"].tolist()

st.sidebar.header("Filtri di analisi", anchor=False)
periodo = st.sidebar.date_input(
    "Periodo", value=(min_date, max_date), min_value=min_date, max_value=max_date,
    format="DD/MM/YYYY",
)
zona = st.sidebar.selectbox("Zona", ["Tutte", *zone])
categoria = st.sidebar.selectbox("Categoria di servizio", ["Tutte", *categorie])
raggruppamento = st.sidebar.radio("Andamento nel tempo", ["Mensile", "Giornaliero"], horizontal=True)

if not isinstance(periodo, (list, tuple)) or len(periodo) != 2:
    st.warning("Seleziona la data iniziale e quella finale del periodo.")
    st.stop()
inizio, fine = periodo
if inizio > fine:
    st.warning("La data iniziale non può essere successiva a quella finale.")
    st.stop()

where_parts = ["t.data BETWEEN ? AND ?"]
params = [inizio.isoformat(), fine.isoformat()]
if zona != "Tutte":
    where_parts.append("f.zona_servizio = ?")
    params.append(zona)
if categoria != "Tutte":
    where_parts.append("v.categoria = ?")
    params.append(categoria)

# La medesima base filtrata alimenta KPI e grafici: nessun filtro disallineato.
filtered = f"""
    WITH filtrate AS (
        SELECT f.richiesta_id, f.cliente_key, f.fornitore_key,
               f.zona_servizio, f.importo_eur, f.tempo_erogazione_min,
               f.stato, f.in_ritardo, t.data, v.nome AS fornitore,
               v.categoria
        FROM fact_richieste AS f
        JOIN dim_tempo AS t ON t.tempo_key = f.tempo_key
        JOIN dim_fornitore AS v ON v.fornitore_key = f.fornitore_key
        WHERE {' AND '.join(where_parts)}
    )
"""

kpi = read_sql(filtered + """
    SELECT COUNT(*) AS richieste,
           COALESCE(SUM(CASE WHEN stato = 'Completata' THEN importo_eur ELSE 0 END),0) AS incassi,
           AVG(CASE WHEN stato = 'Completata' THEN tempo_erogazione_min END) AS tempo_medio,
           COUNT(DISTINCT CASE WHEN stato = 'Completata' THEN cliente_key END) AS clienti_attivi,
           SUM(CASE WHEN stato = 'Annullata' THEN 1 ELSE 0 END) AS annullate,
           SUM(CASE WHEN stato = 'Completata' THEN in_ritardo ELSE 0 END) AS ritardi,
           SUM(CASE WHEN stato = 'Completata' THEN 1 ELSE 0 END) AS completate
    FROM filtrate
""", params).iloc[0]

ritorno = read_sql(filtered + """
    ,per_cliente AS (
        SELECT cliente_key, COUNT(*) AS n
        FROM filtrate WHERE stato = 'Completata'
        GROUP BY cliente_key
    )
    SELECT COUNT(*) AS clienti_con_richieste_completate,
           COALESCE(SUM(CASE WHEN n >= 2 THEN 1 ELSE 0 END),0) AS clienti_ritorno,
           COALESCE(ROUND(100.0 * SUM(CASE WHEN n >= 2 THEN 1 ELSE 0 END)
                          / NULLIF(COUNT(*), 0), 1),0) AS pct_ritorno
    FROM per_cliente
""", params).iloc[0]


def euro(value: float) -> str:
    return "€ " + f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


st.subheader("Indicatori principali", anchor=False)
# Prima riga: tre indicatori; seconda riga: gli altri quattro.
a, b, c = st.columns(3)
a.metric("Richieste totali", f"{int(kpi['richieste']):,}".replace(",", "."))
b.metric("Incassi da servizi completati", euro(kpi["incassi"]))
c.metric("Tempo medio di erogazione", "—" if pd.isna(kpi["tempo_medio"]) else f"{kpi['tempo_medio']:.1f} min")

d, e, f, g = st.columns(4)
d.metric("Clienti attivi", str(int(kpi["clienti_attivi"])))
e.metric("Clienti che ritornano", f"{float(ritorno['pct_ritorno']):.1f}%")
f.metric("Richieste annullate", str(int(kpi["annullate"])))
g.metric("Servizi completati in ritardo", str(int(kpi["ritardi"])))

st.caption(
    "Definizioni: incassi = somma degli importi delle richieste completate; "
    "tempo medio = media dei minuti delle richieste completate; "
    "clienti attivi = clienti con almeno una richiesta completata nel periodo; "
    "clienti che ritornano = quota di clienti attivi con almeno due richieste completate "
    "nella selezione corrente."
)

if int(kpi["richieste"]) == 0:
    st.warning("Nessuna richiesta corrisponde ai filtri selezionati.")
    st.stop()

st.divider()
col_left, col_right = st.columns([1.35, 1])
with col_left:
    st.subheader("Andamento delle richieste", anchor=False)
    bucket = "substr(data,1,7)" if raggruppamento == "Mensile" else "data"
    andamento = read_sql(filtered + f"""
        SELECT {bucket} AS Periodo, COUNT(*) AS Richieste
        FROM filtrate GROUP BY {bucket} ORDER BY {bucket}
    """, params)
    st.line_chart(andamento, x="Periodo", y="Richieste", height=310)

with col_right:
    st.subheader("I 5 fornitori con più incassi", anchor=False)
    top = read_sql(filtered + """
        SELECT fornitore AS Fornitore,
               ROUND(SUM(importo_eur),2) AS Incassi_EUR
        FROM filtrate WHERE stato='Completata'
        GROUP BY fornitore_key, fornitore
        ORDER BY Incassi_EUR DESC, fornitore ASC LIMIT 5
    """, params)
    if len(top):
        top_chart = (
            alt.Chart(top)
            .mark_bar()
            .encode(
                x=alt.X("Incassi_EUR:Q", title="Incassi (EUR)"),
                y=alt.Y("Fornitore:N", sort="-x", title="Fornitore", axis=alt.Axis(labelLimit=320)),
                tooltip=[
                    alt.Tooltip("Fornitore:N", title="Fornitore"),
                    alt.Tooltip("Incassi_EUR:Q", title="Incassi (EUR)", format=",.2f"),
                ],
            )
            .properties(height=310)
        )
        st.altair_chart(top_chart, use_container_width=True)
    else:
        st.info("Nessun servizio completato nel periodo.")

col_zona, col_cat = st.columns(2)
with col_zona:
    st.subheader("Richieste per zona", anchor=False)
    per_zona = read_sql(filtered + """
        SELECT zona_servizio AS Zona, COUNT(*) AS Richieste
        FROM filtrate GROUP BY zona_servizio ORDER BY Richieste DESC
    """, params)
    st.bar_chart(per_zona, x="Zona", y="Richieste", height=290)
with col_cat:
    st.subheader("Richieste per categoria", anchor=False)
    per_categoria = read_sql(filtered + """
        SELECT categoria AS Categoria, COUNT(*) AS Richieste
        FROM filtrate GROUP BY categoria ORDER BY Richieste DESC
    """, params)
    categoria_chart = (
        alt.Chart(per_categoria)
        .mark_bar()
        .encode(
            x=alt.X("Richieste:Q", title="Richieste"),
            y=alt.Y("Categoria:N", sort="-x", title="Categoria", axis=alt.Axis(labelLimit=260)),
            tooltip=[
                alt.Tooltip("Categoria:N", title="Categoria"),
                alt.Tooltip("Richieste:Q", title="Richieste"),
            ],
        )
        .properties(height=290)
    )
    st.altair_chart(categoria_chart, use_container_width=True)

with st.expander("Visualizza tabella di dettaglio ed esporta le analisi"):
    riepilogo = read_sql(filtered + """
        SELECT substr(data,1,7) AS Mese, zona_servizio AS Zona,
               categoria AS Categoria, COUNT(*) AS Richieste,
               ROUND(SUM(CASE WHEN stato='Completata' THEN importo_eur ELSE 0 END),2) AS Incassi_EUR
        FROM filtrate GROUP BY Mese,Zona,Categoria ORDER BY Mese,Zona,Categoria
    """, params)
    st.dataframe(riepilogo, use_container_width=True, hide_index=True)
    st.download_button(
        "Esporta riepilogo CSV", riepilogo.to_csv(index=False).encode("utf-8-sig"),
        file_name="riepilogo_on_demand.csv", mime="text/csv",
    )

st.caption("Database: SQLite locale · Schema a stella · Pipeline ETL in Python · Dataset sintetico riproducibile")
