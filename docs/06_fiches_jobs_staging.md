# Fiches des jobs Talend de staging

29 jobs, un par table de `staging`. Toutes les colonnes de staging sont de type texte ; seules `batch_id` et `charge_le` sont techniques et se remplissent dans le `tMap`. **Dans Talend, tous les champs lus sont de type `String`** : le typage se fait plus tard, en SQL.

Variables de contexte : `context.path_raw` (= `C:/projet11/data/raw`), `context.path_generated` (= `C:/projet11/data/generated`), `context.batch_id` (Long), et les connexions PostgreSQL et MySQL du groupe `Dev`.

## 1. Vue d'ensemble

| N° | Job | Table de staging | Format | Lignes attendues |
|---|---|---|---|---|
| 1 | `j_stg_faostat_elevage` | `staging.stg_faostat_elevage` | CSV | 40 |
| 2 | `j_stg_faostat_prix` | `staging.stg_faostat_prix` | CSV | 4 561 |
| 3 | `j_stg_taux_change` | `staging.stg_taux_change` | CSV | 755 |
| 4 | `j_stg_ndvi` | `staging.stg_ndvi` | CSV | 59 296 |
| 5 | `j_stg_meteo_horaire` | `staging.stg_meteo_horaire` | CSV | 157 824 |
| 6 | `j_stg_abattage` | `staging.stg_abattage` | CSV | 2 809 |
| 7 | `j_stg_vente` | `staging.stg_vente` | CSV | 6 662 |
| 8 | `j_stg_releve_prix` | `staging.stg_releve_prix` | CSV | 3 768 |
| 9 | `j_stg_alimentation` | `staging.stg_alimentation` | CSV | 110 437 |
| 10 | `j_stg_ref_especes` | `staging.stg_ref_especes` | CSV | 4 |
| 11 | `j_stg_ref_races` | `staging.stg_ref_races` | CSV | 11 |
| 12 | `j_stg_ref_maladies` | `staging.stg_ref_maladies` | CSV | 9 |
| 13 | `j_stg_ref_vaccins` | `staging.stg_ref_vaccins` | CSV | 7 |
| 14 | `j_stg_ref_lieux` | `staging.stg_ref_lieux` | CSV | 6 |
| 15 | `j_stg_ref_marches` | `staging.stg_ref_marches` | CSV | 6 |
| 16 | `j_stg_ref_destinations` | `staging.stg_ref_destinations` | CSV | 7 |
| 17 | `j_stg_exploitation` | `staging.stg_exploitation` | PostgreSQL | 200 |
| 18 | `j_stg_animal` | `staging.stg_animal` | PostgreSQL | 35 292 |
| 19 | `j_stg_lot_volaille` | `staging.stg_lot_volaille` | PostgreSQL | 725 |
| 20 | `j_stg_suivi_lot_semaine` | `staging.stg_suivi_lot_semaine` | PostgreSQL | 11 683 |
| 21 | `j_stg_vaccin` | `staging.stg_vaccin` | MySQL | 7 |
| 22 | `j_stg_vaccination` | `staging.stg_vaccination` | MySQL | 151 413 |
| 23 | `j_stg_production` | `staging.stg_production` | Excel | 136 258 |
| 24 | `j_stg_mouvement` | `staging.stg_mouvement` | JSON | 8 152 |
| 25 | `j_stg_collier` | `staging.stg_collier` | JSON | 300 |
| 26 | `j_stg_gps` | `staging.stg_gps` | JSON | 395 947 |
| 27 | `j_stg_veterinaire` | `staging.stg_veterinaire` | XML | 24 |
| 28 | `j_stg_intervention` | `staging.stg_intervention` | XML | 2 390 |
| 29 | `j_stg_wahis` | `staging.stg_wahis` | CSV (4 fichiers) | 537 |

Total attendu dans le staging : **1 089 130 lignes**.

## 2. Jobs CSV (16)

Composants : `tFileInputDelimited` → `tMap` → `tPostgresqlOutput`. Réglages communs : séparateur `,` ; séparateur de ligne `\n` ; en-tête = 1 ligne ; encodage `UTF-8` ; délimiteur de texte `"`. Talend associe les colonnes **par position** : les noms accentués des en-têtes sont sans importance.

