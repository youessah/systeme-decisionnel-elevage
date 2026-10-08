# Dossier de besoins v1 : Système décisionnel pour un réseau d'éleveurs

**Projet 11 · Élevage, santé animale et marchés** (domaine Agriculture, module BC05)
**Version** : 1.0 · **Date** : 04/10/2026 · **Auteur** : youessah
**Statut** : périmètre validé par l'enseignant

---

## 1. Contexte

L'élevage est une activité majeure du Cameroun, avec des systèmes très différents selon les régions : grand élevage bovin pastoral sur les hautes terres de l'Adamaoua, petits ruminants et transhumance dans l'Extrême-Nord sahélien, élevage périurbain et avicole à l'Ouest, proche des grands marchés de consommation.

Un réseau d'éleveurs fictif, réparti sur ces trois régions, regroupe des exploitations qui travaillent avec des vétérinaires, vendent sur des marchés à bétail et déplacent parfois leurs troupeaux selon les saisons. Les informations utiles à la gestion du réseau (cheptel, vaccinations, déplacements, ventes, alimentation, interventions vétérinaires, météo) sont produites par des outils différents, dans des formats différents, et ne sont jamais réunies.

> **Précision méthodologique** : les données propres au réseau (cheptel, vaccinations, ventes, GPS, etc.) sont **synthétiques**, inspirées du contexte camerounais. Elles ne représentent pas des statistiques réelles. Seules les sources FAOSTAT, WAHIS, NDVI, Open-Meteo et le taux de change sont des données publiques.

## 2. Problématique

> Comment centraliser, fiabiliser et analyser des données d'élevage dispersées (cheptel, santé, marchés, alimentation, environnement) afin d'aider un réseau d'éleveurs camerounais à anticiper les risques sanitaires, à mieux vendre et à maîtriser ses coûts ?

## 3. Objectifs du projet

1. **Centraliser** 15 sources hétérogènes dans un entrepôt de données dimensionnel (PostgreSQL).
2. **Fiabiliser** les données grâce à un ETL (Talend) avec contrôles qualité, rejets journalisés et reprise sur incident.
3. **Actualiser** l'entrepôt de façon incrémentale (ajouts, modifications, suppressions) et automatique (deux déclencheurs au minimum).
4. **Analyser** par 25 indicateurs répartis sur 5 pages d'un tableau de bord (Power BI).
5. **Anticiper** grâce à 3 fonctionnalités de Machine Learning et 2 de NLP, intégrées au tableau de bord.

## 4. Utilisateurs et questions décisionnelles

| Utilisateur | Questions auxquelles le système doit répondre |
|---|---|
| **Responsable du réseau** | Le cheptel progresse-t-il ? Quelle est la mortalité et où se concentre-t-elle ? Quelle est la production ? |
| **Vétérinaire coordinateur** | Quelles exploitations risquent un foyer ou une forte mortalité ? Nos délais d'intervention sont-ils tenus ? La couverture vaccinale est-elle suffisante ? Quels symptômes reviennent ? |
| **Analyste marché** | À quel prix, où et quand vendre ? Quelle marge dégage un éleveur ? Quelle part des ventes part à l'export ? |
| **Conseiller en alimentation et pâturage** | Quel est le coût d'alimentation par animal ? Quel est l'état des pâturages ? Où et combien de jours les animaux subissent-ils un stress thermique ? |

### Les trois grandes décisions éclairées

1. **Santé** : prévenir les foyers et la mortalité, et réagir plus vite.
2. **Marchés** : choisir le bon moment, le bon lieu et l'espèce à vendre, mesurer la marge.
3. **Alimentation et environnement** : adapter l'alimentation, la transhumance et la protection des animaux face à la chaleur et à l'état des pâturages.

## 5. Périmètre retenu

