# Vérification des sources publiques

**Projet 11 · Phase 2, étape 1** · Recherches effectuées le 04/10/2026

Ce document recense, pour chacune des 6 sources publiques, où la télécharger, ce qu'il faut en extraire, sa licence, ses risques et son **plan B**.

**Légende** : ✅ confirmé par recherche · ⚠️ à tester sur ta machine (page dynamique, couverture du Cameroun ou adresse déduite d'un modèle).

**Limites de cette vérification** : je n'ai pas pu télécharger les fichiers moi-même, ni ouvrir les interfaces dynamiques (FAOSTAT, WAHIS). La disponibilité des données *spécifiques au Cameroun et à 2023-2025* est donc à confirmer par le test rapide de la section 4.

---

## 1. Synthèse

| N° | Source | Accès | Licence | Statut | Risque |
|---|---|---|---|---|---|
| 1 | FAOSTAT élevage | Téléchargement | CC BY 4.0 | ✅ existe, ⚠️ dernière année pour le Cameroun | Faible |
| 2 | FAOSTAT prix producteurs | Téléchargement | CC BY 4.0 | ✅ existe, ⚠️ couverture Cameroun | Moyen |
| 3 | WAHIS | Interface publique | Accès public sans restriction | ⚠️ nombre de foyers pour le Cameroun inconnu | **Élevé** |
| 11 | NDVI (WFP/NASA) | Téléchargement HDX | CC BY (à confirmer sur la page Cameroun) | ✅ téléchargé, complet (2002 à sept. 2026) | Faible |
| 12 | Open-Meteo | API sans clé | Gratuit non commercial, attribution | ✅ endpoint et variables confirmés | Faible |
| 15 | Taux de change | API sans clé | CC0 | ✅ existe, ⚠️ historique 2023 | Faible |

---

## 2. Détail par source

### Source 1 : FAOSTAT élevage (domaine QCL « Crops and livestock products »)

- **Liens**
  - Interface : https://www.fao.org/faostat/en/#data/QCL ⚠️ (adresse déduite du modèle des autres domaines)
  - Fichier complet (CSV dans un ZIP, format large) : https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_All_Data_NOFLAG.zip ✅
  - Catalogue de tous les jeux, avec adresses de téléchargement : https://bulks-faostat.fao.org/production/datasets_E.json ✅
- **À extraire** : pays = Cameroon ; élément = Stocks (effectifs) ; produits = bovins, ovins, caprins, poulets. Le fichier mondial est lourd : on le filtre en Python et on conserve un petit CSV « Cameroun ».
- **Licence** : CC BY 4.0, avec mention obligatoire de la source (voir §3). ✅
- **Risque** : les dernières années ne sont pas toujours publiées. Si 2024 ou 2025 manquent, on le signale et on s'en sert comme tendance historique (le projet n'en a besoin que comme repère).
- **Plan B** : prendre les années disponibles les plus récentes ; ou télécharger le jeu « Cameroon » déjà filtré sur la plateforme HDX (voir source 2).

### Source 2 : FAOSTAT prix des produits animaux (domaine PP « Producer Prices »)

- **Liens**
  - Interface : https://www.fao.org/faostat/en/#data/PP ✅
  - Documentation : https://files-faostat.fao.org/production/PP/PP_e.pdf ✅
  - Jeu « Cameroon - Food Prices » (dont Producer Prices) : https://data.humdata.org/ → rechercher « Cameroon Food Prices » ✅ (confirmé dans le répertoire ReliefWeb : https://response.reliefweb.int/cameroon/data?page=0)
- **Ce que les données contiennent** : prix reçus par les producteurs, annuels depuis 1991, mensuels depuis 2010 pour une partie des pays. Les prix mensuels sont en monnaie locale uniquement. ✅
- **À extraire** : pays = Cameroon ; produits : viande bovine, ovine, caprine, poulet, lait, œufs ; unité = monnaie locale par tonne.
- **Licence** : CC BY 4.0 (FAOSTAT). ✅
- **Risque** : tous les produits ne sont pas couverts pour le Cameroun, et les noms de produits ont changé avec les révisions de classification (vérifier les libellés dans le fichier).
- **Plan B** : si peu de produits sont disponibles, ne retenir que ceux qui existent (au minimum bovins et poulets) ; les autres prix de référence seront renseignés par un jeu synthétique clairement signalé. Cette source ne sert que de **repère** pour comparer les prix du marché simulé (indicateur 16).

### Source 3 : WAHIS (foyers de maladies, WOAH)