| Job | Fichier (expression Talend) | Remarque |
|---|---|---|
| `j_stg_faostat_elevage` | `context.path_raw + "/faostat_elevage_cameroun.csv"` | Fichier FAO ; en-tête sur 1 ligne ; UTF-8 |
| `j_stg_faostat_prix` | `context.path_raw + "/faostat_prix_cameroun.csv"` | Codes avec apostrophe : les garder tels quels, ils sont nettoyés plus tard en SQL |
| `j_stg_taux_change` | `context.path_raw + "/faostat_change_cameroun.csv"` | XAF par dollar, annuel et mensuel |
| `j_stg_ndvi` | `context.path_raw + "/ndvi_cmr_full.csv"` | 59 296 lignes : prévoir 1 à 2 minutes |
| `j_stg_meteo_horaire` | `context.path_generated + "/meteo_horaire_reference.csv"` | Tableau horaire dérivé des réponses figées de l'API Open-Meteo |
| `j_stg_abattage` | `context.path_generated + "/abattages/abattage.csv"` | Job modèle conseillé (petit fichier) |
| `j_stg_vente` | `context.path_generated + "/marche/vente.csv"` |  |
| `j_stg_releve_prix` | `context.path_generated + "/marche/releve_prix.csv"` |  |
| `j_stg_alimentation` | `context.path_generated + "/alimentation/alimentation.csv"` | Environ 110 000 lignes |
| `j_stg_ref_especes` | `context.path_generated + "/referentiel/ref_especes.csv"` | Référentiel |
| `j_stg_ref_races` | `context.path_generated + "/referentiel/ref_races.csv"` | Référentiel |
| `j_stg_ref_maladies` | `context.path_generated + "/referentiel/ref_maladies.csv"` | Référentiel |
| `j_stg_ref_vaccins` | `context.path_generated + "/referentiel/ref_vaccins.csv"` | Référentiel |
| `j_stg_ref_lieux` | `context.path_generated + "/referentiel/ref_lieux.csv"` | Référentiel |
| `j_stg_ref_marches` | `context.path_generated + "/referentiel/ref_marches.csv"` | Référentiel |
| `j_stg_ref_destinations` | `context.path_generated + "/referentiel/ref_destinations.csv"` | Référentiel |

## 3. Jobs PostgreSQL (4) : source `src_cheptel`

Composants : `tPostgresqlInput` (connexion `pg_db_src`) → `tMap` → `tPostgresqlOutput`. La requête convertit tout en texte.

**`j_stg_exploitation`** → `staging.stg_exploitation` (200 lignes attendues)
```sql
SELECT id_exploitation::text AS id_exploitation, nom_exploitation::text AS nom_exploitation, proprietaire::text AS proprietaire, pcode_departement::text AS pcode_departement, departement::text AS departement, region::text AS region, espece_principale::text AS espece_principale, systeme_elevage::text AS systeme_elevage, taille::text AS taille, date_creation::text AS date_creation, latitude::text AS latitude, longitude::text AS longitude, statut::text AS statut, updated_at::text AS updated_at FROM public.exploitation
```

**`j_stg_animal`** → `staging.stg_animal` (35292 lignes attendues)
```sql
SELECT id_animal::text AS id_animal, id_exploitation::text AS id_exploitation, espece::text AS espece, race::text AS race, sexe::text AS sexe, date_naissance::text AS date_naissance, type_entree::text AS type_entree, date_entree::text AS date_entree, date_sortie::text AS date_sortie, motif_sortie::text AS motif_sortie, cause_deces::text AS cause_deces, statut_reproducteur::text AS statut_reproducteur, updated_at::text AS updated_at FROM public.animal
```

**`j_stg_lot_volaille`** → `staging.stg_lot_volaille` (725 lignes attendues)
```sql
SELECT id_lot::text AS id_lot, id_exploitation::text AS id_exploitation, espece::text AS espece, type_production::text AS type_production, race::text AS race, date_mise_en_place::text AS date_mise_en_place, effectif_initial::text AS effectif_initial, date_sortie::text AS date_sortie, nb_morts_total::text AS nb_morts_total, motif_sortie::text AS motif_sortie, updated_at::text AS updated_at FROM public.lot_volaille
```

**`j_stg_suivi_lot_semaine`** → `staging.stg_suivi_lot_semaine` (11683 lignes attendues)
```sql
SELECT id_suivi::text AS id_suivi, id_lot::text AS id_lot, date_semaine::text AS date_semaine, nb_morts::text AS nb_morts, effectif_fin_semaine::text AS effectif_fin_semaine FROM public.suivi_lot_semaine
```

