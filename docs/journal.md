vérification des sources publiques

Périmètre : 6 départements retenus (Vina et Mbéré, Diamaré et Mayo-Tsanaga, Mifi et Menoua).

Source 12 · Open-Meteo : OK
Test 1 : l'archive horaire de Ngaoundéré (janvier 2023) répond avec température et humidité.
Source 15 · Taux de change
Test 2 (6 mars 2024, base euro) : OK, xaf = 655,957 (taux fixe XAF/EUR).
Test 3 (15 juin 2023, ancien format) : erreur. Plan B : XAF dérivé de l'euro par le taux fixe ; taux USD historiques tirés du fichier FAO cmr_faostat_exchange_rates.csv (à télécharger) ; l'API sert aux dates récentes (démonstration incrémentale). NGN abandonné (devise optionnelle).
Source 11 · NDVI : OK
Jeu HDX « Cameroon: NDVI at Subnational Level » (WFP/NASA MODIS), ID 6da39ddb-76b0-4510-8648-c0f3fb15d52b.
Période 2002-07-01 à 2026-09-20, mise à jour mensuelle. Fichier cmr-ndvi-subnat-full.csv → data/raw/ndvi_cmr_full.csv.
59 296 lignes = 68 unités (10 régions + 58 départements) × 872 décades. Colonnes : date, adm_level, adm_id, PCODE, n_pixels, vim, vim_avg, viq.
Table de correspondance administrative : OK
Fichier COD-AB cmr_admin_boundaries.xlsx → data/raw/cmr_admin_codes.xlsx, feuille cmr_admin2.
Les noms sont dans adm2_name1 (adm2_name est vide). Régions écrites en anglais (Adamawa, Far-North, West).
Codes : Vina CM001005, Mbéré CM001004, Diamaré CM004001, Mayo-Tsanaga CM004006, Mifi CM008006, Menoua CM008005.
Source 2 · Prix FAO producteurs : exploitable comme repère seulement
Jeu HDX cmr-faostat-food-prices, fichier cmr_faostat_producer_prices.csv → data/raw/faostat_prix_cameroun.csv (4 561 lignes, 18 colonnes).
Éléments : indice (base 2014-2016 = 100), prix en LCU, SLC et USD par tonne.
Indice disponible 1991-2025 pour les produits animaux. Prix absolus uniquement en 1992-2003 (bovin, poulet, lait, œufs) et en 2003 (ovin, caprin, porcin). Aucun prix mensuel pour les animaux.
Indice 2003 identique (69,99) pour tous les produits : valeur estimée (drapeau E).
Estimation reconstituée 2023 (XAF/kg) : bovin ≈ 635, ovin ≈ 836, caprin ≈ 1 205, poulet ≈ 1 732 à 2 046, lait ≈ 238, œufs ≈ 1 362. À étiqueter « estimation ». Codes M49 et CPC avec apostrophe à retirer à l'ETL.
À comparer avec le jeu WFP « Cameroon - Food Prices » si celui-ci contient des produits d'élevage.
Source 1 · FAOSTAT élevage : à confirmer
Interface FAOSTAT QCL : élément « Réserves », dernière année visible 2024. Bovins 5 941 769 (I), caprins 6 632 453 (I), ovins 3 551 761 (E), poulets 45 575 milliers (I).
Fichier à placer dans data/raw/faostat_elevage_cameroun.csv ; inspection à faire.
Source 3 · WAHIS : données réelles pour 2022 et 2023
Liste « Gestion des événements » : 8 événements Cameroun (2006 à 2022), aucun en 2023-2025 (influenza aviaire, variole du singe, peste équine, etc.).
Tableau de bord « Données quantitatives » (rapports semestriels inclus) : données par région pour 2022 et 2023, rien pour 2024-2025.
Filtres : Cameroun, Adamaoua + Extrême-Nord + Ouest, 7 maladies, espèces ruminants.
2022 : sensibles 2 334, cas 799, morts 20.
2023 : sensibles 1 073, cas 625, morts 36 (S1 : 626 / 441 / 15 ; S2 : 447 / 184 / 21).
Structure de l'export : outbreak_id vide = rapport semestriel ; rempli = notification immédiate ou rapport de suivi. « Nouveaux foyers » = foyers débutés pendant le semestre. Ils sont portés par des lignes dont l'espèce est vide, donc un filtre d'espèce les supprime. Un foyer touchant plusieurs espèces n'est compté qu'une fois.
Export téléchargé : Données quantitatives 2026-10-06.csv, 6 365 octets