| Dimension | Choix |
|---|---|
| **Pays** | Cameroun |
| **Régions** | Adamaoua (chef-lieu Ngaoundéré), Extrême-Nord (Maroua), Ouest (Bafoussam) |
| **Niveau géographique** | Pays > Région > Département, avec **2 départements par région** (6 au total, voir tableau ci-dessous) |
| **Espèces** | Bovins, ovins, caprins, volailles |
| **Période simulée** | 2023 à 2025 (à ajuster si les sources publiques ne couvrent pas toute la période) |
| **Réseau simulé** | Environ 200 exploitations : ~70 Adamaoua, ~70 Extrême-Nord, ~60 Ouest (paramétrable) |
| **Devise** | Franc CFA (XAF), avec EUR et USD pour les comparaisons |
| **Langue des textes** | Français (comptes rendus vétérinaires) ; WAHIS est principalement en anglais |
| **Mode de traitement** | Lots planifiés (quotidiens), pas de temps réel |

**Départements retenus** (la zone d'étude compte 6 départements, soit 6 points de météo et 6 zones de pâturage) :

| Région | Département 1 (chef-lieu) | Département 2 (chef-lieu) |
|---|---|---|
| Adamaoua | Vina (Ngaoundéré) | Mbéré (Meiganga) |
| Extrême-Nord | Diamaré (Maroua) | Mayo-Tsanaga (Mokolo) |
| Ouest | Mifi (Bafoussam) | Menoua (Dschang) |

**Profil d'élevage simulé par région** (hypothèse de génération) :

| Région | Espèces dominantes | Particularités à reproduire dans les données |
|---|---|---|
| Adamaoua | Bovins | Grands troupeaux, production laitière, pâturages |
| Extrême-Nord | Ovins, caprins, bovins | Chaleur forte, transhumance, pression sur les pâturages |
| Ouest | Volailles, caprins, bovins | Œufs et chair, ventes vers les grands centres de consommation |

## 6. Ce que le projet ne fait pas (hors périmètre)

- Application web ou mobile, écrans de saisie, authentification.
- Temps réel.
- Logiciel de gestion d'élevage ou ERP (comptabilité, facturation, stocks).
- Diagnostic ou prescription vétérinaire : les modèles fournissent une aide à la décision.
- Étude épidémiologique officielle ou prévision nationale.
- Autres pays, autres régions, autres espèces (porcins, poissons, abeilles...).
- Cartographie avancée, calcul d'itinéraires.
- Deep learning, développement de modèle de langage.
- Déploiement cloud de production, haute disponibilité, sécurité d'entreprise avancée.

Toute idée hors de cette liste est consignée comme **perspective d'évolution** dans le dossier final.

## 7. Sources de données

| N° | Source | Format · origine | Rôle |
|---|---|---|---|
| 1 | FAOSTAT élevage | CSV · FAO (public) | Contexte et benchmark des effectifs |
| 2 | FAOSTAT prix des produits animaux | CSV · FAO (public) | Prix de référence annuels |
| 3 | WOAH WAHIS, foyers de maladies | CSV · WOAH (public) | Foyers de maladies, base du résumé NLP |
| 4 | Cheptel par exploitation | PostgreSQL · généré | Animaux, naissances, décès |
| 5 | Vaccinations | MySQL · généré | Couverture, rappels |
| 6 | Mouvements et transhumance | JSON · généré | Déplacements, distances |
| 7 | Abattages | CSV · généré | Poids, nombre d'animaux abattus |
| 8 | Production de lait et d'œufs | Excel · généré | Production journalière |
| 9 | Alimentation et fourrage | CSV · généré | Consommation, coûts |
| 10 | Prix du marché à bétail | CSV · généré | Transactions : prix, volumes, destination |
| 11 | Pâturages (NDVI) | CSV · open data | Indice de pâturage |
| 12 | Météo (Open-Meteo) | API REST JSON | Température, humidité |
| 13 | Vétérinaires et interventions | XML · généré | Interventions, délais, coûts, comptes rendus |
| 14 | Colliers GPS | JSON · généré | Positions, détection d'anomalies |
| 15 | Taux de change | API REST JSON | Conversion de devises |

**Formats couverts** : CSV, PostgreSQL, MySQL, JSON, Excel, XML, API REST (7 formats pour une exigence minimale de 4).

## 8. Exigences à satisfaire (cahier des charges)

| Exigence | Réponse du projet |
|---|---|
| 15 sources, 4 formats minimum | 15 sources, 7 formats |
| 1 million de lignes minimum | Générateurs paramétrables, volume cible > 1,5 million de lignes |
| Entrepôt avec SCD2 | `dim_exploitation` et `dim_veterinaire` en SCD2 |
| Staging, qualité, rejets, journalisation, reprise | Schémas `staging` et `audit`, tables `etl_run_log`, `etl_reject`, `etl_watermark` |
| Chargement complet puis incrémental | Scénario de démonstration J0 à J3 + panne |
| 2 déclencheurs automatiques minimum | Planificateur de tâches Windows + dépôt de fichier (+ trigger PostgreSQL optionnel) |
| 25 indicateurs sur 5 pages | Voir `02_indicateurs_tracabilite.md` |
| 3 ML + 2 NLP écrits dans l'entrepôt | Calcul par lot, résultats dans le schéma `ml`, métriques affichées |
| Indicateur d'actualité des données | « Dernier chargement » sur chaque page |
| Dossier de conception | Ce dossier et les suivants, dans `docs/` |

### Fonctionnalités ML et NLP

| Type | Fonctionnalité | Page |
|---|---|---|
| ML 1 | Prédiction du risque sanitaire et de mortalité par exploitation | Santé animale |
| ML 2 | Prévision des prix par espèce et des volumes vendus | Marchés |
| ML 3 | Détection d'anomalies de comportement via les colliers GPS | Alimentation et environnement |
| NLP 1 | Extraction des symptômes et maladies dans les comptes rendus vétérinaires | Santé animale |
| NLP 2 | Résumé automatique des foyers de maladies (WAHIS) par région | Santé animale |

## 9. Outils et environnement

PostgreSQL 18 (entrepôt et source cheptel), MySQL 9.1 via WAMP (source vaccinations), Talend Open Studio 8.0.1 (ETL), Python 3.13 (génération des données, ML, NLP), Power BI Desktop (tableau de bord), GitHub (versionnement), Planificateur de tâches Windows (déclenchement planifié).

## 10. Hypothèses et contraintes

- Les données synthétiques sont construites avec un signal réaliste (mortalité liée à la chaleur, aux retards de vaccination et aux délais d'intervention ; anomalies GPS étiquetées), faute de quoi les modèles seraient sans intérêt.
- Les sources publiques ont été vérifiées le 06/10/2026 (voir `03_sources_publiques.md`). WAHIS fournit des données réelles par région et par semestre jusqu'en 2023, mais rien pour 2024-2025 : ces années sont simulées, calibrées sur l'historique réel, et signalées par une colonne `origine` (`WAHIS` ou `SIMULE`). Les données FAO de prix ne donnent des prix absolus qu'en 2003 : elles servent de repère et non de référence de niveau.
- Talend Open Studio ne fournit ni intégration Git ni planificateur : les jobs seront exportés manuellement et planifiés avec le Planificateur de tâches Windows.
- Projet individuel : le périmètre est volontairement borné (3 régions, 4 espèces, 25 indicateurs, 5 modèles, 5 pages).

## 11. Risques

| Risque | Parade |
|---|---|
| Source publique ou API indisponible | Copie locale figée, plan B décidé dès la phase 2 |
| Données générées sans signal, ML inexploitable | Corrélations et anomalies injectées et étiquetées |
| Indicateur incalculable faute de champ | Matrice de traçabilité avant la génération |
| Volumétrie insuffisante ou machine lente | Paramètres de configuration, chargements par lots |
| Démonstration incrémentale qui échoue | Scénario scripté, vidéo de secours |
| Retard cumulé | Jalons par phase, MVP d'abord |

## 12. Livrables

Dossier de conception (besoins, matrice des processus, modèle de l'entrepôt, plan des flux ETL), scripts de génération, scripts SQL, jobs Talend, scripts ML/NLP, entrepôt chargé, rapport Power BI, démonstration incrémentale et soutenance.
