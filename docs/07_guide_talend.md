# Guide Talend : construire les jobs de staging

**Talend Open Studio for Data Integration 8.0.1** · projet `elevage_decisionnel` · 29 jobs de staging + 1 job maître

> Ce guide a été écrit **sans pouvoir exécuter Talend** : les noms des menus peuvent différer légèrement selon ta version. Si un écran ne ressemble pas à la description, fais une capture d'écran et envoie-la.
> Le détail de chaque job (fichier, requête, colonnes, chemins JSON et XML) se trouve dans `docs/06_fiches_jobs_staging.md`.

## 0. Principe

Le staging est un **sas brut** : on y copie les sources telles quelles, **sans corriger ni filtrer**. Toutes les colonnes sont du texte. Les défauts volontaires (dates impossibles, doublons, valeurs négatives...) y entrent donc, et c'est normal : ils sont détectés et écartés **à l'étape suivante**, en SQL, avec journalisation des rejets.

Chaque job de staging fait quatre choses :

1. **Journaliser son début** dans `audit.etl_run_log`.
2. **Vider sa table de staging** (le staging ne contient que le lot en cours).
3. **Lire la source** et écrire dans `staging.<table>` avec `batch_id` et `charge_le`.
4. **Journaliser sa fin** : réussite avec les compteurs, ou échec avec le message d'erreur.

Un **job maître** fabrique le numéro de lot (`batch_id`) et lance les 29 jobs.

---

## 1. Préparation (une seule fois, environ 45 minutes)

### 1.1 Compléter le groupe de contexte `Dev`

Dans **Contexts > Dev**, ajoute :

| Variable | Type | Valeur |
|---|---|---|
| `batch_id` | Long | `0` |
| `declencheur` | String | `MANUEL` |
| `mode_chargement` | String | `COMPLET` |

Vérifie que `path_raw` vaut `C:/projet11/data/raw` et `path_generated` vaut `C:/projet11/data/generated`, et que le raccourci `C:\projet11` existe (`Get-ChildItem C:\projet11`).

### 1.2 Créer les trois connexions dans les métadonnées

Dans **Metadata > Db Connections > clic droit > Create connection** :

| Nom | Type | Base | Réglages |
|---|---|---|---|
| `cx_dwh` | PostgreSQL | `context.pg_db_dwh` | Hôte, port, utilisateur et mot de passe : variables de contexte |
| `cx_src_cheptel` | PostgreSQL | `context.pg_db_src` | Idem |
| `cx_src_vaccinations` | MySQL | `context.mysql_db` | **Db Version : MySQL 8**, paramètre supplémentaire `serverTimezone=UTC` |

Dans les champs, utilise les variables de contexte **sans guillemets** (`context.pg_host`, `String.valueOf(context.pg_port)`, etc.) comme tu l'as fait pour `j_test_connexions`. Teste chaque connexion avec le bouton **Check**.

### 1.3 Appliquer l'ajustement du staging

```powershell
psql -U postgres -d dwh_elevage -v ON_ERROR_STOP=1 -f sql\09_ajustements_staging.sql
```

---

## 2. Le job modèle : `j_stg_abattage` (environ 90 minutes)

On commence par un petit fichier (2 809 lignes). Quand ce job fonctionne, **tous les autres CSV s'obtiennent par duplication**.

### 2.1 Créer le job et lui donner le contexte

Clic droit sur **Job Designs > Create job** : nom `j_stg_abattage`. Dans l'onglet **Contexts** du job, ajoute le groupe `Dev` (ou glisse-le depuis le référentiel).

### 2.2 Placer les composants

Dans le plan de travail, dépose et relie ainsi :

```
tPostgresqlRow_1 (début du journal)
        │ OnSubjobOk
        ▼
tPostgresqlRow_2 (vider la table)
        │ OnSubjobOk
        ▼
tFileInputDelimited_1 ──► tMap_1 ──► tPostgresqlOutput_1
        │ OnSubjobOk
        ▼
tPostgresqlRow_3 (fin : SUCCES)

tFileInputDelimited_1 ──OnComponentError──► tPostgresqlRow_4 (fin : ECHEC)
```

Les liens `OnSubjobOk` et `OnComponentError` se créent par clic droit sur le composant de départ, **Trigger**, puis un clic sur le composant d'arrivée.

### 2.3 Régler chaque composant

