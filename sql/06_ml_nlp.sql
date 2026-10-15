-- 06_ml_nlp.sql : tables de résultats écrites par le calcul par lot (DAG ML/NLP) et lues par le tableau de bord.

-- Métriques d'évaluation de chaque modèle (affichées dans le tableau de bord)
CREATE TABLE IF NOT EXISTS ml.ml_metrique (
    modele           TEXT NOT NULL,                 -- ML1, ML2, ML3, NLP1, NLP2
    version_modele   TEXT NOT NULL,
    metrique         TEXT NOT NULL,                 -- precision, rappel, f1, auc, mae, rmse, mape, rouge
    valeur           NUMERIC(10,4) NOT NULL,
    jeu_evaluation   TEXT,                          -- test, validation croisée, échantillon annoté
    calcule_le       TIMESTAMP NOT NULL DEFAULT now(),
    batch_id         BIGINT,
    PRIMARY KEY (modele, version_modele, metrique, calcule_le)
);

-- ML 1 : risque sanitaire et mortalité par exploitation et par mois
CREATE TABLE IF NOT EXISTS ml.ml_risque_sanitaire (
    exploitation_sk  INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    date_sk          INT NOT NULL REFERENCES dwh.dim_date(date_sk),       -- mois prédit
    proba_risque     NUMERIC(6,5) NOT NULL,
    classe_risque    TEXT NOT NULL CHECK (classe_risque IN ('faible','moyen','eleve')),
    facteurs_cles    TEXT,                                                 -- ex. « stress thermique; rappel en retard »
    version_modele   TEXT NOT NULL,
    calcule_le       TIMESTAMP NOT NULL DEFAULT now(),
    batch_id         BIGINT,
    PRIMARY KEY (exploitation_sk, date_sk, version_modele)
);

-- ML 2 : prévision des prix par espèce et des volumes vendus
CREATE TABLE IF NOT EXISTS ml.ml_prevision_prix (
    espece_race_sk   INT NOT NULL REFERENCES dwh.dim_espece_race(espece_race_sk),
    date_sk          INT NOT NULL REFERENCES dwh.dim_date(date_sk),       -- date prévue
    prix_kg_prevu_xaf    NUMERIC(14,2) NOT NULL,
    prix_kg_borne_basse  NUMERIC(14,2),
    prix_kg_borne_haute  NUMERIC(14,2),
    volume_prevu_kg      NUMERIC(14,2),
    version_modele   TEXT NOT NULL,
    calcule_le       TIMESTAMP NOT NULL DEFAULT now(),
    batch_id         BIGINT,
    PRIMARY KEY (espece_race_sk, date_sk, version_modele)
);

-- ML 3 : anomalies de comportement GPS (agrégées par collier et par jour)
CREATE TABLE IF NOT EXISTS ml.ml_anomalies_gps (
    id_collier       TEXT NOT NULL,
    date_sk          INT NOT NULL REFERENCES dwh.dim_date(date_sk),
    exploitation_sk  INT NOT NULL REFERENCES dwh.dim_exploitation(exploitation_sk),
    score_anomalie   NUMERIC(8,5) NOT NULL,
    est_anomalie     BOOLEAN NOT NULL,
    type_suppose     TEXT,                                                 -- immobilité (maladie), sortie de zone (vol), perte de signal
    version_modele   TEXT NOT NULL,
    calcule_le       TIMESTAMP NOT NULL DEFAULT now(),
    batch_id         BIGINT,
    PRIMARY KEY (id_collier, date_sk, version_modele)
);

-- NLP 1 : symptômes et maladies extraits des comptes rendus (une ligne par entité extraite)
CREATE TABLE IF NOT EXISTS ml.nlp_extractions_veto (
    id_intervention  TEXT NOT NULL REFERENCES dwh.fact_intervention_veto(id_intervention),
    type_entite      TEXT NOT NULL CHECK (type_entite IN ('symptome','maladie')),
    entite           TEXT NOT NULL,                 -- forme canonique (fièvre, diarrhée, TRYP...)
    est_nie          BOOLEAN NOT NULL DEFAULT FALSE,  -- « Aucun signe d'orchite »
    texte_source     TEXT,                          -- passage du compte rendu
    methode          TEXT NOT NULL,                 -- spaCy EntityRuler, NER...
    version_modele   TEXT NOT NULL,
    calcule_le       TIMESTAMP NOT NULL DEFAULT now(),
    batch_id         BIGINT,
    PRIMARY KEY (id_intervention, type_entite, entite, version_modele)
);

-- NLP 2 : résumé automatique par région et par période (comptes rendus + WAHIS en complément)
CREATE TABLE IF NOT EXISTS ml.nlp_resume_foyers (
    region           TEXT NOT NULL,
    periode_debut    DATE NOT NULL,
    periode_fin      DATE NOT NULL,
    resume           TEXT NOT NULL,
    langue           TEXT NOT NULL DEFAULT 'fr',
    nb_documents     INT,
    methode          TEXT NOT NULL,                 -- extractif, Hugging Face, gabarit structuré
    version_modele   TEXT NOT NULL,
    calcule_le       TIMESTAMP NOT NULL DEFAULT now(),
    batch_id         BIGINT,
    PRIMARY KEY (region, periode_debut, periode_fin, version_modele)
);
