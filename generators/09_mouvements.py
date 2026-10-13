"""Génère la source 6 : mouvements du bétail et transhumance (fichiers JSON, un par année).

Trois types de mouvements :
  - transhumance_aller / transhumance_retour : seules les exploitations « Transhumant » partent en saison
    sèche vers un site de pâturage fixe (distance selon la région) et reviennent avec les pluies ;
  - vente  : un mouvement par transaction du marché (exploitation -> marché, ville ou pays d'export) ;
  - achat  : un mouvement par animal acheté (marché -> exploitation).
Les distances sont calculées à partir des coordonnées (formule de haversine).

Sorties  data/generated/mouvements/mouvements_<année>.json  (avec défauts volontaires)
         data/generated/pilotes/mouvements_propre.csv, defauts_mouvements.csv

Lancer depuis la racine du dépôt :  python generators/09_mouvements.py
"""
import json

import numpy as np
import pandas as pd

from common import (ESP, RACINE, charger_cfg, dossier_ref, dossier_verite, jour, jours, dates)


def haversine(lat1, lon1, lat2, lon2):
    """Distance en kilomètres entre deux points (latitude, longitude en degrés)."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def deplacer(lat, lon, km, cap):
    """Point atteint en partant de (lat, lon), à `km` kilomètres, selon le cap (radians)."""
    dlat = km * np.cos(cap) / 111.0
    dlon = km * np.sin(cap) / (111.0 * np.cos(np.radians(lat)))
    return lat + dlat, lon + dlon


def main():
    cfg = charger_cfg()
    mv = cfg["mouvements"]
    th = mv["transhumance"]
    rng = np.random.default_rng(cfg["projet"]["graine"] + 8)
    ref, verite = dossier_ref(cfg), dossier_verite(cfg)
    expl = pd.read_csv(ref / "ref_exploitations.csv")
    marches = pd.read_csv(ref / "ref_marches.csv").set_index("id_marche")
    marche_dep = pd.read_csv(ref / "ref_marches.csv").set_index("pcode_departement")
    ani = pd.read_csv(verite / "animal_propre.csv", parse_dates=["date_entree", "date_sortie"])
    ventes = pd.read_csv(verite / "vente_propre.csv", parse_dates=["date_transaction"])
    annees = sorted({d.year for d in pd.date_range(cfg["projet"]["periode"]["debut"], cfg["projet"]["periode"]["fin"])})
    D0, D1 = jour(cfg["projet"]["periode"]["debut"]), jour(cfg["projet"]["periode"]["fin"])
    fx = expl.set_index("id_exploitation")
    lignes = []

    # ------------------------------------------------------------------ transhumance
    entree, sortie = jours(ani["date_entree"]), np.where(ani["date_sortie"].notna(), jours(ani["date_sortie"]), 10 ** 7)
    for _, e in expl[expl["systeme_elevage"] == "Transhumant"].iterrows():
        region = e["region"]
        if region not in th["distance_mediane_km"]:
            continue
        dist = float(np.clip(rng.lognormal(np.log(th["distance_mediane_km"][region]), 0.4), *th["distance_min_max_km"]))
        cap = rng.uniform(0, 2 * np.pi)
        lat_d, lon_d = deplacer(e["latitude"], e["longitude"], dist, cap)  # site de pâturage de la saison sèche
        mask_f = (ani["id_exploitation"] == e["id_exploitation"]).to_numpy()
        for an in annees:
            for sens, (a, b) in (("transhumance_aller", th["fenetre_aller"]), ("transhumance_retour", th["fenetre_retour"])):
                if rng.random() > th["part_exploitations_qui_partent"]:
                    continue
                d1, d2 = jour(f"{an}-{a}"), jour(f"{an}-{b}")
                depart = int(rng.integers(d1, d2 + 1))
                if depart < D0 or depart > D1:
                    continue
                arrivee = depart + max(1, int(round(dist / th["vitesse_km_jour"])))
                for esp in ESP:
                    if rng.random() > th["especes"][region].get(esp, 0):
                        continue
                    n = int((mask_f & (ani["espece"] == esp).to_numpy() & (entree <= depart) & (sortie > depart)).sum())
                    if n < 2:
                        continue
                    nb = max(1, int(round(n * rng.uniform(*th["part_troupeau"]))))
                    o, d = ((e["latitude"], e["longitude"]), (lat_d, lon_d)) if sens.endswith("aller") else ((lat_d, lon_d), (e["latitude"], e["longitude"]))
                    lignes.append(dict(id_exploitation=e["id_exploitation"], espece=esp, nb_tetes=nb, type_mouvement=sens,
                                       date_depart=depart, date_arrivee=arrivee, lieu_o=("Exploitation " + e["id_exploitation"]) if sens.endswith("aller") else "Pâturage de saison sèche",
                                       lat_o=o[0], lon_o=o[1], lieu_d="Pâturage de saison sèche" if sens.endswith("aller") else ("Exploitation " + e["id_exploitation"]),
                                       lat_d=d[0], lon_d=d[1], id_transaction=None))

    # ------------------------------------------------------------------ ventes (un mouvement par transaction)
    villes = {k: tuple(v) for k, v in mv["villes"].items()}
    for r in ventes.itertuples():
        f = fx.loc[r.id_exploitation]
        if r.destination_categorie == "local":
            lat_d, lon_d, lieu = marches.loc[r.id_marche, "latitude"], marches.loc[r.id_marche, "longitude"], marches.loc[r.id_marche, "nom_marche"]
        else:
            (lat_d, lon_d), lieu = villes[r.destination], r.destination
        km = float(haversine(f["latitude"], f["longitude"], lat_d, lon_d))
        arrivee = jour(r.date_transaction)
        lignes.append(dict(id_exploitation=r.id_exploitation, espece=r.espece, nb_tetes=int(r.nb_tetes), type_mouvement="vente",
                           date_depart=max(arrivee - int(km // 250), D0), date_arrivee=arrivee, lieu_o="Exploitation " + r.id_exploitation,
                           lat_o=f["latitude"], lon_o=f["longitude"], lieu_d=lieu, lat_d=lat_d, lon_d=lon_d, id_transaction=r.id_transaction))

    # ------------------------------------------------------------------ achats (un mouvement par animal acheté)
    ach = ani[(ani["type_entree"] == "achat") & (ani["date_entree"] >= pd.Timestamp(cfg["projet"]["periode"]["debut"]))]
    for r in ach.itertuples():
        f = fx.loc[r.id_exploitation]
        m = marche_dep.loc[f["pcode_departement"]]
        arrivee = jour(r.date_entree)
        lignes.append(dict(id_exploitation=r.id_exploitation, espece=r.espece, nb_tetes=1, type_mouvement="achat",
                           date_depart=arrivee, date_arrivee=arrivee, lieu_o=m["nom_marche"], lat_o=m["latitude"], lon_o=m["longitude"],
                           lieu_d="Exploitation " + r.id_exploitation, lat_d=f["latitude"], lon_d=f["longitude"], id_transaction=None))

    df = pd.DataFrame(lignes).sort_values(["date_depart", "id_exploitation"]).reset_index(drop=True)
    df["distance_km"] = haversine(df["lat_o"], df["lon_o"], df["lat_d"], df["lon_d"]).round(1)
    for c in ("lat_o", "lon_o", "lat_d", "lon_d"):
        df[c] = df[c].astype(float).round(5)
    df.insert(0, "id_mouvement", [f"MVT-{i:06d}" for i in range(1, len(df) + 1)])
    df["date_depart"], df["date_arrivee"] = dates(df["date_depart"]), dates(df["date_arrivee"])
    propre = df.copy()

    # ------------------------------------------------------------------ défauts volontaires
    obs, etiq = propre.copy(), []
    n = len(obs)
    k = max(3, int(n * mv["defauts"]["taux"] / 4))
    i = rng.choice(n, k, replace=False)
    obs.loc[i, ["lat_o", "lon_o"]] = obs.loc[i, ["lon_o", "lat_o"]].to_numpy()
    etiq += [("mouvement", x, "coordonnees_inversees") for x in obs.loc[i, "id_mouvement"]]
    i = rng.choice(n, k, replace=False)
    obs.loc[i, "date_arrivee"] = obs.loc[i, "date_depart"] - pd.Timedelta(days=3)
    etiq += [("mouvement", x, "arrivee_avant_depart") for x in obs.loc[i, "id_mouvement"]]
    i = rng.choice(n, k, replace=False)
    obs.loc[i, "distance_km"] = -obs.loc[i, "distance_km"]
    etiq += [("mouvement", x, "distance_negative") for x in obs.loc[i, "id_mouvement"]]
    i = rng.choice(n, k, replace=False)
    dup = obs.loc[i].copy()
    dup["id_mouvement"] = [f"MVT-{n + j + 1:06d}" for j in range(k)]
    etiq += [("mouvement", x, "doublon") for x in dup["id_mouvement"]]
    obs = pd.concat([obs, dup], ignore_index=True)

    # ------------------------------------------------------------------ écriture (JSON imbriqué, un fichier par année)
    sortie_d = RACINE / mv["sortie"]
    sortie_d.mkdir(parents=True, exist_ok=True)
    for an in sorted(obs["date_depart"].dt.year.unique()):
        enreg = []
        for r in obs[obs["date_depart"].dt.year == an].itertuples():
            enreg.append({
                "id_mouvement": r.id_mouvement, "id_exploitation": r.id_exploitation, "espece": r.espece, "nb_tetes": int(r.nb_tetes),
                "type_mouvement": r.type_mouvement, "date_depart": r.date_depart.strftime("%Y-%m-%d"),
                "date_arrivee": r.date_arrivee.strftime("%Y-%m-%d"),
                "origine": {"lieu": r.lieu_o, "latitude": r.lat_o, "longitude": r.lon_o},
                "destination": {"lieu": r.lieu_d, "latitude": r.lat_d, "longitude": r.lon_d},
                "distance_km": r.distance_km, "id_transaction": r.id_transaction})
        (sortie_d / f"mouvements_{an}.json").write_text(json.dumps(enreg, ensure_ascii=False), encoding="utf-8")
    propre.to_csv(verite / "mouvements_propre.csv", index=False, encoding="utf-8")
    pd.DataFrame(etiq, columns=["table", "identifiant", "type_defaut"]).to_csv(verite / "defauts_mouvements.csv", index=False)

    # ------------------------------------------------------------------ contrôles
    print(f"=== {len(obs)} mouvements (dont {len(etiq)} défauts volontaires) ===")
    print(pd.crosstab(propre["type_mouvement"], propre["date_depart"].dt.year).to_string())
    t = propre[propre["type_mouvement"] == "transhumance_aller"].merge(expl[["id_exploitation", "region"]], on="id_exploitation")
    print("\nDistances de transhumance (km) par région :")
    print(t.groupby("region")["distance_km"].describe()[["count", "mean", "min", "max"]].round(1).to_string())
    print(f"\nExploitations qui transhument : {t['id_exploitation'].nunique()} sur {(expl['systeme_elevage'] == 'Transhumant').sum()} déclarées « Transhumant »")
    print(f"Cohérence avec le marché : {(propre['type_mouvement'] == 'vente').sum()} mouvements de vente, {len(ventes)} transactions (doit être égal)")
    print("Écrit dans", sortie_d.relative_to(RACINE))


if __name__ == "__main__":
    main()
