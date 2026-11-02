# Modèle de l'entrepôt (constellation)

Projet 11 · Élevage, santé animale et marchés · base `dwh_elevage`

Ce document complète `02_indicateurs_tracabilite.md` (indicateur → source → fait). Il décrit la matrice
processus × dimensions, les granularités et les décisions de modélisation. Les scripts correspondants sont
`sql/03_dimensions.sql`, `04_faits.sql`, `05_audit.sql`, `06_ml_nlp.sql` et `07_staging.sql`.
La correspondance fichier par fichier est dans `05_mapping_sources_dwh.md`.

## 1. Matrice processus × dimensions

| Fait (granularité) | Date | Exploit. | Espèce/race | Lieu | Maladie | Vaccin | Véto | Produit | Aliment | Marché | Devise |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fact_cheptel (exploitation × espèce × mois) | ✔ | ✔ | ✔ | ✔ | | | | | | | |
| fact_vaccination (une vaccination) | ✔✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | | | | |
| fact_intervention_veto (une intervention) | ✔✔ | ✔ | ✔ | ✔ | ✔ | | ✔ | | | | ✔ |
| fact_foyer_maladie (semestre × région × maladie × espèce) | ✔ | | ✔ | ✔ | ✔ | | | | | | |
| fact_production (exploitation × jour × produit) | ✔ | ✔ | ✔ | | | | | ✔ | | | |
| fact_abattage (une ligne d'abattage) | ✔ | ✔ | ✔ | ✔ | | | | | | | |
| fact_vente_prix (une transaction de marché) | ✔ | ✔ | ✔ | ✔ | | | | ✔ | | ✔ | ✔ |
| fact_releve_prix (marché × espèce × semaine) | ✔ | | ✔ | ✔ | | | | | | ✔ | ✔ |
| fact_alimentation (une ligne d'alimentation hebdomadaire) | ✔ | ✔ | ✔ | | | | | | ✔ | | ✔ |
| fact_mouvement (un déplacement) | ✔✔ | ✔ | ✔ | ✔✔ | | | | | | | |
| fact_gps_position (collier × horodatage) | ✔ | ✔ | ✔ | ✔ | | | | | | | |
| fact_environnement (département × jour) | ✔ | | | ✔ | | | | | | | |
| fact_reference_fao (année × élément × produit) | ✔ | | (✔) | | | | | | | | |

✔✔ = dimension à rôles multiples (rappel prévu et réalisé ; signalement et intervention ; départ et arrivée ; lieu d'origine et de destination).
Table d'appui : `ref_taux_change` (mois × devise), alimentée par la source 15.

## 2. Décisions de modélisation à justifier dans le dossier

1. **Constellation plutôt qu'étoile** : 13 processus de granularités différentes partagent des dimensions conformes (date, exploitation, espèce, lieu).
2. **SCD2** sur `dim_exploitation` (système d'élevage, taille, propriétaire, région, département, statut) et `dim_veterinaire` : clé de substitution, `date_debut`, `date_fin`, `est_courant`, `hash_diff`.
3. **Deux faits pour le marché à bétail** : `fact_vente_prix` (transaction, avec le lien vers l'exploitation, nécessaire à la marge de l'éleveur) et `fact_releve_prix` (prix de référence hebdomadaires par marché, qui alimentent la prévision ML 2).
4. **`fact_foyer_maladie` au semestre** : l'export WAHIS est agrégé. Les foyers sont rattachés à une ligne de `dim_lieu` de niveau `region`. Les lignes sans espèce prennent le membre « espèce inconnue » (`sk = -1`).
5. **Alimentation hebdomadaire** : la source fournit une semaine par ligne. Le fait garde cette granularité plutôt que de l'étaler artificiellement sur les jours.
6. **Additivité** : additives (décès, naissances, litres, kilos, coûts) ; semi-additives (effectifs : sommables sur les exploitations, pas sur le temps) ; non additives (taux, prix moyens, couverture : calculés dans `bi` à partir des numérateurs et dénominateurs stockés).
7. **Devises** : montants conservés en devise d'origine et en XAF, convertis au taux du mois de l'événement.
8. **Suppressions** : suppression logique (`est_supprime`) dans les faits transactionnels, pour la démonstration incrémentale du jour 3.
9. **Membre inconnu** (`sk = -1`) dans chaque dimension : rejet si la clé est obligatoire, rattachement sinon.
10. **Staging en texte brut** : toutes les colonnes de `staging` sont en `TEXT`. Le typage et les contrôles se font à la transformation, pour journaliser chaque rejet (type, format, plage) dans `audit.etl_reject`.
11. **Résultats ML/NLP** dans le schéma `ml`. Le NLP 2 résume les comptes rendus vétérinaires par région, WAHIS (quantitatif, sans texte) en complément.

## 3. Points tranchés grâce à l'inventaire des colonnes et aux vérifications

| Point | Résultat |
|---|---|
| Destination des ventes (indicateur 20) | Dans `vente.csv` (`destination_categorie`, `destination`). `abattage.csv` n'en a pas : champ retiré de `fact_abattage`. |
| Règle « export » | `ref_destinations.csv` : catégories `local`, `autre région`, `export`. Sont exportés : Nigeria, Tchad, Gabon, Guinée équatoriale. Règle : `est_export = (destination_categorie = 'export')`. |
| Sexe et statut reproducteur (indicateur 9) | Présents dans `animal.csv`. |
| Dates de rappel (indicateur 15) | `numero_dose`, `date_rappel_prevue` et `date_rappel_realisee` présents dans `vaccination.csv`. |
| `poids_vif_kg` des abattages (indicateur 10) | **Total de la ligne**, pas poids par animal (ex. 584 animaux → 1 226 kg, soit environ 2 kg chacun : des volailles). Formule : Σ `poids_vif_kg` ÷ Σ `nb_animaux`, **à ventiler par espèce** : un poulet de 2 kg et un bovin de plusieurs centaines de kg rendent la moyenne globale sans sens. |
| Niveau de WAHIS | **Région** : Adamaoua, Extrême-Nord et Ouest. Le Nord, présent dans l'export du 06/10, est hors périmètre et écarté par l'ETL. Les foyers se rattachent aux lignes `niveau = 'region'` de `dim_lieu`. |
| Indicateur 3 (couverture vaccinale) | Vue `bi.v_couverture_vaccinale` (`sql/08_vues_bi.sql`) : animaux à jour ÷ animaux éligibles, par exploitation, vaccin et mois, ruminants seulement. « À jour » = dernière dose + intervalle de rappel + 30 jours couvre la fin du mois. |
| Tolérance du rappel (indicateur 15) | `rappel_a_temps` = rappel réalisé au plus tard **30 jours après** la date prévue (même tolérance que la couverture). Sans tolérance, l'indicateur serait artificiellement proche de 0. |

## 4. Points encore ouverts

| Point | Comment le vérifier | Impact |
|---|---|---|
| Couverture de WAHIS | Les **trois exports** réels (`wahis_quantitatif_2026-10-05.csv`, `wahis_quantitatif_cameroun.csv`, `wahis_quantitatif_complet.csv`) sont fusionnés et dédoublonnés ; seules les 3 régions du périmètre et les années à partir de 2020 (début du calendrier) sont chargées. WAHIS ne publie rien après 2023 : 2024-2025 vient du fichier simulé `wahis_quantitatif_simule_2024_2025.csv` (`generators/15_wahis_simule.py`) | L'indicateur 11 et le NLP 2 couvrent les 3 régions ; la part réelle et la part simulée restent distinguables |
| Sens de la colonne `origine` | Déduite du **nom du fichier** : contient `simule` → `SIMULE`, sinon `WAHIS`. `pression_foyers_semestre.csv` est un facteur caché de la simulation : ce n'est **jamais** une source de l'ETL | Clé de `fact_foyer_maladie` |
| Les libellés `origine` et `destination` des mouvements existent-ils dans `ref_lieux` ? | Comparer les libellés | Sinon `lieu_*_sk = -1` et le libellé est conservé |
| Espèce rattachée au lait (`nb_vaches_lactation`) | Règle de gestion | Hypothèse retenue : Bovins pour le lait, Volailles pour les œufs |
