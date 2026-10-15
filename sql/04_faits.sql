-- 04_faits.sql : 11 tables de faits (constellation) + ref_taux_change.
-- Conventions : *_sk = clés de substitution ; id_* = clé naturelle (dimension dégénérée) pour l'UPSERT ;
-- est_supprime = suppression logique ; batch_id = lot ETL ayant écrit la ligne.

-- ---------------------------------------------------------------- taux de change (source 15)
CREATE TABLE IF NOT EXISTS dwh.ref_taux_change (
    date_sk         INT NOT NULL REFERENCES dwh.dim_date(date_sk),
    devise_sk       INT NOT NULL REFERENCES dwh.dim_devise(devise_sk),
    taux_vers_xaf   NUMERIC(18,6) NOT NULL,      -- 1 unité de devise = x XAF
    batch_id        BIGINT NOT NULL,
    PRIMARY KEY (date_sk, devise_sk)
);

-- ---------------------------------------------------------------- 1. cheptel (exploitation × espèce × mois)
CREATE TABLE IF NOT EXISTS dwh.fact_cheptel (
    date_sk                     INT NOT NULL REFERENCES dwh.dim_date(date_sk),     -- 1er jour du mois
    exploitation_sk             INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    espece_race_sk              INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    lieu_sk                     INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),
    effectif_debut              INT,
    effectif_fin                INT NOT NULL,                                       -- semi-additif
    nb_naissances               INT NOT NULL DEFAULT 0,
    nb_deces                    INT NOT NULL DEFAULT 0,
    nb_entrees                  INT NOT NULL DEFAULT 0,
    nb_sorties                  INT NOT NULL DEFAULT 0,
    nb_femelles_reproductrices  INT,                                                -- semi-additif
    batch_id                    BIGINT NOT NULL,
    PRIMARY KEY (date_sk, exploitation_sk, espece_race_sk)
);

-- ---------------------------------------------------------------- 2. vaccination (une vaccination)
CREATE TABLE IF NOT EXISTS dwh.fact_vaccination (
    id_vaccination          TEXT PRIMARY KEY,
    id_animal               TEXT,                             -- dimension dégénérée (S5 est au niveau animal : à confirmer)
    numero_dose             SMALLINT,
    date_sk                 INT NOT NULL REFERENCES dwh.dim_date(date_sk),
    exploitation_sk         INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    espece_race_sk          INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    lieu_sk                 INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),
    maladie_sk              INT NOT NULL REFERENCES dwh.dim_maladie(maladie_sk),
    vaccin_sk               INT NOT NULL REFERENCES dwh.dim_vaccin(vaccin_sk),
    nb_animaux_vaccines     INT NOT NULL DEFAULT 1,
    est_rappel              BOOLEAN NOT NULL DEFAULT FALSE,
    rappel_du               BOOLEAN NOT NULL DEFAULT FALSE,   -- un rappel était prévu après cette dose
    date_rappel_prevue_sk   INT REFERENCES dwh.dim_date(date_sk),
    date_rappel_realisee_sk INT REFERENCES dwh.dim_date(date_sk),
    rappel_a_temps          BOOLEAN,                          -- NULL tant que l'échéance n'est pas passée
    est_supprime            BOOLEAN NOT NULL DEFAULT FALSE,
    batch_id                BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fvacc_expl ON dwh.fact_vaccination (exploitation_sk, date_sk);

-- ---------------------------------------------------------------- 3. intervention vétérinaire (une intervention)
CREATE TABLE IF NOT EXISTS dwh.fact_intervention_veto (
    id_intervention          TEXT PRIMARY KEY,
    date_signalement_sk      INT NOT NULL REFERENCES dwh.dim_date(date_sk),   -- rôle 1
    date_intervention_sk     INT REFERENCES dwh.dim_date(date_sk),            -- rôle 2
    exploitation_sk          INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    espece_race_sk           INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    lieu_sk                  INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),
    maladie_sk               INT NOT NULL REFERENCES dwh.dim_maladie(maladie_sk),
    veterinaire_sk           INT NOT NULL REFERENCES dwh.dim_veterinaire(veterinaire_sk),
    devise_sk                INT NOT NULL REFERENCES dwh.dim_devise(devise_sk),
    ts_signalement           TIMESTAMP NOT NULL,
    ts_intervention          TIMESTAMP,
    delai_h                  NUMERIC(8,2),                                    -- non additif (moyenne côté BI)
    nb_malades               INT,
    nb_traites               INT,
    nb_deces                 INT,
    cout_medicaments         NUMERIC(14,2),                                   -- devise d'origine
    honoraires               NUMERIC(14,2),
    cout_total_xaf           NUMERIC(14,2),
    compte_rendu             TEXT,                                            -- entrée du NLP 1
    est_supprime             BOOLEAN NOT NULL DEFAULT FALSE,
    batch_id                 BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_finterv_expl ON dwh.fact_intervention_veto (exploitation_sk, date_signalement_sk);