- **Liens**
  - Interface publique : https://wahis.woah.org/ ✅
  - Présentation officielle : https://www.woah.org/en/what-we-do/animal-health-and-welfare/disease-data-collection/world-animal-health-information-system/ ✅
  - Aide : https://wahis-support.woah.org ✅
  - Mode d'emploi du téléchargement par rapport (CSV) : https://www.loicleray.com/wahis-download ✅
- **Ce qu'on sait** : WAHIS publie les données officielles validées depuis 2005, accessibles au public sans restriction. Les rapports sont téléchargeables en CSV ; pour un export complet d'une maladie, il faut contacter l'OMSA. ✅
- **À extraire** : pour le Cameroun (et éventuellement les pays voisins) : maladie, espèce, date de début, localisation, nombre de cas et de décès, description. Maladies cibles : fièvre aphteuse, péripneumonie contagieuse bovine, peste des petits ruminants, charbon bactéridien, maladie de Newcastle, influenza aviaire, dermatose nodulaire contagieuse.
- **Licence** : accès public ; citer « WOAH, WAHIS ». L'OMSA décline toute responsabilité sur l'exactitude des données retraitées. ✅
- **Risques** : c'est la source la plus incertaine. Le nombre de foyers déclarés par le Cameroun sur 2023-2025 peut être faible. Les rapports sont téléchargés **un par un**, et les textes sont en anglais.
- **Plan B (recommandé dès maintenant)** : approche **hybride**. On télécharge les rapports réels disponibles pour le Cameroun (et la sous-région si nécessaire), puis on complète avec des foyers synthétiques **de même structure**, avec une colonne `origine` (`WAHIS` ou `SYNTHETIQUE`). Cette colonne est affichée dans le tableau de bord et expliquée dans le dossier. Le résumé NLP (NLP 2) fonctionne de la même façon sur les deux types de lignes.

### Source 11 : Pâturages (NDVI)

**Statut : ✅ vérifié et téléchargé le 04/10/2026.**

- **Jeu** : « Cameroon: NDVI at Subnational Level » sur HDX, page https://data.humdata.org/dataset/cmr-ndvi-subnational ✅
- **Fichier retenu** : `cmr-ndvi-subnat-full.csv` (3,7 Mo, série complète). Le second fichier, `cmr-ndvi-subnat-5ytd.csv`, ne contient que les cinq dernières années glissantes et n'est pas utilisé. Rangé dans `data/raw/ndvi_cmr_full.csv`.
- **Métadonnées** : période du 1er juillet 2002 au 20 septembre 2026, mise à jour mensuelle, modifié le 23/09/2026, source NASA (MODIS) et WFP, identifiant du jeu `6da39ddb-76b0-4510-8648-c0f3fb15d52b`. ✅
- **Structure du fichier** : 59 296 lignes et 8 colonnes : `date`, `adm_level`, `adm_id`, `PCODE`, `n_pixels`, `vim` (NDVI de la décade), `vim_avg` (moyenne de long terme), `viq` (anomalie en %). ✅
- **Contrôle arithmétique** : 59 296 = 68 unités × 872 décades. Les 68 unités correspondent à **10 régions et 58 départements** (chiffres du référentiel officiel COD-AB), et les 872 décades couvrent juillet 2002 à septembre 2026 à raison de 3 par mois. Le fichier est donc complet et sans trou apparent. ✅
- **Point d'attention** : le fichier ne contient **que des codes** (`PCODE`, `adm_id`), pas de noms. Il faut une table de correspondance code → nom pour retrouver Vina, Mbéré, Diamaré, Mayo-Tsanaga, Mifi et Menoua. Elle est fournie par le jeu de référence **COD-AB** (limites administratives) ou **COD-PS** (statistiques de population), publiés sur HDX : https://data.humdata.org/dataset/cod-ab-cmr et https://data.humdata.org/dataset/cod-ps-cmr ✅
- **Licence** : ⚠️ à relever dans la page de métadonnées HDX (les autres pays de la même série sont en « Creative Commons Attribution International »).
- **Plan B** : en cas de problème de correspondance, générer un NDVI synthétique saisonnier signalé comme tel (peu probable : le fichier est complet).

### Source 12 : Météo (Open-Meteo, API)

- **Liens**
  - Documentation : https://open-meteo.com/en/docs/historical-weather-api ✅
  - Endpoint de l'archive : https://archive-api.open-meteo.com/v1/archive ✅
