-- 99_reset_dwh.sql : REMISE À ZÉRO de staging, dwh, audit et ml (destructif, à lancer à la main).
-- Le schéma bi n'est pas touché. Ensuite : relancer 03, 04, 05, 06 puis 07.
DROP SCHEMA IF EXISTS staging CASCADE;
DROP SCHEMA IF EXISTS dwh     CASCADE;
DROP SCHEMA IF EXISTS audit   CASCADE;
DROP SCHEMA IF EXISTS ml      CASCADE;
CREATE SCHEMA staging; CREATE SCHEMA dwh; CREATE SCHEMA audit; CREATE SCHEMA ml;
