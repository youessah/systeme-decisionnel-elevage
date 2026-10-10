"""Crée les tables et charge les sources 4 et 5 dans leurs bases d'origine.

  Source 4  cheptel        -> PostgreSQL, base src_cheptel        (tables exploitation, animal, lot_volaille, suivi_lot_semaine)
  Source 5  vaccinations   -> MySQL,      base src_vaccinations   (tables vaccin, vaccination)

Les connexions sont lues dans config/.env (PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, MYSQL_HOST, MYSQL_PORT,
MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB). Les bases doivent déjà exister (voir sql/00_ et sql/02_).

Lancer depuis la racine du dépôt :
    python generators/05_charger_sources.py            (premier chargement ; refuse d'écraser des tables non vides)
    python generators/05_charger_sources.py --reset    (supprime les tables et recharge tout)
"""
import argparse
import os
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv
from sqlalchemy import (Column, Date, DateTime, Float, ForeignKey, Index, Integer, MetaData, String, Table,
                        create_engine, text)
from sqlalchemy.engine import URL

RACINE = Path(__file__).resolve().parents[1]


# ----------------------------------------------------------------------------
# Définition des tables
# ----------------------------------------------------------------------------
def tables_cheptel():
    m = MetaData()
    exploitation = Table(
        "exploitation", m,
        Column("id_exploitation", String(12), primary_key=True),
        Column("nom_exploitation", String(120)), Column("proprietaire", String(100)),
        Column("pcode_departement", String(10)), Column("departement", String(50)), Column("region", String(30)),
        Column("espece_principale", String(20)), Column("systeme_elevage", String(20)), Column("taille", String(10)),
        Column("date_creation", Date), Column("latitude", Float), Column("longitude", Float),
        Column("statut", String(15)), Column("updated_at", DateTime))
    animal = Table(
        "animal", m,
        Column("id_animal", String(12), primary_key=True),
        Column("id_exploitation", String(12), ForeignKey("exploitation.id_exploitation"), nullable=False),
        Column("espece", String(20)), Column("race", String(40)), Column("sexe", String(1)),
        Column("date_naissance", Date), Column("type_entree", String(12)), Column("date_entree", Date),
        Column("date_sortie", Date), Column("motif_sortie", String(12)), Column("cause_deces", String(30)),
        Column("statut_reproducteur", String(3)), Column("updated_at", DateTime),
        Index("ix_animal_exploitation", "id_exploitation"), Index("ix_animal_updated", "updated_at"))
    lot = Table(
        "lot_volaille", m,
        Column("id_lot", String(12), primary_key=True),
        Column("id_exploitation", String(12), ForeignKey("exploitation.id_exploitation"), nullable=False),
        Column("espece", String(20)), Column("type_production", String(10)), Column("race", String(40)),
        Column("date_mise_en_place", Date), Column("effectif_initial", Integer), Column("date_sortie", Date),
        Column("nb_morts_total", Integer), Column("motif_sortie", String(12)), Column("updated_at", DateTime),
        Index("ix_lot_updated", "updated_at"))
    suivi = Table(
        "suivi_lot_semaine", m,
        Column("id_suivi", Integer, primary_key=True, autoincrement=False),
        Column("id_lot", String(12), ForeignKey("lot_volaille.id_lot"), nullable=False),
        Column("date_semaine", Date), Column("nb_morts", Integer), Column("effectif_fin_semaine", Integer),
        Index("ix_suivi_lot", "id_lot"))
    return m, [("exploitation", exploitation), ("animal", animal), ("lot_volaille", lot), ("suivi_lot_semaine", suivi)]


def tables_vaccinations():
    m = MetaData()
    vaccin = Table(
        "vaccin", m,
        Column("code_vaccin", String(10), primary_key=True),
        Column("vaccin", String(80)), Column("code_maladie", String(10)), Column("especes_cibles", String(60)),
        Column("rappel_jours", Integer), Column("maladie", String(80)))
    vaccination = Table(
        "vaccination", m,
        Column("id_vaccination", String(14), primary_key=True),
        Column("id_exploitation", String(12), nullable=False), Column("id_animal", String(12)), Column("id_lot", String(12)),
        Column("espece", String(20)),
        Column("code_vaccin", String(10), ForeignKey("vaccin.code_vaccin"), nullable=False),
        Column("vaccin", String(80)), Column("maladie_ciblee", String(80)), Column("numero_dose", Integer),
        Column("date_vaccination", Date), Column("date_rappel_prevue", Date), Column("date_rappel_realisee", Date),
        Column("id_veterinaire", String(10)), Column("nb_animaux_vaccines", Integer), Column("updated_at", DateTime),
        Index("ix_vacc_exploitation", "id_exploitation"), Index("ix_vacc_updated", "updated_at"))
    return m, [("vaccin", vaccin), ("vaccination", vaccination)]


