-- 07_staging.sql : une table par fichier ou table source (couche staging).
-- Choix : toutes les colonnes sont en TEXT (copie brute). Le typage et les contrôles (type, format, plage)
-- se font à l'étape de transformation, pour pouvoir journaliser chaque rejet dans audit.etl_reject.
-- Colonnes ajoutées par l'ETL : batch_id (lot de chargement) et charge_le (horodatage).

-- S1 faostat_elevage_cameroun.csv
CREATE TABLE IF NOT EXISTS staging.stg_faostat_elevage (
    code_domaine               TEXT,
    domaine                    TEXT,
    code_zone_m49              TEXT,
    zone                       TEXT,
    code_element               TEXT,
    element                    TEXT,
    code_produit_cpc           TEXT,
    produit                    TEXT,
    code_annee                 TEXT,
    annee                      TEXT,
    unite                      TEXT,
    valeur                     TEXT,
    symbole                    TEXT,
    description_symbole        TEXT,
    note                       TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_faostat_elevage_batch ON staging.stg_faostat_elevage (batch_id);

-- S2 faostat_prix_cameroun.csv
CREATE TABLE IF NOT EXISTS staging.stg_faostat_prix (
    iso3                       TEXT,
    start_date                 TEXT,
    end_date                   TEXT,
    area_code                  TEXT,
    area_code_m49              TEXT,
    area                       TEXT,
    item_code                  TEXT,
    item_code_cpc              TEXT,
    item                       TEXT,
    element_code               TEXT,
    element                    TEXT,
    year_code                  TEXT,
    year                       TEXT,
    months_code                TEXT,
    months                     TEXT,
    unit                       TEXT,
    value                      TEXT,
    flag                       TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_faostat_prix_batch ON staging.stg_faostat_prix (batch_id);

-- S3 wahis_quantitatif_cameroun.csv
CREATE TABLE IF NOT EXISTS staging.stg_wahis (
    annee                      TEXT,
    semestre                   TEXT,
    region_mondiale            TEXT,
    pays                       TEXT,
    division_administrative    TEXT,
    maladie                    TEXT,
    genotype_serotype          TEXT,
    categorie_animale          TEXT,
    event_id                   TEXT,
    espece                     TEXT,
    outbreak_id                TEXT,
    nouveaux_foyers            TEXT,
    sensibles                  TEXT,
    unites_mesure              TEXT,
    cas                        TEXT,
    mis_a_mort_elimines        TEXT,
    abattus_commerciaux        TEXT,
    morts                      TEXT,
    vaccines                   TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_wahis_batch ON staging.stg_wahis (batch_id);

-- S4 PostgreSQL src_cheptel.animal
CREATE TABLE IF NOT EXISTS staging.stg_animal (
    id_animal                  TEXT,
    id_exploitation            TEXT,
    espece                     TEXT,
    race                       TEXT,
    sexe                       TEXT,
    date_naissance             TEXT,
    type_entree                TEXT,
    date_entree                TEXT,
    date_sortie                TEXT,
    motif_sortie               TEXT,
    cause_deces                TEXT,
    statut_reproducteur        TEXT,
    updated_at                 TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_animal_batch ON staging.stg_animal (batch_id);

-- S4 PostgreSQL src_cheptel.exploitation
CREATE TABLE IF NOT EXISTS staging.stg_exploitation (
    id_exploitation            TEXT,
    nom_exploitation           TEXT,
    proprietaire               TEXT,
    pcode_departement          TEXT,
    departement                TEXT,
    region                     TEXT,
    espece_principale          TEXT,
    systeme_elevage            TEXT,
    taille                     TEXT,
    date_creation              TEXT,
    latitude                   TEXT,
    longitude                  TEXT,
    statut                     TEXT,
    updated_at                 TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_exploitation_batch ON staging.stg_exploitation (batch_id);

-- S4 PostgreSQL src_cheptel.lot_volaille
CREATE TABLE IF NOT EXISTS staging.stg_lot_volaille (
    id_lot                     TEXT,
    id_exploitation            TEXT,
    espece                     TEXT,
    type_production            TEXT,
    race                       TEXT,
    date_mise_en_place         TEXT,
    effectif_initial           TEXT,
    date_sortie                TEXT,
    nb_morts_total             TEXT,
    motif_sortie               TEXT,
    updated_at                 TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_lot_volaille_batch ON staging.stg_lot_volaille (batch_id);

-- S4 PostgreSQL src_cheptel.suivi_lot_semaine
CREATE TABLE IF NOT EXISTS staging.stg_suivi_lot_semaine (
    id_suivi                   TEXT,
    id_lot                     TEXT,
    date_semaine               TEXT,
    nb_morts                   TEXT,
    effectif_fin_semaine       TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_suivi_lot_semaine_batch ON staging.stg_suivi_lot_semaine (batch_id);

-- S5 MySQL src_vaccinations.vaccination
CREATE TABLE IF NOT EXISTS staging.stg_vaccination (
    id_vaccination             TEXT,
    id_exploitation            TEXT,
    id_animal                  TEXT,
    id_lot                     TEXT,
    espece                     TEXT,
    code_vaccin                TEXT,
    vaccin                     TEXT,
    maladie_ciblee             TEXT,
    numero_dose                TEXT,
    date_vaccination           TEXT,
    date_rappel_prevue         TEXT,
    date_rappel_realisee       TEXT,
    id_veterinaire             TEXT,
    nb_animaux_vaccines        TEXT,
    updated_at                 TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_vaccination_batch ON staging.stg_vaccination (batch_id);

-- S5 MySQL src_vaccinations.vaccin
CREATE TABLE IF NOT EXISTS staging.stg_vaccin (
    code_vaccin                TEXT,
    vaccin                     TEXT,
    code_maladie               TEXT,
    especes_cibles             TEXT,
    rappel_jours               TEXT,
    maladie                    TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_vaccin_batch ON staging.stg_vaccin (batch_id);

-- S6 mouvements_AAAA.json
CREATE TABLE IF NOT EXISTS staging.stg_mouvement (
    id_mouvement               TEXT,
    id_exploitation            TEXT,
    espece                     TEXT,
    nb_tetes                   TEXT,
    type_mouvement             TEXT,
    date_depart                TEXT,
    date_arrivee               TEXT,
    origine                    TEXT,
    destination                TEXT,
    distance_km                TEXT,
    id_transaction             TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_mouvement_batch ON staging.stg_mouvement (batch_id);

-- S7 abattage.csv
CREATE TABLE IF NOT EXISTS staging.stg_abattage (
    id_abattage                TEXT,
    id_exploitation            TEXT,
    id_animal                  TEXT,
    id_lot                     TEXT,
    espece                     TEXT,
    nb_animaux                 TEXT,
    date_abattage              TEXT,
    poids_vif_kg               TEXT,
    poids_carcasse_kg          TEXT,
    abattoir                   TEXT,
    region                     TEXT,
    statut_inspection          TEXT,
    updated_at                 TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_abattage_batch ON staging.stg_abattage (batch_id);

-- S8 production_lait_oeufs.xlsx (une feuille par année)
CREATE TABLE IF NOT EXISTS staging.stg_production (
    date                       TEXT,
    id_exploitation            TEXT,
    litres_lait                TEXT,
    nb_vaches_lactation        TEXT,
    nb_oeufs                   TEXT,
    nb_pondeuses               TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_production_batch ON staging.stg_production (batch_id);

-- S9 alimentation.csv
CREATE TABLE IF NOT EXISTS staging.stg_alimentation (
    id_alimentation            TEXT,
    date_semaine               TEXT,
    id_exploitation            TEXT,
    espece                     TEXT,
    id_lot                     TEXT,
    type_aliment               TEXT,
    quantite_kg                TEXT,
    prix_unitaire              TEXT,
    devise                     TEXT,
    cout_total                 TEXT,
    updated_at                 TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_alimentation_batch ON staging.stg_alimentation (batch_id);

-- S10 vente.csv
CREATE TABLE IF NOT EXISTS staging.stg_vente (
    id_transaction             TEXT,
    date_transaction           TEXT,
    id_marche                  TEXT,
    marche                     TEXT,
    region                     TEXT,
    id_exploitation            TEXT,
    id_animal                  TEXT,
    id_lot                     TEXT,
    espece                     TEXT,
    nb_tetes                   TEXT,
    poids_total_kg             TEXT,
    prix_total                 TEXT,
    devise                     TEXT,
    destination_categorie      TEXT,
    destination                TEXT,
    updated_at                 TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_vente_batch ON staging.stg_vente (batch_id);

-- S10 releve_prix.csv
CREATE TABLE IF NOT EXISTS staging.stg_releve_prix (
    id_releve                  TEXT,
    semaine                    TEXT,
    id_marche                  TEXT,
    espece                     TEXT,
    prix_moyen_kg_vif          TEXT,
    prix_min_kg_vif            TEXT,
    prix_max_kg_vif            TEXT,
    nb_presentes               TEXT,
    devise                     TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_releve_prix_batch ON staging.stg_releve_prix (batch_id);

-- S11 ndvi_cmr_full.csv
CREATE TABLE IF NOT EXISTS staging.stg_ndvi (
    date                       TEXT,
    adm_level                  TEXT,
    adm_id                     TEXT,
    pcode                      TEXT,
    n_pixels                   TEXT,
    vim                        TEXT,
    vim_avg                    TEXT,
    viq                        TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_ndvi_batch ON staging.stg_ndvi (batch_id);

-- S12 API Open-Meteo (JSON aplati)
CREATE TABLE IF NOT EXISTS staging.stg_meteo_horaire (
    pcode_departement          TEXT,
    departement                TEXT,
    horodatage                 TEXT,
    temperature_c              TEXT,
    humidite_pct               TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_meteo_horaire_batch ON staging.stg_meteo_horaire (batch_id);

-- S13 veterinaires_interventions.xml <veterinaire>
CREATE TABLE IF NOT EXISTS staging.stg_veterinaire (
    id_veterinaire             TEXT,
    nom                        TEXT,
    prenom                     TEXT,
    statut                     TEXT,
    specialite                 TEXT,
    date_prise_poste           TEXT,
    pcode_departement          TEXT,
    departement                TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_veterinaire_batch ON staging.stg_veterinaire (batch_id);

-- S13 veterinaires_interventions.xml <intervention>
CREATE TABLE IF NOT EXISTS staging.stg_intervention (
    id_intervention            TEXT,
    id_exploitation            TEXT,
    id_veterinaire             TEXT,
    espece                     TEXT,
    code_maladie               TEXT,
    maladie                    TEXT,
    date_signalement           TEXT,
    date_intervention          TEXT,
    nb_animaux_malades         TEXT,
    nb_animaux_traites         TEXT,
    nb_deces                   TEXT,
    cout_medicaments           TEXT,
    honoraires                 TEXT,
    devise                     TEXT,
    compte_rendu               TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_intervention_batch ON staging.stg_intervention (batch_id);

-- S14 colliers.json
CREATE TABLE IF NOT EXISTS staging.stg_collier (
    id_collier                 TEXT,
    id_animal                  TEXT,
    id_exploitation            TEXT,
    espece                     TEXT,
    date_pose                  TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_collier_batch ON staging.stg_collier (batch_id);

-- S14 gps_AAAA-MM.json
CREATE TABLE IF NOT EXISTS staging.stg_gps (
    id_collier                 TEXT,
    id_animal                  TEXT,
    id_exploitation            TEXT,
    horodatage                 TEXT,
    latitude                   TEXT,
    longitude                  TEXT,
    vitesse_kmh                TEXT,
    batterie_pct               TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_gps_batch ON staging.stg_gps (batch_id);

-- S15 API / faostat_change_cameroun.csv
CREATE TABLE IF NOT EXISTS staging.stg_taux_change (
    iso3                       TEXT,
    start_date                 TEXT,
    end_date                   TEXT,
    area_code                  TEXT,
    area_code_m49              TEXT,
    area                       TEXT,
    element_code               TEXT,
    element                    TEXT,
    iso_currency_code          TEXT,
    currency                   TEXT,
    year_code                  TEXT,
    year                       TEXT,
    months_code                TEXT,
    months                     TEXT,
    unit                       TEXT,
    value                      TEXT,
    flag                       TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_taux_change_batch ON staging.stg_taux_change (batch_id);

-- référentiel ref_especes.csv
CREATE TABLE IF NOT EXISTS staging.stg_ref_especes (
    code_espece                TEXT,
    espece                     TEXT,
    groupe                     TEXT,
    production_principale      TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_ref_especes_batch ON staging.stg_ref_especes (batch_id);

-- référentiel ref_races.csv
CREATE TABLE IF NOT EXISTS staging.stg_ref_races (
    code_race                  TEXT,
    espece                     TEXT,
    race                       TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_ref_races_batch ON staging.stg_ref_races (batch_id);

-- référentiel ref_maladies.csv
CREATE TABLE IF NOT EXISTS staging.stg_ref_maladies (
    code_maladie               TEXT,
    maladie                    TEXT,
    sigle                      TEXT,
    categorie                  TEXT,
    especes_concernees         TEXT,
    mot_cle_wahis              TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_ref_maladies_batch ON staging.stg_ref_maladies (batch_id);

-- référentiel ref_vaccins.csv
CREATE TABLE IF NOT EXISTS staging.stg_ref_vaccins (
    code_vaccin                TEXT,
    vaccin                     TEXT,
    code_maladie               TEXT,
    especes_cibles             TEXT,
    rappel_jours               TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_ref_vaccins_batch ON staging.stg_ref_vaccins (batch_id);

-- référentiel ref_lieux.csv
CREATE TABLE IF NOT EXISTS staging.stg_ref_lieux (
    id_lieu                    TEXT,
    departement                TEXT,
    pcode_departement          TEXT,
    region                     TEXT,
    pcode_region               TEXT,
    chef_lieu                  TEXT,
    latitude                   TEXT,
    longitude                  TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_ref_lieux_batch ON staging.stg_ref_lieux (batch_id);

-- référentiel ref_marches.csv
CREATE TABLE IF NOT EXISTS staging.stg_ref_marches (
    id_marche                  TEXT,
    nom_marche                 TEXT,
    ville                      TEXT,
    pcode_departement          TEXT,
    departement                TEXT,
    region                     TEXT,
    latitude                   TEXT,
    longitude                  TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_ref_marches_batch ON staging.stg_ref_marches (batch_id);

-- référentiel ref_destinations.csv
CREATE TABLE IF NOT EXISTS staging.stg_ref_destinations (
    id_destination             TEXT,
    destination                TEXT,
    categorie                  TEXT,
    batch_id                   BIGINT NOT NULL,
    charge_le                  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_ref_destinations_batch ON staging.stg_ref_destinations (batch_id);
