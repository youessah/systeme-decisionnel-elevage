-- ============================================================================
-- CONTROLE DU STAGING : nombre de lignes par table, compare aux volumes attendus
-- A lancer apres j_master_staging :  psql -U postgres -d dwh_elevage -f sql/90_controle_staging.sql
-- Les volumes attendus sont ceux des fichiers sources (defauts volontaires inclus : le staging est brut).
-- ============================================================================
WITH attendu(table_stg, n) AS (VALUES
    ('stg_faostat_elevage', 40),
    ('stg_faostat_prix', 4561),
    ('stg_taux_change', 755),
    ('stg_ndvi', 59296),
    ('stg_meteo_horaire', 157824),
    ('stg_abattage', 2809),
    ('stg_vente', 6662),
    ('stg_releve_prix', 3768),
    ('stg_alimentation', 110437),
    ('stg_ref_especes', 4),
    ('stg_ref_races', 11),
    ('stg_ref_maladies', 9),
    ('stg_ref_vaccins', 7),
    ('stg_ref_lieux', 6),
    ('stg_ref_marches', 6),
    ('stg_ref_destinations', 7),
    ('stg_exploitation', 200),
    ('stg_animal', 35292),
    ('stg_lot_volaille', 725),
    ('stg_suivi_lot_semaine', 11683),
    ('stg_vaccin', 7),
    ('stg_vaccination', 151413),
    ('stg_production', 136258),
    ('stg_mouvement', 8152),
    ('stg_collier', 300),
    ('stg_gps', 395947),
    ('stg_veterinaire', 24),
    ('stg_intervention', 2390),
    ('stg_wahis', 537)
),
reel AS (
    SELECT 'stg_faostat_elevage' AS table_stg, count(*) AS n FROM staging.stg_faostat_elevage
    UNION ALL SELECT 'stg_faostat_prix' AS table_stg, count(*) AS n FROM staging.stg_faostat_prix
    UNION ALL SELECT 'stg_taux_change' AS table_stg, count(*) AS n FROM staging.stg_taux_change
    UNION ALL SELECT 'stg_ndvi' AS table_stg, count(*) AS n FROM staging.stg_ndvi
    UNION ALL SELECT 'stg_meteo_horaire' AS table_stg, count(*) AS n FROM staging.stg_meteo_horaire
    UNION ALL SELECT 'stg_abattage' AS table_stg, count(*) AS n FROM staging.stg_abattage
    UNION ALL SELECT 'stg_vente' AS table_stg, count(*) AS n FROM staging.stg_vente
    UNION ALL SELECT 'stg_releve_prix' AS table_stg, count(*) AS n FROM staging.stg_releve_prix
    UNION ALL SELECT 'stg_alimentation' AS table_stg, count(*) AS n FROM staging.stg_alimentation
    UNION ALL SELECT 'stg_ref_especes' AS table_stg, count(*) AS n FROM staging.stg_ref_especes
    UNION ALL SELECT 'stg_ref_races' AS table_stg, count(*) AS n FROM staging.stg_ref_races
    UNION ALL SELECT 'stg_ref_maladies' AS table_stg, count(*) AS n FROM staging.stg_ref_maladies
    UNION ALL SELECT 'stg_ref_vaccins' AS table_stg, count(*) AS n FROM staging.stg_ref_vaccins
    UNION ALL SELECT 'stg_ref_lieux' AS table_stg, count(*) AS n FROM staging.stg_ref_lieux
    UNION ALL SELECT 'stg_ref_marches' AS table_stg, count(*) AS n FROM staging.stg_ref_marches
    UNION ALL SELECT 'stg_ref_destinations' AS table_stg, count(*) AS n FROM staging.stg_ref_destinations
    UNION ALL SELECT 'stg_exploitation' AS table_stg, count(*) AS n FROM staging.stg_exploitation
    UNION ALL SELECT 'stg_animal' AS table_stg, count(*) AS n FROM staging.stg_animal
    UNION ALL SELECT 'stg_lot_volaille' AS table_stg, count(*) AS n FROM staging.stg_lot_volaille
    UNION ALL SELECT 'stg_suivi_lot_semaine' AS table_stg, count(*) AS n FROM staging.stg_suivi_lot_semaine
    UNION ALL SELECT 'stg_vaccin' AS table_stg, count(*) AS n FROM staging.stg_vaccin
    UNION ALL SELECT 'stg_vaccination' AS table_stg, count(*) AS n FROM staging.stg_vaccination
    UNION ALL SELECT 'stg_production' AS table_stg, count(*) AS n FROM staging.stg_production
    UNION ALL SELECT 'stg_mouvement' AS table_stg, count(*) AS n FROM staging.stg_mouvement
    UNION ALL SELECT 'stg_collier' AS table_stg, count(*) AS n FROM staging.stg_collier
    UNION ALL SELECT 'stg_gps' AS table_stg, count(*) AS n FROM staging.stg_gps
    UNION ALL SELECT 'stg_veterinaire' AS table_stg, count(*) AS n FROM staging.stg_veterinaire
    UNION ALL SELECT 'stg_intervention' AS table_stg, count(*) AS n FROM staging.stg_intervention
    UNION ALL SELECT 'stg_wahis' AS table_stg, count(*) AS n FROM staging.stg_wahis
)
SELECT a.table_stg,
       a.n AS attendu,
       r.n AS reel,
       CASE WHEN a.n = r.n THEN 'OK' ELSE 'ECART' END AS verdict
FROM attendu a
JOIN reel r ON r.table_stg = a.table_stg
ORDER BY (CASE WHEN a.n = r.n THEN 1 ELSE 0 END), a.table_stg;