-- ---------------------------------------------------------------- 4. foyers WAHIS (semestre × division × maladie × espèce)
-- Export quantitatif agrégé : pas de foyer individuel. Lignes sans espèce -> espece_race_sk = -1.
CREATE TABLE IF NOT EXISTS dwh.fact_foyer_maladie (
    date_sk          INT NOT NULL REFERENCES dwh.dim_date(date_sk),     -- 1er jour du semestre
    annee            SMALLINT NOT NULL,
    semestre         SMALLINT NOT NULL CHECK (semestre IN (1,2)),
    lieu_sk          INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),     -- division administrative
    maladie_sk       INT NOT NULL REFERENCES dwh.dim_maladie(maladie_sk),
    espece_race_sk   INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    origine          TEXT NOT NULL DEFAULT 'WAHIS',                      -- colonne `origine` de la source (dimension dégénérée)
    nouveaux_foyers  INT NOT NULL,                                       -- mesure de l'indicateur 11
    nb_cas           INT,
    nb_deces         INT,
    batch_id         BIGINT NOT NULL,
    PRIMARY KEY (date_sk, lieu_sk, maladie_sk, espece_race_sk, origine)
);

-- ---------------------------------------------------------------- 5. production lait / œufs (exploitation × jour × produit)
CREATE TABLE IF NOT EXISTS dwh.fact_production (
    date_sk          INT NOT NULL REFERENCES dwh.dim_date(date_sk),
    exploitation_sk  INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    espece_race_sk   INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    produit_sk       INT NOT NULL REFERENCES dwh.dim_produit(produit_sk),
    quantite         NUMERIC(12,2) NOT NULL,                                  -- litres ou unités
    nb_animaux_producteurs INT,
    est_supprime     BOOLEAN NOT NULL DEFAULT FALSE,
    batch_id         BIGINT NOT NULL,
    PRIMARY KEY (date_sk, exploitation_sk, espece_race_sk, produit_sk)
);

-- ---------------------------------------------------------------- 6. abattage (un lot abattu)
CREATE TABLE IF NOT EXISTS dwh.fact_abattage (
    id_abattage      TEXT PRIMARY KEY,
    date_sk          INT NOT NULL REFERENCES dwh.dim_date(date_sk),
    exploitation_sk  INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    espece_race_sk   INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    lieu_sk          INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),
    destination      TEXT,                                                    -- si présente dans S7 (à confirmer)
    nb_animaux       INT NOT NULL,
    poids_vif_kg     NUMERIC(10,2),                                           -- poids vif moyen (indicateur 10)
    poids_vif_total_kg NUMERIC(12,2),
    est_supprime     BOOLEAN NOT NULL DEFAULT FALSE,
    batch_id         BIGINT NOT NULL
);

-- ---------------------------------------------------------------- 7. vente / prix du marché (une vente)
CREATE TABLE IF NOT EXISTS dwh.fact_vente_prix (
    id_vente         TEXT PRIMARY KEY,
    date_sk          INT NOT NULL REFERENCES dwh.dim_date(date_sk),
    exploitation_sk  INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    espece_race_sk   INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    lieu_sk          INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),
    produit_sk       INT NOT NULL REFERENCES dwh.dim_produit(produit_sk),
    marche_sk        INT NOT NULL REFERENCES dwh.dim_marche(marche_sk),
    devise_sk        INT NOT NULL REFERENCES dwh.dim_devise(devise_sk),
    destination      TEXT,                                                    -- local / autre région / export (S10)
    est_export       BOOLEAN NOT NULL DEFAULT FALSE,                          -- indicateur 20
    nb_tetes         INT,
    poids_total_kg   NUMERIC(12,2),
    prix_total_devise NUMERIC(16,2),                                          -- devise d'origine
    prix_kg_xaf      NUMERIC(14,2),                                           -- non additif
    montant_xaf      NUMERIC(16,2),                                           -- additif
    est_supprime     BOOLEAN NOT NULL DEFAULT FALSE,
    batch_id         BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fvente_date ON dwh.fact_vente_prix (date_sk, espece_race_sk);

