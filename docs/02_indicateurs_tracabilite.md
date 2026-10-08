# Indicateurs et matrice de traçabilité

**Projet 11 · Élevage, santé animale et marchés** · Version 1.0 · 04/10/2026

Ce document définit les **25 indicateurs** imposés par le cahier des charges (formule, unité, périodicité), relie chacun à ses **sources**, ses **champs** et ses **tables de fait**, puis liste les **champs minimaux** que les générateurs de données devront produire.

**Légende des sources** : S1 FAOSTAT élevage · S2 FAOSTAT prix · S3 WAHIS · S4 Cheptel (PostgreSQL) · S5 Vaccinations (MySQL) · S6 Mouvements (JSON) · S7 Abattages (CSV) · S8 Lait et œufs (Excel) · S9 Alimentation (CSV) · S10 Marché à bétail (CSV) · S11 NDVI (CSV) · S12 Météo (API) · S13 Vétérinaires (XML) · S14 GPS (JSON) · S15 Taux de change (API).

**Dimensions communes** (sauf indication contraire) : date, exploitation, espèce, lieu (région, département). Les filtres du tableau de bord reposent sur elles.

---

## Page 1 · Synthèse

| N° | Indicateur | Formule | Unité · périodicité | Sources et champs | Fait |
|---|---|---|---|---|---|
| 1 | Effectif du cheptel | Nombre d'animaux présents en fin de période | Têtes · mensuel | S4 : id_animal ou effectif, espèce, date_entrée, date_sortie | `fact_cheptel` |
| 2 | Taux de mortalité | Décès de la période ÷ effectif moyen de la période × 100 | % · mensuel, annuel | S4 : date_décès, effectif début et fin | `fact_cheptel` |
| 3 | Couverture vaccinale | Animaux à jour du vaccin ciblé ÷ animaux éligibles × 100 | % · mensuel | S5 : id_animal, vaccin, date_vaccination ; S4 : espèce, date_naissance (éligibilité) | `fact_vaccination` + `fact_cheptel` |
| 4 | Production laitière | Somme des litres de lait produits | Litres · journalier, mensuel | S8 : date, id_exploitation, espèce, litres | `fact_production` |
| 5 | Prix moyen au kilo | Σ (prix total) ÷ Σ (poids vendu en kg), pondéré par le volume | XAF/kg · mensuel | S10 : prix_total, poids_total_kg, devise ; S15 : taux | `fact_vente_prix` |

## Page 2 · Cheptel et production

| N° | Indicateur | Formule | Unité · périodicité | Sources et champs | Fait |
|---|---|---|---|---|---|
| 6 | Cheptel par espèce | Indicateur 1 ventilé par espèce | Têtes · mensuel | S4 : espèce | `fact_cheptel` |
| 7 | Taux de croissance du cheptel | (effectif fin − effectif début) ÷ effectif début × 100 | % · annuel | S4 | `fact_cheptel` |
| 8 | Naissances par an | Nombre de naissances (éclosions pour les volailles) de l'année | Têtes · annuel | S4 : date_naissance, type_entrée = naissance | `fact_cheptel` |
| 9 | Taux de reproduction | Naissances de l'année ÷ femelles reproductrices × 100 | % · annuel | S4 : sexe, statut_reproducteur, date_naissance | `fact_cheptel` |
| 10 | Poids moyen à l'abattage | Σ poids vif ÷ nombre d'animaux abattus | kg · mensuel | S7 : poids_vif_kg, espèce, date_abattage | `fact_abattage` |

## Page 3 · Santé animale

| N° | Indicateur | Formule | Unité · périodicité | Sources et champs | Fait |
|---|---|---|---|---|---|
| 11 | Nombre de foyers de maladies | Somme des nouveaux foyers (foyers débutés pendant la période) | Foyers · semestriel | S3 : année, semestre, division administrative, maladie, nouveaux foyers (lignes sans espèce), colonne `origine` | `fact_foyer_maladie` |
| 12 | Taux de morbidité | Animaux malades ÷ animaux exposés × 100 | % · mensuel | S13 : nb_animaux_malades ; S4 : effectif | `fact_intervention_veto` + `fact_cheptel` |
| 13 | Délai d'intervention vétérinaire | Moyenne de (date_intervention − date_signalement) | Heures · mensuel | S13 : date_signalement, date_intervention | `fact_intervention_veto` |
| 14 | Coût des traitements | Σ (médicaments + honoraires) | XAF · mensuel | S13 : coût_médicaments, honoraires, devise ; S15 | `fact_intervention_veto` |
| 15 | Taux de rappel vaccinal | Rappels réalisés dans les délais ÷ rappels dus × 100 | % · mensuel | S5 : numéro_dose, date_rappel_prévue, date_rappel_réalisée | `fact_vaccination` |