## 4. Jobs MySQL (2) : source `src_vaccinations`

Composants : `tMysqlInput` (**Db Version = MySQL 8**, paramètre JDBC `serverTimezone=UTC`) → `tMap` → `tPostgresqlOutput`.

**`j_stg_vaccin`** → `staging.stg_vaccin` (7 lignes attendues)
```sql
SELECT CAST(code_vaccin AS CHAR) AS code_vaccin, CAST(vaccin AS CHAR) AS vaccin, CAST(code_maladie AS CHAR) AS code_maladie, CAST(especes_cibles AS CHAR) AS especes_cibles, CAST(rappel_jours AS CHAR) AS rappel_jours, CAST(maladie AS CHAR) AS maladie FROM vaccin
```

**`j_stg_vaccination`** → `staging.stg_vaccination` (151413 lignes attendues)
```sql
SELECT CAST(id_vaccination AS CHAR) AS id_vaccination, CAST(id_exploitation AS CHAR) AS id_exploitation, CAST(id_animal AS CHAR) AS id_animal, CAST(id_lot AS CHAR) AS id_lot, CAST(espece AS CHAR) AS espece, CAST(code_vaccin AS CHAR) AS code_vaccin, CAST(vaccin AS CHAR) AS vaccin, CAST(maladie_ciblee AS CHAR) AS maladie_ciblee, CAST(numero_dose AS CHAR) AS numero_dose, CAST(date_vaccination AS CHAR) AS date_vaccination, CAST(date_rappel_prevue AS CHAR) AS date_rappel_prevue, CAST(date_rappel_realisee AS CHAR) AS date_rappel_realisee, CAST(id_veterinaire AS CHAR) AS id_veterinaire, CAST(nb_animaux_vaccines AS CHAR) AS nb_animaux_vaccines, CAST(updated_at AS CHAR) AS updated_at FROM vaccination
```

## 5. Job Excel : `j_stg_production`

Composant : `tFileInputExcel` (**Read excel2007 file format**, fichier `context.path_generated + "/production/production_lait_oeufs.xlsx"`, **trois feuilles** : `Production_2023`, `Production_2024`, `Production_2025`, en-tête sur 1 ligne). Colonnes lues en `String`. Ajoute les trois feuilles dans la liste des feuilles.

**Contrôle indispensable** : branche d'abord un `tLogRow` et regarde les premières lignes. Une date doit apparaître sous la forme `2024-01-01`, et les litres sous la forme `11.2`. Les défauts volontaires (dates en texte `03/05/2024`, litres avec virgule `12,5`) doivent **rester tels quels** : c'est le contrôle qualité qui les détecte. Si une date apparaît sous la forme d'un nombre comme `45292`, note-le et préviens-moi.

## 6. Jobs JSON (3)

Composants : `tFileList` (itération sur les fichiers) → `tFileInputJSON` → `tMap` → `tPostgresqlOutput`. **Read by : JsonPath**, **Loop JsonPath query : `$[*]`**, champs lus en `String`. Le fichier lu est `((String)globalMap.get("tFileList_1_CURRENT_FILEPATH"))`.

**`j_stg_mouvement`** : 3 fichiers `mouvements_2023.json` à `_2025.json` dans `context.path_generated + "/mouvements"`, masque `mouvements_*.json`. **Exécute d'abord `sql/09_ajustements_staging.sql`.**

| Colonne | JsonPath relatif |
|---|---|
| `id_mouvement` | `id_mouvement` |
| `id_exploitation` | `id_exploitation` |
| `espece` | `espece` |
| `nb_tetes` | `nb_tetes` |
| `type_mouvement` | `type_mouvement` |
| `date_depart` | `date_depart` |
| `date_arrivee` | `date_arrivee` |
| `origine_lieu` | `origine.lieu` |
| `origine_latitude` | `origine.latitude` |
| `origine_longitude` | `origine.longitude` |
| `destination_lieu` | `destination.lieu` |
| `destination_latitude` | `destination.latitude` |
| `destination_longitude` | `destination.longitude` |
| `distance_km` | `distance_km` |
| `id_transaction` | `id_transaction` |

`id_transaction` vaut `null` pour les mouvements qui ne sont pas des ventes : c'est normal. Si Talend refuse les chemins imbriqués, passe **Read by** en `XPath` (loop `/root/element`, champs `origine/lieu`, etc.).