-- ---------------------------------------------------------------- 8. alimentation (exploitation × jour × aliment)
CREATE TABLE IF NOT EXISTS dwh.fact_alimentation (
    date_sk          INT NOT NULL REFERENCES dwh.dim_date(date_sk),
    exploitation_sk  INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    espece_race_sk   INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    aliment_sk       INT NOT NULL REFERENCES dwh.dim_aliment(aliment_sk),
    devise_sk        INT NOT NULL REFERENCES dwh.dim_devise(devise_sk),
    quantite_kg      NUMERIC(12,2) NOT NULL,
    cout_devise      NUMERIC(14,2),
    cout_xaf         NUMERIC(14,2),
    est_supprime     BOOLEAN NOT NULL DEFAULT FALSE,
    batch_id         BIGINT NOT NULL,
    PRIMARY KEY (date_sk, exploitation_sk, espece_race_sk, aliment_sk)
);

-- ---------------------------------------------------------------- 9. mouvement (un déplacement)
CREATE TABLE IF NOT EXISTS dwh.fact_mouvement (
    id_mouvement         TEXT PRIMARY KEY,
    date_sk              INT NOT NULL REFERENCES dwh.dim_date(date_sk),         -- date de départ
    date_retour_sk       INT REFERENCES dwh.dim_date(date_sk),
    exploitation_sk      INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    espece_race_sk       INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    lieu_origine_sk      INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),         -- rôle 1
    lieu_destination_sk  INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),         -- rôle 2
    type_mouvement       TEXT NOT NULL,                                          -- transhumance, vente, achat
    nb_animaux           INT,
    distance_km          NUMERIC(8,1),
    est_supprime         BOOLEAN NOT NULL DEFAULT FALSE,
    batch_id             BIGINT NOT NULL
);

-- ---------------------------------------------------------------- 10. positions GPS (collier × horodatage), partitionnée par mois
CREATE TABLE IF NOT EXISTS dwh.fact_gps_position (
    id_collier           TEXT NOT NULL,
    horodatage           TIMESTAMP NOT NULL,
    date_sk              INT NOT NULL REFERENCES dwh.dim_date(date_sk),
    exploitation_sk      INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    espece_race_sk       INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    lieu_sk              INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),
    latitude             NUMERIC(9,6) NOT NULL,
    longitude            NUMERIC(9,6) NOT NULL,
    vitesse_kmh          NUMERIC(6,2),
    distance_kraal_km    NUMERIC(8,2),
    batch_id             BIGINT NOT NULL,
    PRIMARY KEY (id_collier, horodatage)
) PARTITION BY RANGE (horodatage);

DO $$
DECLARE m DATE := DATE '2024-01-01';
BEGIN
    WHILE m < DATE '2027-01-01' LOOP
        EXECUTE format('CREATE TABLE IF NOT EXISTS dwh.fact_gps_position_%s PARTITION OF dwh.fact_gps_position FOR VALUES FROM (%L) TO (%L)',
                       to_char(m, 'YYYY_MM'), m, (m + INTERVAL '1 month')::DATE);
        m := (m + INTERVAL '1 month')::DATE;
    END LOOP;
END $$;
CREATE TABLE IF NOT EXISTS dwh.fact_gps_position_defaut PARTITION OF dwh.fact_gps_position DEFAULT;

-- ---------------------------------------------------------------- 11. environnement (lieu × jour)
CREATE TABLE IF NOT EXISTS dwh.fact_environnement (
    date_sk              INT NOT NULL REFERENCES dwh.dim_date(date_sk),
    lieu_sk              INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),
    temp_moy_c           NUMERIC(5,2),
    temp_max_c           NUMERIC(5,2),
    humidite_moy_pct     NUMERIC(5,2),
    pluie_mm             NUMERIC(7,2),
    ndvi                 NUMERIC(5,4),                                           -- source 11, reporté sur les jours
    indice_thi_max       NUMERIC(5,2),                                           -- indice température-humidité
    stress_thermique     BOOLEAN NOT NULL DEFAULT FALSE,                         -- THI >= seuil de la configuration
    batch_id             BIGINT NOT NULL,
    PRIMARY KEY (date_sk, lieu_sk)
);
