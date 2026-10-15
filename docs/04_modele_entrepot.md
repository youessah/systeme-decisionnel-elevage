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

## 3. Points tranchés grâce à l'inventaire des colonnes

| Point | Résultat |
|---|---|
| Destination des ventes (indicateur 20) | Dans `vente.csv` (`destination_categorie`, `destination`). `abattage.csv` n'en a pas : champ retiré de `fact_abattage`. |
| Sexe et statut reproducteur (indicateur 9) | Présents dans `animal.csv`. |
| Dates de rappel (indicateur 15) | `numero_dose`, `date_rappel_prevue` et `date_rappel_realisee` présents dans `vaccination.csv`. |

## 4. Points encore ouverts

| Point | Comment le vérifier | Impact |
|---|---|---|
| Valeurs de `destination_categorie` (laquelle signifie « export » ?) | `ref_destinations.csv` | Règle `est_export` |
| `poids_vif_kg` d'`abattage.csv` : total de la ligne ou poids par animal ? | Comparer sur des lignes avec `nb_animaux > 1` | Formule de l'indicateur 10 |
| Niveau de la colonne `Division administrative` de WAHIS (région ou département) | `generators/inspect_wahis.py` | Rattachement à `dim_lieu` |
| Les lieux d'origine et de destination des mouvements (`origine`, `destination`) existent-ils dans `ref_lieux` ? | Comparer les libellés | Sinon `lieu_*_sk = -1` et le libellé est conservé |
| Espèce rattachée au lait (`nb_vaches_lactation`) | Règle de gestion | Hypothèse retenue : Bovins pour le lait, Volailles pour les œufs |