**`j_stg_collier`** : un seul fichier `context.path_generated + "/gps/colliers.json"`, loop `$[*]`, champs = noms de colonnes (300 lignes).

**`j_stg_gps`** : 12 fichiers `gps_2025-01.json` à `gps_2025-12.json` dans `context.path_generated + "/gps"`, masque `gps_20*.json` (**pas** `colliers.json`). Loop `$[*]`, champs = noms de colonnes. Environ 396 000 lignes : prévoir plusieurs minutes. Dans `tPostgresqlOutput`, règle **Commit every = 10000**.

## 7. Jobs XML (2) : un seul fichier `veterinaires_interventions.xml`

Composant : `tFileInputXML`, fichier `context.path_generated + "/veterinaires/veterinaires_interventions.xml"`. **Deux jobs distincts**, chacun avec sa boucle.

**`j_stg_veterinaire`** : loop XPath `/reseau_veterinaire/veterinaires/veterinaire`

| Colonne | XPath relatif |
|---|---|
| `id_veterinaire` | `@id` |
| `nom` | `nom` |
| `prenom` | `prenom` |
| `statut` | `statut` |
| `specialite` | `specialite` |
| `date_prise_poste` | `date_prise_poste` |
| `pcode_departement` | `departement/@pcode` |
| `departement` | `departement` |

**`j_stg_intervention`** : loop XPath `/reseau_veterinaire/interventions/intervention`

| Colonne | XPath relatif |
|---|---|
| `id_intervention` | `@id` |
| `id_exploitation` | `exploitation` |
| `id_veterinaire` | `veterinaire` |
| `espece` | `espece` |
| `code_maladie` | `maladie/@code` |
| `maladie` | `maladie` |
| `date_signalement` | `date_signalement` |
| `date_intervention` | `date_intervention` |
| `nb_animaux_malades` | `nb_animaux_malades` |
| `nb_animaux_traites` | `nb_animaux_traites` |
| `nb_deces` | `nb_deces` |
| `cout_medicaments` | `cout_medicaments` |
| `honoraires` | `honoraires` |
| `devise` | `cout_medicaments/@devise` |
| `compte_rendu` | `compte_rendu` |

Compare ces champs avec les colonnes de `stg_intervention` de la section 9 : les noms doivent correspondre. `date_intervention` est **absent** pour quelques interventions (défaut volontaire) : Talend doit renvoyer `null`.

## 8. Job WAHIS : `j_stg_wahis` (4 fichiers)

Composants : `tFileList` → `tFileInputDelimited` → `tMap` → `tPostgresqlOutput`. Le fichier simulé est dans un autre dossier : fais **deux `tFileList`** (un par dossier) qui alimentent le même `tFileInputDelimited`, ou un job par dossier.

| Fichier | Dossier | Lignes |
|---|---|---|
| `wahis_quantitatif_2026-10-05.csv` | `context.path_raw` | 314 |
| `wahis_quantitatif_cameroun.csv` | `context.path_raw` | 41 |
| `wahis_quantitatif_complet.csv` | `context.path_raw` | 57 |
| `wahis_quantitatif_simule_2024_2025.csv` | `context.path_generated + "/wahis"` | 125 |

Dans le `tMap`, alimente `fichier_source` avec le nom du fichier lu : `((String)globalMap.get("tFileList_1_CURRENT_FILE"))`. **Ne dédoublonne pas et ne filtre pas ici** : la fusion, le dédoublonnage, le filtre sur les 3 régions et la déduction de `origine` se font dans l'étape SQL. Pour ne pas effacer un fichier avec le suivant, **n'utilise pas `Clear table`** : place un `tPostgresqlRow` `TRUNCATE staging.stg_wahis` **avant** la boucle, et laisse l'action sur `Default`.

## 9. Colonnes de chaque table de staging (dans l'ordre, sans `batch_id` ni `charge_le`)