**`tPostgresqlRow_1` : début du journal** (connexion : `cx_dwh`, **Use an existing connection** décoché, ou l'une des métadonnées). Requête (entre guillemets Java, sur une ligne) :

```java
"INSERT INTO audit.etl_run_log (batch_id, nom_job, source, declencheur, mode_chargement, statut) VALUES (" + context.batch_id + ", 'j_stg_abattage', 'abattage', '" + context.declencheur + "', '" + context.mode_chargement + "', 'EN_COURS')"
```

**`tPostgresqlRow_2` : vider la table :**

```java
"TRUNCATE staging.stg_abattage"
```

**`tFileInputDelimited_1` :**

| Champ | Valeur |
|---|---|
| Nom de fichier | `context.path_generated + "/abattages/abattage.csv"` |
| Séparateur de ligne | `"\n"` |
| Séparateur de champ | `","` |
| Nb. lignes d'en-tête | `1` |
| Encodage | `UTF-8` |
| Délimiteur de texte (Advanced settings) | `"\""` |

Clique sur **Edit schema** et crée **toutes les colonnes de la section 9 de `06_fiches_jobs_staging.md`** pour `stg_abattage`, dans cet ordre, **toutes de type `String`**. Pour gagner du temps, tu peux d'abord créer une métadonnée **File delimited** sur le fichier (l'assistant lit l'en-tête), puis renommer les colonnes avec les noms du staging.

**`tMap_1` :** relie la sortie du fichier à une sortie `out1`. Dans `out1`, ajoute les mêmes colonnes **plus deux** :

| Colonne | Type | Expression |
|---|---|---|
| `batch_id` | Long | `context.batch_id` |
| `charge_le` | Date | `TalendDate.getCurrentDate()` |

Chaque autre colonne reçoit `row1.<même nom>`.

**`tPostgresqlOutput_1` :**

| Champ | Valeur |
|---|---|
| Table | `"stg_abattage"` |
| Schéma de la base | `"staging"` |
| Action sur les données | `Insert` |
| Action sur la table | `Default` |
| Commit every | `10000` |

**`tPostgresqlRow_3` : succès** (les compteurs viennent des composants) :

```java
"UPDATE audit.etl_run_log SET fin = now(), statut = 'SUCCES', lignes_lues = " + ((Integer)globalMap.get("tFileInputDelimited_1_NB_LINE")) + ", lignes_chargees = " + ((Integer)globalMap.get("tPostgresqlOutput_1_NB_LINE_INSERTED")) + " WHERE batch_id = " + context.batch_id + " AND nom_job = 'j_stg_abattage'"
```

**`tPostgresqlRow_4` : échec :**

```java
"UPDATE audit.etl_run_log SET fin = now(), statut = 'ECHEC', message_erreur = '" + String.valueOf(globalMap.get("tFileInputDelimited_1_ERROR_MESSAGE")).replace("'", "''") + "' WHERE batch_id = " + context.batch_id + " AND nom_job = 'j_stg_abattage'"
```

### 2.4 Premier test

1. Dans **Run**, avant de lancer, mets provisoirement `batch_id = 1` dans la valeur du contexte.
2. Lance le job. Tu dois voir `Job j_stg_abattage terminé` avec un code de sortie `0`.
3. Vérifie dans pgAdmin ou en ligne de commande :

```powershell
psql -U postgres -d dwh_elevage -c "SELECT count(*) FROM staging.stg_abattage;"
psql -U postgres -d dwh_elevage -c "SELECT nom_job, statut, lignes_lues, lignes_chargees FROM audit.etl_run_log;"
```

Résultat attendu : **2 809** lignes et une ligne de journal en `SUCCES` avec 2 809 lues et 2 809 chargées.

### 2.5 Erreurs fréquentes

| Message ou symptôme | Cause probable |
|---|---|
| `Schema ... mismatch` ou colonnes décalées | Le schéma du composant n'a pas les colonnes dans l'ordre du fichier |
| Toutes les valeurs dans la première colonne | Mauvais séparateur de champ |
| `relation "staging.stg_abattage" does not exist` | Le champ « Schéma de la base » est vide : saisis `"staging"` |
| Lignes en trop ou en moins | Nombre de lignes d'en-tête incorrect |
| `Cannot cast ... Long` | `batch_id` n'est pas défini en `Long` dans le tMap |
| Accents abîmés | Encodage du fichier différent de `UTF-8` |

---

## 3. Les 28 autres jobs

### 3.1 Les CSV (15 jobs, environ 15 minutes chacun)

Clic droit sur `j_stg_abattage` > **Duplicate**. Pour chaque copie, change **cinq choses** :

1. le **nom du job** ;
2. le **nom de fichier** du `tFileInputDelimited` ;
3. le **schéma** (colonnes de la table concernée) dans le composant d'entrée et dans le `tMap` ;
4. la **table** dans `tPostgresqlRow_2` (`TRUNCATE`) et dans `tPostgresqlOutput_1` ;
5. le **nom du job et la source** dans les trois requêtes du journal.

Fais-les dans cet ordre : les 7 référentiels (de 4 à 11 lignes, tests faciles), puis `releve_prix`, `vente`, `faostat_elevage`, `faostat_prix`, `taux_change`, `ndvi`, `alimentation`, `meteo_horaire`.

### 3.2 PostgreSQL et MySQL (6 jobs, environ 20 minutes chacun)

Même squelette, mais le composant d'entrée est `tPostgresqlInput` (connexion `cx_src_cheptel`) ou `tMysqlInput` (connexion `cx_src_vaccinations`). Copie la requête de `06_fiches_jobs_staging.md`, section 3 ou 4.

### 3.3 Excel, JSON, XML, WAHIS (7 jobs, environ 30 à 45 minutes chacun)

Suis les sections 5 à 8 de `06_fiches_jobs_staging.md`. Ce sont les plus délicats : fais-les **après** les CSV et les bases, quand tu es à l'aise avec le squelette.

---

## 4. Le job maître : `j_master_staging` (environ 45 minutes)

### 4.1 Fabriquer le numéro de lot

```
tPostgresqlInput_1 ──► tJavaRow_1
   │ OnSubjobOk
   ▼
tRunJob_1 ─► tRunJob_2 ─► ... ─► tRunJob_29     (liens OnSubjobOk)
```

- **`tPostgresqlInput_1`** (connexion `cx_dwh`) : schéma d'une colonne `batch_id` de type `Long` ; requête :

```java
"SELECT nextval('audit.seq_batch_id') AS batch_id"
```

- **`tJavaRow_1`** : relie la sortie et saisis dans le code :

```java
context.batch_id = input_row.batch_id;
```

Dans l'onglet **Contexts** du job maître, ajoute les mêmes variables que dans les jobs fils.

### 4.2 Lancer les jobs fils

Pour chaque `tRunJob`, choisis le job dans **Job**, et **coche « Transmit whole context »** : c'est ce qui fait voyager `batch_id` jusqu'aux fils. Enchaîne-les avec `OnSubjobOk`. Si un job échoue, la chaîne s'arrête : tu corriges, tu relances le job maître, qui repart sur un **nouveau** numéro de lot (le staging étant vidé à chaque job, il n'y a aucun doublon).

