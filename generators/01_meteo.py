"""Télécharge et fige la météo horaire Open-Meteo des 6 départements, puis fait un diagnostic.

Entrées : data/generated/referentiel/ref_lieux.csv (produit par 00_referentiel.py), config/params.yaml
Sorties : data/raw/meteo/<pcode>_<année>.json  (réponses brutes de l'API, conservées telles quelles)
          data/generated/meteo_horaire_reference.csv (tableau horaire, pour caler la simulation)

Le script est rejouable : un fichier déjà téléchargé n'est pas redemandé.
Lancer depuis la racine du dépôt :  python generators/01_meteo.py
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yaml

RACINE = Path(__file__).resolve().parents[1]
URL = "https://archive-api.open-meteo.com/v1/archive"
DOSSIER_BRUT = RACINE / "data" / "raw" / "meteo"
SEUILS_THI = [72, 78, 82]  # seuils testés pour l'indicateur « jours de stress thermique »


def telecharger(lat, lon, annee, chemin):
    """Télécharge une année de données horaires ; ne refait pas un fichier existant."""
    if chemin.exists():
        return "déjà présent"
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": f"{annee}-01-01", "end_date": f"{annee}-12-31",
        "hourly": "temperature_2m,relative_humidity_2m",
        "timezone": "Africa/Douala",
    }
    for essai in range(1, 6):
        r = requests.get(URL, params=params, timeout=90)
        if r.status_code == 200:
            chemin.write_text(r.text, encoding="utf-8")
            return "téléchargé"
        if r.status_code == 429:  # trop de requêtes : on patiente
            time.sleep(20 * essai)
            continue
        raise SystemExit(f"Erreur HTTP {r.status_code} pour {chemin.name} : {r.text[:200]}")
    raise SystemExit(f"Trop de tentatives pour {chemin.name}")


def thi(temp_c, hr):
    """Indice température-humidité : (1,8 T + 32) - (0,55 - 0,0055 HR) x (1,8 T - 26)."""
    return (1.8 * temp_c + 32) - (0.55 - 0.0055 * hr) * (1.8 * temp_c - 26)


def main():
    cfg = yaml.safe_load(open(RACINE / "config" / "params.yaml", encoding="utf-8"))
    debut = int(cfg["projet"]["periode"]["debut"][:4])
    fin = int(cfg["projet"]["periode"]["fin"][:4])
    lieux = pd.read_csv(RACINE / cfg["chemins"]["sortie_referentiel"] / "ref_lieux.csv")
    DOSSIER_BRUT.mkdir(parents=True, exist_ok=True)

    morceaux = []
    for _, d in lieux.iterrows():
        for annee in range(debut, fin + 1):
            f = DOSSIER_BRUT / f"{d['pcode_departement']}_{annee}.json"
            etat = telecharger(d["latitude"], d["longitude"], annee, f)
            print(f"{d['departement']:13s} {annee}  {etat}")
            if etat == "téléchargé":
                time.sleep(1.5)  # courtoisie envers l'API gratuite
            h = json.loads(f.read_text(encoding="utf-8"))["hourly"]
            morceaux.append(pd.DataFrame({
                "pcode_departement": d["pcode_departement"],
                "departement": d["departement"],
                "horodatage": pd.to_datetime(h["time"]),
                "temperature_c": h["temperature_2m"],
                "humidite_pct": h["relative_humidity_2m"],
            }))

    meteo = pd.concat(morceaux, ignore_index=True)
    sortie = RACINE / "data" / "generated" / "meteo_horaire_reference.csv"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    meteo.to_csv(sortie, index=False, encoding="utf-8")

    n_attendu = sum(len(pd.date_range(f"{a}-01-01", f"{a}-12-31 23:00", freq="h")) for a in range(debut, fin + 1))
    print(f"\n=== CONTRÔLES ({len(meteo)} lignes ; {n_attendu} attendues par département) ===")
    ctrl = meteo.groupby("departement").agg(
        lignes=("horodatage", "size"),
        manquants=("temperature_c", lambda s: int(s.isna().sum())),
    )
    print(ctrl.to_string())

    meteo["jour"] = meteo["horodatage"].dt.date
    meteo["thi"] = thi(meteo["temperature_c"], meteo["humidite_pct"])
    jour = meteo.groupby(["departement", "jour"]).agg(
        t_max=("temperature_c", "max"), hr_moy=("humidite_pct", "mean"), thi_max=("thi", "max")).reset_index()

    print("\n=== PROFIL CLIMATIQUE ET STRESS THERMIQUE (part des jours dont le THI maximal dépasse le seuil) ===")
    res = jour.groupby("departement").agg(
        t_max_moy=("t_max", "mean"), hr_moy=("hr_moy", "mean"), thi_max_moy=("thi_max", "mean")).round(1)
    for s in SEUILS_THI:
        res[f"jours>{s} (%)"] = jour.groupby("departement")["thi_max"].apply(lambda x, s=s: round(100 * (x > s).mean(), 1))
    print(res.to_string())
    print("\nSi presque tous les jours dépassent 72, ce seuil ne discrimine pas : choisir un seuil plus élevé.")
    print("Écrit :", sortie.relative_to(RACINE))


if __name__ == "__main__":
    main()