- **Ce que l'API fournit** : historique horaire depuis 1940 (données de réanalyse, c'est-à-dire un modèle météo recalé sur les observations, et non des mesures de station). Variables utiles : `temperature_2m` et `relative_humidity_2m`. Pas de clé, pas de compte. ✅
- **Licence** : gratuit pour un usage non commercial, ce qui est ton cas ; attribution à citer. Le volume demandé (6 lieux × 3 ans) est minuscule face aux limites d'usage équitable (de l'ordre de 10 000 appels par jour selon un descriptif tiers). ✅ / ⚠️ vérifier la page des conditions d'utilisation.
- **À extraire** : une requête par département, avec les coordonnées du chef-lieu :

| Département | Chef-lieu | Latitude | Longitude |
|---|---|---|---|
| Vina | Ngaoundéré | 7,32 | 13,58 |
| Mbéré | Meiganga | 6,52 | 14,37 |
| Diamaré | Maroua | 10,59 | 14,32 |
| Mayo-Tsanaga | Mokolo | 10,74 | 13,80 |
| Mifi | Bafoussam | 5,48 | 10,42 |
| Menoua | Dschang | 5,44 | 10,05 |

*(coordonnées approximatives, suffisantes pour une maille météo ; à confirmer sur une carte)*

- **Test à coller dans ton navigateur** (Ngaoundéré, janvier 2023) :
  ```
  https://archive-api.open-meteo.com/v1/archive?latitude=7.32&longitude=13.58&start_date=2023-01-01&end_date=2023-01-31&hourly=temperature_2m,relative_humidity_2m
  ```
  Tu dois voir un JSON avec des tableaux `time`, `temperature_2m` et `relative_humidity_2m`.
- **Risque** : faible. Prévoir une pause entre les appels et un journal des réponses.
- **Plan B** : si l'API est indisponible le jour J, utiliser les fichiers JSON déjà téléchargés et figés dans `data/raw/`.

### Source 15 : Taux de change (API)

- **Liens**
  - Dernier taux, base euro : https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/eur.json ✅
  - Taux d'une date (exemple 6 mars 2024) : https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@2024-03-06/v1/currencies/eur.json ✅
  - Adresse de secours : https://latest.currency-api.pages.dev/v1/currencies/eur.json ✅
  - Documentation : https://github.com/fawazahmed0/exchange-api ✅