# ----------------------------------------------------------------------------
def lire(csv, table):
    """Lit un CSV et le met au format attendu par la table (dates, entiers, valeurs manquantes -> NULL)."""
    df = pd.read_csv(csv, encoding="utf-8")
    for col in table.columns:
        if col.name not in df.columns:
            continue
        if isinstance(col.type, Date):
            df[col.name] = pd.to_datetime(df[col.name], errors="coerce").dt.date
        elif isinstance(col.type, DateTime):
            df[col.name] = pd.to_datetime(df[col.name], errors="coerce")
        elif isinstance(col.type, Integer):
            df[col.name] = pd.to_numeric(df[col.name], errors="coerce").astype("Int64")
    df = df[[c.name for c in table.columns]].astype(object)
    return df.where(pd.notna(df), None)


def charger(engine, meta, tables, dossier, reset, chunk):
    if reset:
        meta.drop_all(engine)
    meta.create_all(engine)
    with engine.connect() as cx:
        non_vides = [n for n, t in tables if cx.execute(text(f"SELECT COUNT(*) FROM {n}")).scalar() > 0]
    if non_vides:
        print(f"  Tables déjà remplies ({', '.join(non_vides)}) : rien n'est chargé. Utiliser --reset pour recharger.")
        return
    for nom, table in tables:
        df = lire(dossier / f"{nom}.csv", table)
        df.to_sql(nom, engine, if_exists="append", index=False, chunksize=chunk, method="multi")
        print(f"  {nom:20s}{len(df):9d} lignes chargées")


def controles(engine, tables):
    with engine.connect() as cx:
        for nom, table in tables:
            n = cx.execute(text(f"SELECT COUNT(*) FROM {nom}")).scalar()
            print(f"  {nom:20s}{n:9d} lignes en base")


def moteur_pg():
    return create_engine(URL.create(
        "postgresql+psycopg2", username=os.getenv("PG_USER"), password=os.getenv("PG_PASSWORD"),
        host=os.getenv("PG_HOST", "localhost"), port=int(os.getenv("PG_PORT", "5432")),
        database=os.getenv("PG_SRC_DB", "src_cheptel")))


def moteur_mysql():
    return create_engine(URL.create(
        "mysql+pymysql", username=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD") or None,
        host=os.getenv("MYSQL_HOST", "localhost"), port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DB", "src_vaccinations"), query={"charset": "utf8mb4"}))


def main(moteurs=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="supprime les tables avant de recharger")
    args = parser.parse_args()
    load_dotenv(RACINE / "config" / ".env")
    cfg = yaml.safe_load(open(RACINE / "config" / "params.yaml", encoding="utf-8"))
    chunk = int(os.getenv("CHARGEMENT_CHUNK", "2000"))
    pg, my = moteurs or (moteur_pg(), moteur_mysql())

    print("Source 4 : cheptel (PostgreSQL)")
    meta, tables = tables_cheptel()
    charger(pg, meta, tables, RACINE / cfg["cheptel"]["sortie"], args.reset, chunk)
    controles(pg, tables)

    print("\nSource 5 : vaccinations (MySQL)")
    meta, tables = tables_vaccinations()
    charger(my, meta, tables, RACINE / cfg["vaccinations"]["sortie"], args.reset, chunk)
    controles(my, tables)

    print("\nContrôle de cohérence entre les deux bases :")
    with pg.connect() as c1, my.connect() as c2:
        ids_pg = {r[0] for r in c1.execute(text("SELECT id_animal FROM animal"))}
        ids_my = {r[0] for r in c2.execute(text("SELECT DISTINCT id_animal FROM vaccination WHERE id_animal IS NOT NULL"))}
    print(f"  animaux vaccinés : {len(ids_my)} ; absents du cheptel : {len(ids_my - ids_pg)} (doit valoir 0)")


if __name__ == "__main__":
    main()