### 4.3 Contrôle final

```powershell
psql -U postgres -d dwh_elevage -f sql\90_controle_staging.sql
psql -U postgres -d dwh_elevage -c "SELECT nom_job, statut, lignes_lues, lignes_chargees FROM audit.etl_run_log ORDER BY run_id;"
```

La première commande doit afficher **29 lignes « OK »** (aucun « ECART »). La seconde doit montrer 29 jobs en `SUCCES`.

---

## 5. Planning conseillé (4 heures par jour)

| Jour | Contenu | Résultat attendu |
|---|---|---|
| **J1** | Préparation (§1) + job modèle `j_stg_abattage` (§2) | 1 job validé, 2 809 lignes |
| **J2** | 15 jobs CSV par duplication | Référentiels et petits CSV validés |
| **J3** | CSV volumineux (alimentation, météo, NDVI) + 6 jobs de bases | 22 jobs validés |
| **J4** | Excel, JSON, XML, WAHIS | 29 jobs validés |
| **J5** | Job maître + contrôle (`90_controle_staging.sql`) | **Chargement complet du staging** |

Puis commence la **Phase 5 : contrôle qualité et chargement des dimensions et des faits en SQL**, que je te prépare pendant que tu construis ces jobs.

## 6. Précautions

- **Ne pousse pas les contextes sur GitHub** : ils contiennent tes mots de passe. Pour sauvegarder tes jobs, utilise **File > Export items** et garde le fichier hors du dépôt (ou vide les mots de passe avant).
- **Sauvegarde après chaque job** (Ctrl+S) : Talend ne le fait pas toujours.
- Si un job de plus de 100 000 lignes semble figé, laisse-le terminer : le chargement de `meteo_horaire` ou `gps` peut prendre plusieurs minutes.
- Note dans `docs/journal.md` chaque problème rencontré et sa solution : ce sera précieux pour ton dossier.
