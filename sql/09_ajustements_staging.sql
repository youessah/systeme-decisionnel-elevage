-- ============================================================================
-- AJUSTEMENTS DU STAGING (a executer apres 07_staging.sql, avant de creer les jobs Talend)
-- Idempotent : peut etre relance sans erreur.
-- Apres un 99_reset_dwh.sql, relancer 07_staging.sql puis ce script.
-- ============================================================================

-- 1. Mouvements : les objets JSON « origine » et « destination » sont aplatis en 3 colonnes chacun
--    (Talend lit origine.lieu, origine.latitude, origine.longitude directement dans le JSON).
ALTER TABLE staging.stg_mouvement DROP COLUMN IF EXISTS origine;
ALTER TABLE staging.stg_mouvement DROP COLUMN IF EXISTS destination;
ALTER TABLE staging.stg_mouvement ADD COLUMN IF NOT EXISTS origine_lieu          TEXT;
ALTER TABLE staging.stg_mouvement ADD COLUMN IF NOT EXISTS origine_latitude      TEXT;
ALTER TABLE staging.stg_mouvement ADD COLUMN IF NOT EXISTS origine_longitude     TEXT;
ALTER TABLE staging.stg_mouvement ADD COLUMN IF NOT EXISTS destination_lieu      TEXT;
ALTER TABLE staging.stg_mouvement ADD COLUMN IF NOT EXISTS destination_latitude  TEXT;
ALTER TABLE staging.stg_mouvement ADD COLUMN IF NOT EXISTS destination_longitude TEXT;

-- 2. WAHIS : nom du fichier d'origine (la colonne « origine » de fact_foyer_maladie vaut SIMULE
--    quand le nom du fichier contient « simule », sinon WAHIS).
ALTER TABLE staging.stg_wahis ADD COLUMN IF NOT EXISTS fichier_source TEXT;
