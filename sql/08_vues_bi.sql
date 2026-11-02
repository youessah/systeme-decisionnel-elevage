-- ============================================================================
-- VUES POUR POWER BI (schema bi)
-- A executer APRES le chargement de l'entrepot (04_faits.sql) ; a relancer apres un 99_reset_dwh.sql.
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS bi;

-- ----------------------------------------------------------------------------
-- Indicateur 3 : COUVERTURE VACCINALE des ruminants
--   couverture = animaux a jour du vaccin / animaux eligibles, par exploitation, vaccin et mois.
--   * animaux eligibles : effectif de fin de mois (fact_cheptel) des especes visees par le vaccin
--     (vaccins avec rappel uniquement : la brucellose, dose unique, est exclue) ;
--   * animal a jour : il a recu une dose non supprimee dont la date + intervalle de rappel + 30 jours
--     de tolerance couvre la fin du mois.
--   Limites : un animal vendu apres sa vaccination reste compte « a jour » (pas de table animal dans
--   l'entrepot) ; le resultat est plafonne a 100 %. La vue regroupe par id_exploitation (cle naturelle),
--   donc elle ne depend pas de la version SCD2 de l'exploitation ; exploitation_sk est celui de la
--   version courante, pour la relation avec dim_exploitation dans Power BI.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW bi.v_couverture_vaccinale AS
WITH mois AS (
    SELECT DISTINCT
           date_trunc('month', d.date_jour)::date AS mois_debut,
           (date_trunc('month', d.date_jour) + INTERVAL '1 month')::date - 1 AS mois_fin
    FROM dwh.fact_cheptel c
    JOIN dwh.dim_date d ON d.date_sk = c.date_sk
),
eligibles AS (
    SELECT date_trunc('month', d.date_jour)::date AS mois_debut,
           x.id_exploitation,
           v.vaccin_sk,
           SUM(c.effectif_fin) AS animaux_eligibles
    FROM dwh.fact_cheptel c
    JOIN dwh.dim_date d          ON d.date_sk = c.date_sk
    JOIN dwh.dim_exploitation x  ON x.exploitation_sk = c.exploitation_sk
    JOIN dwh.dim_espece_race e   ON e.espece_race_sk = c.espece_race_sk
    JOIN dwh.dim_vaccin v        ON v.rappel_jours IS NOT NULL
                                AND v.especes_cibles LIKE '%' || e.espece || '%'
    WHERE e.espece IN ('Bovins', 'Ovins', 'Caprins')
    GROUP BY 1, 2, 3
),
doses AS (
    SELECT x.id_exploitation,
           f.vaccin_sk,
           f.id_animal,
           d.date_jour AS date_dose,
           d.date_jour + (v.rappel_jours + 30) AS valide_jusqu_au
    FROM dwh.fact_vaccination f
    JOIN dwh.dim_date d          ON d.date_sk = f.date_sk
    JOIN dwh.dim_exploitation x  ON x.exploitation_sk = f.exploitation_sk
    JOIN dwh.dim_vaccin v        ON v.vaccin_sk = f.vaccin_sk
    WHERE f.id_animal IS NOT NULL
      AND NOT f.est_supprime
      AND v.rappel_jours IS NOT NULL
),
a_jour AS (
    SELECT m.mois_debut, o.id_exploitation, o.vaccin_sk,
           COUNT(DISTINCT o.id_animal) AS animaux_a_jour
    FROM mois m
    JOIN doses o ON m.mois_fin BETWEEN o.date_dose AND o.valide_jusqu_au
    GROUP BY 1, 2, 3
)
SELECT e.mois_debut,
       e.id_exploitation,
       cur.exploitation_sk,
       e.vaccin_sk,
       vc.code_vaccin,
       vc.libelle AS vaccin,
       e.animaux_eligibles,
       LEAST(COALESCE(a.animaux_a_jour, 0), e.animaux_eligibles) AS animaux_a_jour,
       ROUND(100.0 * LEAST(COALESCE(a.animaux_a_jour, 0), e.animaux_eligibles) / NULLIF(e.animaux_eligibles, 0), 1) AS couverture_pct
FROM eligibles e
LEFT JOIN a_jour a
       ON a.mois_debut = e.mois_debut AND a.id_exploitation = e.id_exploitation AND a.vaccin_sk = e.vaccin_sk
JOIN dwh.dim_vaccin vc       ON vc.vaccin_sk = e.vaccin_sk
JOIN dwh.dim_exploitation cur ON cur.id_exploitation = e.id_exploitation AND cur.est_courant
WHERE e.animaux_eligibles > 0;

COMMENT ON VIEW bi.v_couverture_vaccinale IS 'Indicateur 3 : couverture vaccinale des ruminants par exploitation, vaccin et mois';