- **Ce que l'API fournit** : plus de 200 devises, sans clé, sans limite annoncée ; licence CC0 (domaine public). ✅
- **Point d'attention : l'historique de 2023.** Le nouveau format avec date semble disponible depuis mars 2024 seulement ; un ancien format couvre 2020 à 2024 (modèle d'adresse : `https://cdn.jsdelivr.net/gh/fawazahmed0/currency-api@1/2023-06-15/currencies/eur.min.json`). ⚠️ à tester pour une date de 2023.
- **Plan B (très solide)** : le **franc CFA (XAF) est lié à l'euro à un taux fixe de 655,957 XAF pour 1 EUR**. Il suffit donc d'obtenir les taux EUR → USD (et éventuellement EUR → NGN) et de dériver XAF par calcul. Pour l'euro et le dollar, les taux de référence de la BCE (publiés par exemple par le service Frankfurter) conviennent ; le naira (NGN) n'y figure pas, donc on le garde comme devise optionnelle.

---

## 3. Mentions de sources à reprendre dans le dossier et le tableau de bord

| Source | Mention |
|---|---|
| FAOSTAT | « FAO. FAOSTAT, Crops and livestock products / Producer Prices. Licence : CC-BY-4.0. » (avec l'adresse de la page) |
| WAHIS | « WOAH, World Animal Health Information System (WAHIS). » |
| NDVI | « NASA (MODIS) et WFP, via HDX : NDVI at Subnational Level, Cameroun. » |
| Open-Meteo | « Données météo : Open-Meteo.com. » |
| Taux de change | « fawazahmed0/exchange-api (CC0) » et la BCE le cas échéant |

---

## 4. Test rapide de 20 minutes à faire sur ta machine

| # | Test | Résultat attendu |
|---|---|---|
| 1 | Coller l'adresse de test Open-Meteo (§ source 12) dans le navigateur | Un JSON avec températures et humidités |
| 2 | Coller l'adresse du taux de change du 6 mars 2024 (§ source 15) et chercher `xaf` dans la page | Une valeur proche de 656 si la base est l'euro |
| 3 | Tester une date de 2023 avec l'ancien format (§ source 15) | Un JSON ; sinon, on applique le plan B |
| 4 | Sur data.humdata.org, rechercher « Cameroon NDVI Subnational » | Fait : fichier `cmr-ndvi-subnat-full.csv` ; reste à noter la licence |
| 5 | Sur data.humdata.org, rechercher « Cameroon Food Prices » | Une page avec les prix producteurs ; noter la dernière année |
| 6 | Sur wahis.woah.org, filtrer le pays « Cameroon » et noter le nombre d'événements 2023-2025 | Un nombre, même faible (il décide de l'ampleur du complément synthétique) |
| 7 | Télécharger le fichier FAOSTAT QCL (§ source 1) et vérifier la présence du Cameroun | Des lignes « Cameroon » avec l'élément « Stocks » |

Note les résultats dans `docs/journal.md` : ils décident de l'ampleur de la génération synthétique.

---

## 5. Comment « figer » les sources

1. Télécharge chaque fichier dans `data/raw/` avec un nom explicite : `faostat_qcl_cameroun.csv`, `faostat_prix_cameroun.csv`, `wahis_foyers_cameroun.csv`, `ndvi_cmr_adm2.csv`, `meteo_<departement>_2023_2025.json`, `taux_change_<date>.json`.
2. Garde aussi une copie du fichier brut d'origine (le ZIP FAOSTAT complet, par exemple) dans un dossier hors dépôt.
3. Calcule une empreinte pour prouver que le fichier n'a pas changé :
   ```powershell
   Get-FileHash data\raw\* -Algorithm SHA256 | Select-Object @{n='Fichier';e={Split-Path $_.Path -Leaf}}, Hash | Export-Csv docs\sources_manifest.csv -NoTypeInformation -Encoding utf8
   ```
4. Note dans `docs/sources_manifest.csv` (ou dans le journal) la date de téléchargement et l'adresse d'origine.

Attention : ton `.gitignore` ignore le contenu de `data/`. Les fichiers figés ne seront donc **pas** envoyés sur GitHub. Sauvegarde-les sur un autre support. Seul le manifeste, placé dans `docs/`, est versionné.


---

## 6. Bilan de la vérification (06/10/2026)

Cette section remplace les hypothèses des sections précédentes lorsqu'elles diffèrent.

| N° | Source | Statut | Couverture constatée |
|---|---|---|---|
| 1 | FAOSTAT élevage | ✅ | 2015 à 2024, 4 espèces (bovins, caprins, ovins, poulets en milliers de têtes) ; pas de 2025 |
| 2 | Prix FAO producteurs | ✅ repère seulement | Indice 1991-2025 ; prix absolus en 1992-2003 (bovin, poulet, lait, œufs) et 2003 (ovin, caprin, porcin) ; aucune valeur mensuelle pour les animaux ; indice 2003 identique pour tous les produits (valeur estimée) |
| 3 | WAHIS, données quantitatives | 🔶 export final à refaire | Réel 2005-2023 par région et semestre : Adamaoua (2005-2007, 2012, 2014-2023), Ouest (2005-2023 avec trous), Extrême-Nord (2020-2023) ; rien en 2024-2025 |
| 11 | NDVI | ✅ | 2002-07-01 à 2026-09-20, 68 unités administratives, 872 décades |
| 12 | Open-Meteo | ✅ | Archive horaire testée sur Ngaoundéré |
| 15 | Taux de change | ✅ | FAO : XAF par USD, mensuel 2023-2025 (606,57 en 2023, 606,35 en 2024, 581,93 en 2025) ; API testée depuis le 06/03/2024 ; XAF/EUR fixe à 655,957 |

### Décisions
- **Foyers** : 2005-2023 réels quand ils existent, 2024-2025 simulés ; grain semestriel pour les données réelles.
- **Devises** : XAF, EUR, USD. EUR/USD déduit de 655,957 ÷ (XAF par USD).
- **Prix** : repères FAO étiquetés « estimation reconstituée » ; niveaux du marché simulé à calibrer ensuite.
- **WAHIS** : l'export final (Cameroun, 3 régions, toutes années, toutes maladies, toutes espèces) sera rangé dans `data/raw/wahis_quantitatif_complet.csv`.

### Défauts de qualité observés sur les données réelles (utiles à l'ETL)
Valeurs manquantes écrites `-` ; noms de maladies en plusieurs graphies (espaces et fautes) ; semestre en texte (« Jan-Jui 2023 ») ; codes FAO avec apostrophe ; nombre de lignes dépendant des filtres d'export.
