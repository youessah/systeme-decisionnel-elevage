# Correspondance sources → staging → entrepôt

Cahier de route de l'ETL (Phase 4). Les noms de colonnes sont ceux de `docs/colonnes_sources.txt`.
Les fichiers `pilotes/*_propre.csv` sont des copies de vérité du générateur : l'ETL ne les lit jamais.

## 1. Dimensions

| Source | Staging | Cible | Règles |
|---|---|---|---|
| `ref_lieux.csv` | `stg_ref_lieux` | `dim_lieu` | Une ligne par département (`pcode_departement`). Ajouter une ligne `niveau = 'region'` par région (`pcode = pcode_region`, `zone = 'Toutes zones'`). |
| `ref_especes.csv`, `ref_races.csv` | `stg_ref_especes`, `stg_ref_races` | `dim_espece_race` | Une ligne par (espèce, race), plus une ligne « Indéterminée » par espèce. |
| `ref_maladies.csv` | `stg_ref_maladies` | `dim_maladie` | `categorie` ← `categorie`. |
| `vaccin.csv` / `ref_vaccins.csv` | `stg_vaccin`, `stg_ref_vaccins` | `dim_vaccin` | `maladie_sk` via `code_maladie` ; `rappel_jours` en entier. |
| `ref_marches.csv` | `stg_ref_marches` | `dim_marche` | `lieu_sk` via `pcode_departement`. |
| `exploitation.csv` (PostgreSQL) | `stg_exploitation` | `dim_exploitation` (**SCD2**) | `hash_diff` = md5 de `systeme_elevage, taille, proprietaire, region, pcode_departement, statut`. Changement de hash → fermer la version courante (`date_fin`, `est_courant = false`) et en ouvrir une. |
| `ref_veterinaires.csv` + XML `<veterinaire>` | `stg_veterinaire` | `dim_veterinaire` (**SCD2**) | `hash_diff` sur `statut, specialite, pcode_departement`. |
| types d'aliment (valeurs distinctes de `alimentation.csv`) | `stg_alimentation` | `dim_aliment` | `code_aliment = type_aliment` ; `est_fourrage` par règle de gestion. |
| `ref_destinations.csv` | `stg_ref_destinations` | (contrôle) | Sert à valider `destination` et `destination_categorie` des ventes. |
| — | — | `dim_date`, `dim_devise`, `dim_produit` | Graines dans `03_dimensions.sql`. |

## 2. Faits

| Source | Staging | Cible | Règles de transformation |
|---|---|---|---|
| `animal.csv`, `lot_volaille.csv`, `suivi_lot_semaine.csv` | `stg_animal`, `stg_lot_volaille`, `stg_suivi_lot_semaine` | `fact_cheptel` | Mammifères : effectif mensuel recalculé avec `date_entree` / `date_sortie`, naissances avec `date_naissance` et `type_entree`, décès avec `motif_sortie`. Volailles : `effectif_fin_semaine` du dernier suivi du mois. `nb_femelles_reproductrices` : `sexe = F` et `statut_reproducteur`. |
| `vaccination.csv` (MySQL) | `stg_vaccination` | `fact_vaccination` | `maladie_sk` via `code_vaccin` ; `est_rappel = numero_dose > 1` ; `rappel_du = date_rappel_prevue is not null` ; `rappel_a_temps` = rappel réalisé au plus tard à la date prévue (NULL si l'échéance n'est pas passée). |
| XML `<intervention>` | `stg_intervention` | `fact_intervention_veto` | `delai_h` = `date_intervention − date_signalement` ; `cout_total_xaf` = (médicaments + honoraires) × taux du mois ; `maladie_sk = -1` si `code_maladie` vide. |
| `wahis_quantitatif_cameroun.csv` | `stg_wahis` | `fact_foyer_maladie` | `Semestre` (texte) → 1 ou 2 ; `Nouveaux foyers` (texte) → entier ; `Division administrative` → `dim_lieu` niveau région ; `Maladie` rapprochée par `mot_cle_wahis` ; `Espèce` vide → `-1`. |
| `production_lait_oeufs.xlsx` (3 feuilles) | `stg_production` | `fact_production` | **Format large à séparer** : une ligne lait (`litres_lait`, producteurs = `nb_vaches_lactation`) et une ligne œufs (`nb_oeufs`, producteurs = `nb_pondeuses`). Espèce : Bovins pour le lait, Volailles pour les œufs (hypothèse à valider). |
| `abattage.csv` | `stg_abattage` | `fact_abattage` | `region` de la source sert de contrôle de cohérence ; pas de destination. |
| `vente.csv` | `stg_vente` | `fact_vente_prix` | `produit_sk` = « Animal vif » ; `montant_xaf = prix_total × taux(devise, mois)` ; `prix_kg_xaf = montant_xaf / poids_total_kg` ; `est_export = (destination_categorie = 'export')` (à valider sur `ref_destinations.csv`). |
| `releve_prix.csv` | `stg_releve_prix` | `fact_releve_prix` | `semaine` → début de semaine ; prix convertis en XAF. |
| `alimentation.csv` | `stg_alimentation` | `fact_alimentation` | `date_semaine` → début de semaine ; `cout_xaf = cout_total × taux`. |
| `mouvements_AAAA.json` | `stg_mouvement` | `fact_mouvement` | `origine` et `destination` (libellés) → `dim_lieu` si trouvés, sinon `-1` avec libellé conservé ; `id_transaction` renseigné pour les ventes. |
| `gps_AAAA-MM.json` + `colliers.json` | `stg_gps`, `stg_collier` | `fact_gps_position` | `espece` via `colliers.json` ; `distance_kraal_km` = distance entre la position et l'exploitation ; partition mensuelle. |
| `meteo_horaire_reference.csv` / API Open-Meteo | `stg_meteo_horaire` | `fact_environnement` | Agrégation par département et par jour : température moyenne et maximale, humidité, **indice THI**, `stress_thermique = THI ≥ seuil` (seuil dans la configuration). |
| `ndvi_cmr_full.csv` | `stg_ndvi` | `fact_environnement` | `vim` → `ndvi` ; `PCODE` → `dim_lieu` ; valeur reportée sur les jours de la période. |
| `faostat_change_cameroun.csv` / API de change | `stg_taux_change` | `ref_taux_change` | `Year` + `Months` → date ; `Value` → `taux_vers_xaf`. Vérifier la couverture de l'USD et de l'EUR. |
| `faostat_elevage_cameroun.csv` | `stg_faostat_elevage` | `fact_reference_fao` (`domaine = 'elevage'`) | `Année` → 1er janvier. |
| `faostat_prix_cameroun.csv` | `stg_faostat_prix` | `fact_reference_fao` (`domaine = 'prix'`) | `Year` → 1er janvier. |

## 3. Validation des contrôles qualité

Les fichiers `pilotes/defauts_*.csv` (colonnes `table`, `identifiant`, `type_defaut`) listent tous les défauts injectés
dans les sources. Chaque ligne doit se retrouver dans `audit.etl_reject` avec le bon `code_motif` au premier chargement.
Écart entre les deux = contrôle manquant ou trop permissif. C'est le test automatisé principal de la Phase 4.

## 4. Ordre de chargement

1. Référentiels et dimensions (lieu, espèce/race, maladie, vaccin, marché, aliment).
2. Dimensions SCD2 (exploitation, vétérinaire).
3. `ref_taux_change`.
4. Faits, dans n'importe quel ordre ; `fact_cheptel` avant les calculs ML.
5. Résultats ML et NLP (calcul par lot).
