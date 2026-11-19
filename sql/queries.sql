-- Le seguenti interrogazioni SQL si possono eseguire sul file SQLite.
-- I valori riguardano l'intero archivio (senza filtri). L'app applica
-- filtri aggiuntivi a data, zona e categoria con query parametrizzate.

-- Q1. Richieste totali, incassi, tempo medio, clienti attivi
SELECT
 COUNT(*) AS richieste_totali,
 ROUND(SUM(CASE WHEN stato='Completata' THEN importo_eur ELSE 0 END),2) AS incassi_eur,
 ROUND(AVG(CASE WHEN stato='Completata' THEN tempo_erogazione_min END),1) AS tempo_medio_min,
 COUNT(DISTINCT CASE WHEN stato='Completata' THEN cliente_key END) AS clienti_attivi
FROM fact_richieste;

-- Q2. Clienti che ritornano (= almeno 2 richieste completate / clienti attivi)
WITH richieste_cliente AS (
 SELECT cliente_key, COUNT(*) AS n
 FROM fact_richieste
 WHERE stato='Completata'
 GROUP BY cliente_key
)
SELECT COUNT(*) AS clienti_attivi,
 SUM(CASE WHEN n >= 2 THEN 1 ELSE 0 END) AS clienti_ritorno,
 ROUND(100.0 * SUM(CASE WHEN n >= 2 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),1)
   AS quota_ritorno_percentuale
FROM richieste_cliente;

-- Q3. Andamento mensile
SELECT substr(t.data,1,7) AS mese, COUNT(*) AS richieste
FROM fact_richieste f JOIN dim_tempo t ON t.tempo_key=f.tempo_key
GROUP BY mese ORDER BY mese;

-- Q4. I primi 5 fornitori per incassi
SELECT v.nome, ROUND(SUM(f.importo_eur),2) AS incassi_eur
FROM fact_richieste f JOIN dim_fornitore v ON v.fornitore_key=f.fornitore_key
WHERE f.stato='Completata'
GROUP BY f.fornitore_key ORDER BY incassi_eur DESC, v.nome ASC LIMIT 5;

-- Q5. Richieste per zona
SELECT zona_servizio AS zona, COUNT(*) AS richieste
FROM fact_richieste GROUP BY zona ORDER BY richieste DESC;

-- Q6. Richieste per categoria
SELECT v.categoria, COUNT(*) AS richieste
FROM fact_richieste f JOIN dim_fornitore v ON f.fornitore_key=v.fornitore_key
GROUP BY v.categoria ORDER BY richieste DESC;

-- Q7. Richieste annullate e ritardate
SELECT stato, COUNT(*) AS richieste, SUM(in_ritardo) AS in_ritardo
FROM fact_richieste GROUP BY stato;
