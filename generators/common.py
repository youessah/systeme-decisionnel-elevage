"""Fonctions communes aux générateurs 06 et suivants.

Les dates sont manipulées sous forme de « numéro de jour » entier (jours écoulés depuis 1970) :
c'est plus rapide et évite les confusions de formats. Les paramètres sont lus dans config/params.yaml
et, s'il existe, config/params_sources.yaml (les sections de celui-ci s'ajoutent à celles du premier).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RACINE = Path(__file__).resolve().parents[1]
EPOQUE = pd.Timestamp("1970-01-01")
JOURS = 30.44
ESP = ["Bovins", "Ovins", "Caprins"]
MOIS_EN = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6, "July": 7,
           "August": 8, "September": 9, "October": 10, "November": 11, "December": 12}


def jour(ts):
    return int((pd.Timestamp(ts) - EPOQUE).days)


def jours(s, defaut=0):
    """Série de dates -> numéros de jour ; valeur manquante -> défaut."""
    return ((pd.to_datetime(s) - EPOQUE).dt.days.fillna(defaut)).astype(int).to_numpy()


def dates(j):
    return pd.to_datetime(np.asarray(j), unit="D")


def charger_cfg():
    cfg = yaml.safe_load(open(RACINE / "config" / "params.yaml", encoding="utf-8"))
    extra = RACINE / "config" / "params_sources.yaml"
    if extra.exists():
        cfg.update(yaml.safe_load(open(extra, encoding="utf-8")))
    return cfg


def dossier_ref(cfg):
    return RACINE / cfg["chemins"]["sortie_referentiel"]


def dossier_verite(cfg):
    return RACINE / cfg["signal"]["sortie_pilotes"]


def mois_periode(cfg):
    p = cfg["projet"]["periode"]
    return pd.date_range(p["debut"], p["fin"], freq="MS")


def taux_usd(cfg):
    """Retourne une fonction (année, mois) -> francs CFA pour 1 dollar, d'après le fichier FAO (mensuel)."""
    df = pd.read_csv(RACINE / "data" / "raw" / "faostat_change_cameroun.csv")
    df = df[df["Element"] == "Local currency units per USD"]
    m = df[df["Months"].isin(MOIS_EN)]
    t = {(int(r.Year), MOIS_EN[r.Months]): float(r.Value) for r in m.itertuples()}
    annuel = df[df["Months"] == "Annual value"].set_index("Year")["Value"].astype(float).to_dict()
    return lambda y, mo: t.get((int(y), int(mo)), annuel.get(int(y), 600.0))


def table_mois(pil, colonne, ids):
    """Pivot (exploitation x mois) d'une colonne des facteurs cachés, dans l'ordre des exploitations."""
    return pil.pivot(index="id_exploitation", columns="mois", values=colonne).reindex(ids)


def valeur_mois(serie_pilotes, ids_exploitation, dates_):
    """Valeur d'une colonne des facteurs cachés pour chaque (exploitation, date)."""
    mois = pd.DatetimeIndex(pd.to_datetime(dates_)).to_period("M").to_timestamp()
    idx = pd.MultiIndex.from_arrays([np.asarray(ids_exploitation), mois])
    return serie_pilotes.reindex(idx).to_numpy()
