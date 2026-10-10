-- A executer connecte a la base dwh_elevage
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS dwh;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS ml;
CREATE SCHEMA IF NOT EXISTS bi;

COMMENT ON SCHEMA staging IS 'Copie brute des sources, avec batch_id';
COMMENT ON SCHEMA dwh     IS 'Entrepot : dimensions et faits';
COMMENT ON SCHEMA audit   IS 'Journalisation ETL, rejets, filigranes';
COMMENT ON SCHEMA ml      IS 'Resultats ML et NLP';
COMMENT ON SCHEMA bi      IS 'Vues exposees a Power BI';
