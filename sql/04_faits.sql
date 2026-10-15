-- 04_faits.sql : 13 tables de faits (constellation) + ref_taux_change.
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
    id_animal               TEXT,                             -- renseigné pour les mammifères
    id_lot                  TEXT,                             -- renseigné pour les volailles
    numero_dose             SMALLINT,
    date_sk                 INT NOT NULL REFERENCES dwh.dim_date(date_sk),
    exploitation_sk         INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    espece_race_sk          INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    lieu_sk                 INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),
    maladie_sk              INT NOT NULL REFERENCES dwh.dim_maladie(maladie_sk),
    vaccin_sk               INT NOT NULL REFERENCES dwh.dim_vaccin(vaccin_sk),
    veterinaire_sk          INT NOT NULL REFERENCES dwh.dim_veterinaire(veterinaire_sk),
    nb_animaux_vaccines     INT NOT NULL DEFAULT 1,
    est_rappel              BOOLEAN NOT NULL DEFAULT FALSE,   -- numero_dose > 1
    rappel_du               BOOLEAN NOT NULL DEFAULT FALSE,   -- un rappel est prévu après cette dose
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
    id_abattage        TEXT PRIMARY KEY,
    id_animal          TEXT,
    id_lot             TEXT,
    date_sk            INT NOT NULL REFERENCES dwh.dim_date(date_sk),
    exploitation_sk    INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    espece_race_sk     INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    lieu_sk            INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),
    abattoir           TEXT,                                  -- dimension dégénérée
    statut_inspection  TEXT,                                  -- dimension dégénérée
    nb_animaux         INT NOT NULL,
    poids_vif_kg       NUMERIC(12,2),                         -- total de la ligne (indicateur 10 = Σ poids / Σ nb_animaux)
    poids_carcasse_kg  NUMERIC(12,2),
    est_supprime       BOOLEAN NOT NULL DEFAULT FALSE,
    batch_id           BIGINT NOT NULL
);

-- ---------------------------------------------------------------- 7. vente / prix du marché (une vente)
CREATE TABLE IF NOT EXISTS dwh.fact_vente_prix (
    id_transaction        TEXT PRIMARY KEY,
    id_animal             TEXT,
    id_lot                TEXT,
    date_sk               INT NOT NULL REFERENCES dwh.dim_date(date_sk),
    exploitation_sk       INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    espece_race_sk        INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    lieu_sk               INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),
    produit_sk            INT NOT NULL REFERENCES dwh.dim_produit(produit_sk),   -- « Animal vif »
    marche_sk             INT NOT NULL REFERENCES dwh.dim_marche(marche_sk),
    devise_sk             INT NOT NULL REFERENCES dwh.dim_devise(devise_sk),
    destination           TEXT,                                                  -- dimension dégénérée
    destination_categorie TEXT,                                                  -- local / autre région / export
    est_export            BOOLEAN NOT NULL DEFAULT FALSE,                        -- indicateur 20
    nb_tetes              INT,
    poids_total_kg        NUMERIC(12,2),
    prix_total_devise     NUMERIC(16,2),                                         -- devise d'origine
    prix_kg_xaf           NUMERIC(14,2),                                         -- non additif
    montant_xaf           NUMERIC(16,2),                                         -- additif
    est_supprime          BOOLEAN NOT NULL DEFAULT FALSE,
    batch_id              BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fvente_date ON dwh.fact_vente_prix (date_sk, espece_race_sk);

-- ---------------------------------------------------------------- 8. alimentation (exploitation × jour × aliment)
CREATE TABLE IF NOT EXISTS dwh.fact_alimentation (
    id_alimentation      TEXT PRIMARY KEY,
    id_lot               TEXT,
    date_sk              INT NOT NULL REFERENCES dwh.dim_date(date_sk),         -- début de la semaine
    exploitation_sk      INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    espece_race_sk       INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    aliment_sk           INT NOT NULL REFERENCES dwh.dim_aliment(aliment_sk),
    devise_sk            INT NOT NULL REFERENCES dwh.dim_devise(devise_sk),
    quantite_kg          NUMERIC(12,2) NOT NULL,
    prix_unitaire_devise NUMERIC(14,2),
    cout_devise          NUMERIC(14,2),
    cout_xaf             NUMERIC(14,2),
    est_supprime         BOOLEAN NOT NULL DEFAULT FALSE,
    batch_id             BIGINT NOT NULL
);