- `stg_faostat_elevage` (15) : code_domaine, domaine, code_zone_m49, zone, code_element, element, code_produit_cpc, produit, code_annee, annee, unite, valeur, symbole, description_symbole, note
- `stg_faostat_prix` (18) : iso3, start_date, end_date, area_code, area_code_m49, area, item_code, item_code_cpc, item, element_code, element, year_code, year, months_code, months, unit, value, flag
- `stg_wahis` (20) : annee, semestre, region_mondiale, pays, division_administrative, maladie, genotype_serotype, categorie_animale, event_id, espece, outbreak_id, nouveaux_foyers, sensibles, unites_mesure, cas, mis_a_mort_elimines, abattus_commerciaux, morts, vaccines, fichier_source
- `stg_animal` (13) : id_animal, id_exploitation, espece, race, sexe, date_naissance, type_entree, date_entree, date_sortie, motif_sortie, cause_deces, statut_reproducteur, updated_at
- `stg_exploitation` (14) : id_exploitation, nom_exploitation, proprietaire, pcode_departement, departement, region, espece_principale, systeme_elevage, taille, date_creation, latitude, longitude, statut, updated_at
- `stg_lot_volaille` (11) : id_lot, id_exploitation, espece, type_production, race, date_mise_en_place, effectif_initial, date_sortie, nb_morts_total, motif_sortie, updated_at
- `stg_suivi_lot_semaine` (5) : id_suivi, id_lot, date_semaine, nb_morts, effectif_fin_semaine
- `stg_vaccination` (15) : id_vaccination, id_exploitation, id_animal, id_lot, espece, code_vaccin, vaccin, maladie_ciblee, numero_dose, date_vaccination, date_rappel_prevue, date_rappel_realisee, id_veterinaire, nb_animaux_vaccines, updated_at
- `stg_vaccin` (6) : code_vaccin, vaccin, code_maladie, especes_cibles, rappel_jours, maladie
- `stg_mouvement` (15) : id_mouvement, id_exploitation, espece, nb_tetes, type_mouvement, date_depart, date_arrivee, origine_lieu, origine_latitude, origine_longitude, destination_lieu, destination_latitude, destination_longitude, distance_km, id_transaction
- `stg_abattage` (13) : id_abattage, id_exploitation, id_animal, id_lot, espece, nb_animaux, date_abattage, poids_vif_kg, poids_carcasse_kg, abattoir, region, statut_inspection, updated_at
- `stg_production` (6) : date, id_exploitation, litres_lait, nb_vaches_lactation, nb_oeufs, nb_pondeuses
- `stg_alimentation` (11) : id_alimentation, date_semaine, id_exploitation, espece, id_lot, type_aliment, quantite_kg, prix_unitaire, devise, cout_total, updated_at
- `stg_vente` (16) : id_transaction, date_transaction, id_marche, marche, region, id_exploitation, id_animal, id_lot, espece, nb_tetes, poids_total_kg, prix_total, devise, destination_categorie, destination, updated_at
- `stg_releve_prix` (9) : id_releve, semaine, id_marche, espece, prix_moyen_kg_vif, prix_min_kg_vif, prix_max_kg_vif, nb_presentes, devise
- `stg_ndvi` (8) : date, adm_level, adm_id, pcode, n_pixels, vim, vim_avg, viq
- `stg_meteo_horaire` (5) : pcode_departement, departement, horodatage, temperature_c, humidite_pct
- `stg_veterinaire` (8) : id_veterinaire, nom, prenom, statut, specialite, date_prise_poste, pcode_departement, departement
- `stg_intervention` (15) : id_intervention, id_exploitation, id_veterinaire, espece, code_maladie, maladie, date_signalement, date_intervention, nb_animaux_malades, nb_animaux_traites, nb_deces, cout_medicaments, honoraires, devise, compte_rendu
- `stg_collier` (5) : id_collier, id_animal, id_exploitation, espece, date_pose
- `stg_gps` (8) : id_collier, id_animal, id_exploitation, horodatage, latitude, longitude, vitesse_kmh, batterie_pct
- `stg_taux_change` (17) : iso3, start_date, end_date, area_code, area_code_m49, area, element_code, element, iso_currency_code, currency, year_code, year, months_code, months, unit, value, flag
- `stg_ref_especes` (4) : code_espece, espece, groupe, production_principale
- `stg_ref_races` (3) : code_race, espece, race
- `stg_ref_maladies` (6) : code_maladie, maladie, sigle, categorie, especes_concernees, mot_cle_wahis
- `stg_ref_vaccins` (5) : code_vaccin, vaccin, code_maladie, especes_cibles, rappel_jours
- `stg_ref_lieux` (8) : id_lieu, departement, pcode_departement, region, pcode_region, chef_lieu, latitude, longitude
- `stg_ref_marches` (8) : id_marche, nom_marche, ville, pcode_departement, departement, region, latitude, longitude
- `stg_ref_destinations` (3) : id_destination, destination, categorie