*Dimensions supplémentaires* : maladie, vaccin, vétérinaire.

## Page 4 · Marchés

| N° | Indicateur | Formule | Unité · périodicité | Sources et champs | Fait |
|---|---|---|---|---|---|
| 16 | Prix par espèce | Indicateur 5 ventilé par espèce (et comparaison aux prix de référence S2) | XAF/kg · mensuel | S10 ; S2 : prix annuels | `fact_vente_prix` |
| 17 | Volume vendu | Σ poids vendu (kg) et nombre de têtes | kg, têtes · mensuel | S10 : poids_total_kg, nb_têtes | `fact_vente_prix` |
| 18 | Marge de l'éleveur | Revenus des ventes − coûts d'alimentation − coûts de traitement | XAF · mensuel, par exploitation | S10 : prix_total, id_exploitation ; S9 : coût ; S13 : coûts | `fact_vente_prix`, `fact_alimentation`, `fact_intervention_veto` |
| 19 | Abattages par mois | Nombre d'animaux abattus dans le mois | Têtes · mensuel | S7 : date_abattage, espèce | `fact_abattage` |
| 20 | Part des ventes exportées | Volume (kg) vendu à destination « export » ÷ volume total vendu × 100 | % · mensuel | S10 : destination (local, autre région, export) | `fact_vente_prix` |

*Dimensions supplémentaires* : marché, devise.

## Page 5 · Alimentation et environnement

| N° | Indicateur | Formule | Unité · périodicité | Sources et champs | Fait |
|---|---|---|---|---|---|
| 21 | Consommation de fourrage | Σ quantité de fourrage consommée | kg · mensuel | S9 : type_aliment, quantité_kg | `fact_alimentation` |
| 22 | Coût d'alimentation par animal | Σ coût d'alimentation ÷ effectif moyen | XAF/animal · mensuel | S9 : coût, devise ; S4 : effectif ; S15 | `fact_alimentation` + `fact_cheptel` |
| 23 | Indice de pâturage | NDVI moyen de la zone sur la période | Sans unité (0 à 1) · décadaire ou mensuel | S11 : zone, date, ndvi | `fact_environnement` |
| 24 | Distances de transhumance | Distance moyenne et totale origine → destination des mouvements de type transhumance | km · saisonnier, annuel | S6 : type_mouvement, coordonnées origine et destination, distance_km | `fact_mouvement` |
| 25 | Jours de stress thermique | Nombre de jours où le THI journalier dépasse le seuil | Jours · mensuel | S12 : température et humidité horaires, zone | `fact_environnement` |

**Définition de l'indicateur 25** : indice température-humidité (THI) = (1,8 × T + 32) − (0,55 − 0,0055 × HR) × (1,8 × T − 26), avec T la température en °C et HR l'humidité relative en %. Un jour compte comme « stress thermique » si son THI maximal dépasse le seuil retenu. Valeur de départ : **72**, seuil classique pour les bovins laitiers, à justifier dans le dossier de conception (les seuils varient selon l'espèce).

---

## Fonctionnalités ML et NLP : données nécessaires

| Fonctionnalité | Variables d'entrée | Cible ou sortie | Remarque pour les générateurs |
|---|---|---|---|
| ML 1 : risque sanitaire et mortalité | Taux de vaccination, délais d'intervention, THI, foyers voisins, effectif | Décès ou foyer à 30 jours | La mortalité doit dépendre réellement de ces facteurs |
| ML 2 : prévision des prix et volumes | Série mensuelle des prix et volumes par espèce, jours fériés, change | Prix et volumes futurs | Saisonnalité et tendance à reproduire |
| ML 3 : anomalies GPS | Vitesse, distance parcourue, immobilité, sortie de zone | Anomalie (maladie ou vol) | Anomalies étiquetées pour l'évaluation |
| NLP 1 : symptômes et maladies | Comptes rendus vétérinaires (XML, texte libre en français) | Symptômes et maladies extraits | 50 à 100 textes annotés à la main |
| NLP 2 : résumé des foyers | Commentaires épidémiologiques des fiches d'événements WAHIS (texte réel, peu d'événements) et textes générés par région | Résumé par région | L'export quantitatif ne contient pas de texte ; langue à préciser (WAHIS surtout en anglais) |