-- ---------------------------------------------------------------- 9. mouvement (un déplacement)
CREATE TABLE IF NOT EXISTS dwh.fact_mouvement (
    id_mouvement         TEXT PRIMARY KEY,
    id_transaction       TEXT,                                                   -- lien avec la vente, si le mouvement en est une
    date_sk              INT NOT NULL REFERENCES dwh.dim_date(date_sk),         -- date de départ
    date_arrivee_sk      INT REFERENCES dwh.dim_date(date_sk),
    exploitation_sk      INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    espece_race_sk       INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    lieu_origine_sk      INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),         -- rôle 1
    lieu_destination_sk  INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),         -- rôle 2
    libelle_origine      TEXT,
    libelle_destination  TEXT,
    type_mouvement       TEXT NOT NULL,                                          -- transhumance, vente, achat
    nb_tetes             INT,
    distance_km          NUMERIC(8,1),
    est_supprime         BOOLEAN NOT NULL DEFAULT FALSE,
    batch_id             BIGINT NOT NULL
);

-- ---------------------------------------------------------------- 10. positions GPS (collier × horodatage), partitionnée par mois
CREATE TABLE IF NOT EXISTS dwh.fact_gps_position (
    id_collier           TEXT NOT NULL,
    horodatage           TIMESTAMP NOT NULL,
    id_animal            TEXT,
    date_sk              INT NOT NULL REFERENCES dwh.dim_date(date_sk),
    exploitation_sk      INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    espece_race_sk       INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    lieu_sk              INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),
    latitude             NUMERIC(9,6) NOT NULL,
    longitude            NUMERIC(9,6) NOT NULL,
    vitesse_kmh          NUMERIC(6,2),
    batterie_pct         NUMERIC(5,1),
    distance_kraal_km    NUMERIC(8,2),                                           -- dérivée à l'ETL (position - exploitation)
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


-- ---------------------------------------------------------------- 12. relevé de prix du marché (marché × espèce × semaine)
-- Source : releve_prix.csv (prix de référence hebdomadaires, indépendants des transactions). Alimente ML 2 et le benchmark.
CREATE TABLE IF NOT EXISTS dwh.fact_releve_prix (
    id_releve            TEXT PRIMARY KEY,
    date_sk              INT NOT NULL REFERENCES dwh.dim_date(date_sk),         -- début de la semaine
    marche_sk            INT NOT NULL REFERENCES dwh.dim_marche(marche_sk),
    espece_race_sk       INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    lieu_sk              INT NOT NULL REFERENCES dwh.dim_lieu(lieu_sk),
    devise_sk            INT NOT NULL REFERENCES dwh.dim_devise(devise_sk),
    prix_moyen_kg_vif    NUMERIC(14,2),                                         -- devise d'origine, non additif
    prix_min_kg_vif      NUMERIC(14,2),
    prix_max_kg_vif      NUMERIC(14,2),
    prix_moyen_kg_xaf    NUMERIC(14,2),
    nb_presentes         INT,
    batch_id             BIGINT NOT NULL
);

-- ---------------------------------------------------------------- 13. références FAOSTAT annuelles (sources 1 et 2)
-- Effectifs nationaux et prix de référence : contexte et comparaison avec le marché local (indicateur 16).
CREATE TABLE IF NOT EXISTS dwh.fact_reference_fao (
    date_sk          INT NOT NULL REFERENCES dwh.dim_date(date_sk),             -- 1er janvier de l'année
    domaine          TEXT NOT NULL CHECK (domaine IN ('elevage','prix')),
    element          TEXT NOT NULL,
    produit          TEXT NOT NULL,
    espece_race_sk   INT NOT NULL DEFAULT -1 REFERENCES dwh.dim_espece_race(espece_race_sk),
    unite            TEXT,
    valeur           NUMERIC(18,4),
    flag             TEXT,
    batch_id         BIGINT NOT NULL,
    PRIMARY KEY (date_sk, domaine, element, produit)
);
