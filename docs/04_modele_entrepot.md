# Modèle de l'entrepôt (constellation)

Projet 11 · Élevage, santé animale et marchés

Ce document complète `02_indicateurs_tracabilite.md` (indicateur → source → fait). Il décrit la matrice
processus × dimensions, les granularités et les décisions de modélisation. Les scripts correspondants sont
`sql/03_dimensions.sql`, `04_faits.sql`, `05_audit.sql` et `06_ml_nlp.sql` (base `dwh_elevage`).

## 1. Matrice processus × dimensions

| Fait (granularité) | Date | Exploit. | Espèce/race | Lieu | Maladie | Vaccin | Véto | Produit | Aliment | Marché | Devise |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fact_cheptel (exploitation × espèce × mois) | ✔ | ✔ | ✔ | ✔ | | | | | | | |
| fact_vaccination (une dose) | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | | | | | |
| fact_intervention_veto (une intervention) | ✔✔ | ✔ | ✔ | ✔ | ✔ | | ✔ | | | | ✔ |
| fact_foyer_maladie (semestre × division × maladie × espèce) | ✔ | | ✔ | ✔ | ✔ | | | | | | |
| fact_production (exploitation × jour × produit) | ✔ | ✔ | ✔ | | | | | ✔ | | | |
| fact_abattage (un lot abattu) | ✔ | ✔ | ✔ | ✔ | | | | | | | |
| fact_vente_prix (une vente au marché) | ✔ | ✔ | ✔ | ✔ | | | | ✔ | | ✔ | ✔ |
| fact_alimentation (exploitation × jour × aliment) | ✔ | ✔ | ✔ | | | | | | ✔ | | ✔ |
| fact_mouvement (un déplacement) | ✔✔ | ✔ | ✔ | ✔✔ | | | | | | | |
| fact_gps_position (collier × horodatage) | ✔ | ✔ | ✔ | ✔ | | | | | | | |
| fact_environnement (lieu × jour) | ✔ | | | ✔ | | | | | | | |

✔✔ = dimension à rôles multiples (date de signalement et d'intervention ; date de départ et de retour ; lieu d'origine et de destination).
Table d'appui : `ref_taux_change` (date × devise), alimentée par la source 15.

## 2. Décisions de modélisation à justifier dans le dossier

1. **Constellation plutôt qu'étoile** : 11 processus de granularités différentes partagent des dimensions conformes (date, exploitation, espèce, lieu).
2. **SCD2** sur `dim_exploitation` (zone, taille, propriétaire, statut sanitaire) et `dim_veterinaire` (statut, département) : clé de substitution, `date_debut`, `date_fin`, `est_courant`, `hash_diff`.
3. **`fact_vente_prix` à la transaction** : la marge de l'éleveur (indicateur 18 = ventes − alimentation − traitements) exige le lien vente → exploitation. L'agrégation par marché × espèce × jour se fait dans la couche BI (schéma `bi`).
4. **`fact_foyer_maladie` au semestre** : l'export WAHIS est agrégé (nouveaux foyers par semestre et par division, certaines lignes sans espèce). Ces lignes sont rattachées au membre « espèce inconnue » (`sk = -1`).
5. **Additivité** : additives (décès, naissances, litres, kilos, coûts) ; semi-additives (effectifs : sommables sur les exploitations, pas sur le temps) ; non additives (taux, prix moyens, couverture : calculés dans `bi` à partir des numérateurs et dénominateurs stockés).
6. **Devises** : montants conservés en devise d'origine et en XAF, convertis au taux du jour de l'événement.
7. **Suppressions** : suppression logique (`est_supprime`) dans les faits transactionnels, pour la démonstration incrémentale du jour 3.
8. **Membre inconnu** (`sk = -1`) dans chaque dimension : rejet si la clé est obligatoire, rattachement sinon.
9. **Résultats ML/NLP** dans le schéma `ml`, métriques dans `ml.ml_metrique`. Le NLP 2 résume les comptes rendus vétérinaires par région, WAHIS en complément.

## 3. Points à confirmer sur les données générées

| Point | Où le vérifier | Impact |
|---|---|---|
| Le champ `destination` (local / autre région / export) existe-t-il dans S10 (ventes) ou dans S7 (abattages) ? | `docs/colonnes_sources.txt` | Indicateur 20 : la traçabilité le place dans S10 ; `fact_vente_prix.destination` est prévu, `fact_abattage.destination` reste facultatif |
| S5 est-il au niveau animal (`id_animal`, `numero_dose`) ? | idem | Granularité de `fact_vaccination` |
| S5 contient-il `date_rappel_prevue` et `date_rappel_realisee` ? | idem | Indicateur 15 |
| S4 contient-il `sexe` et `statut_reproducteur` ? | idem | Indicateur 9 |
| Signification de la colonne `origine` de WAHIS | `generators/inspect_wahis.py` | Clé de `fact_foyer_maladie` |