---

## Champs minimaux à prévoir dans chaque source

C'est le résultat clé de la traçabilité : si un champ de ce tableau manque dans un générateur, un indicateur devient incalculable.

| Source | Champs minimaux |
|---|---|
| **S4 Cheptel** | id_animal (ou effectif par lot pour les volailles), id_exploitation, espèce, race, sexe, date_naissance, type_entrée (naissance, achat), date_entrée, date_sortie, motif_sortie (décès, vente, abattage), statut_reproducteur, updated_at |
| **S5 Vaccinations** | id_vaccination, id_animal ou id_lot, id_exploitation, vaccin, maladie_ciblée, numéro_dose, date_vaccination, date_rappel_prévue, date_rappel_réalisée, id_vétérinaire, updated_at |
| **S6 Mouvements** | id_mouvement, id_exploitation, espèce, nb_têtes, type_mouvement (transhumance, vente, achat), date_départ, date_arrivée, lat/lon origine, lat/lon destination, distance_km |
| **S7 Abattages** | id_abattage, id_exploitation, espèce, date_abattage, poids_vif_kg, poids_carcasse_kg, abattoir, région |
| **S8 Lait et œufs** | date, id_exploitation, espèce, litres_lait, nb_œufs |
| **S9 Alimentation** | date, id_exploitation, espèce, type_aliment, quantité_kg, coût, devise |
| **S10 Marché à bétail** | id_transaction, date, marché, région, id_exploitation, espèce, nb_têtes, poids_total_kg, prix_total, devise, **destination** (local, autre région, export) |
| **S11 NDVI** | date, zone (région ou département), ndvi |
| **S12 Météo** | horodatage, zone, température, humidité relative |
| **S13 Vétérinaires** | id_intervention, id_vétérinaire, id_exploitation, espèce, maladie, date_signalement, date_intervention, nb_animaux_malades, coût_médicaments, honoraires, devise, **compte_rendu** (texte libre) |
| **S14 GPS** | id_collier, id_animal, id_exploitation, horodatage, lat, lon, vitesse (optionnel), indicateur d'anomalie (réservé à l'évaluation, non chargé dans l'entrepôt) |
| **S3 WAHIS** (export « Données quantitatives ») | année, semestre, division administrative, maladie, génotype/sous-type, catégorie animale, espèce, nouveaux foyers, sensibles, cas, mis à mort, morts, vaccinés. Valeurs manquantes écrites `-` ; les nouveaux foyers sont portés par des lignes dont l'espèce est vide |
| **S2 FAOSTAT prix** | pays, produit, année, prix, devise |
| **S1 FAOSTAT élevage** | pays, espèce, année, effectif |
| **S15 Taux de change** | date, devise_source, devise_cible, taux |

### Trois décisions de conception qui en découlent

1. **S10 est une table de transactions** (une ligne par vente), et non un simple relevé de prix : c'est ce qui permet de calculer la marge par exploitation (18), les volumes (17) et la part exportée (20).
2. **S4 contient le sexe et le statut reproducteur**, nécessaires au taux de reproduction (9), et les motifs de sortie, nécessaires à la mortalité (2).
3. **Les suppressions** sont simulées dans S4 et S5 (animal retiré, vaccination annulée) pour démontrer leur détection lors de l'ETL incrémental.

---

## Points à valider avant la phase 2

- [ ] Disponibilité et licence de S1, S2, S3, S11, S12, S15 pour le Cameroun et la période 2023 à 2025.
- [ ] Seuil THI et méthode de calcul journalier (indicateur 25).
- [ ] Définition de l'éligibilité vaccinale (indicateur 3) : quelles espèces pour quels vaccins.
- [x] Départements retenus : Vina et Mbéré (Adamaoua), Diamaré et Mayo-Tsanaga (Extrême-Nord), Mifi et Menoua (Ouest).
