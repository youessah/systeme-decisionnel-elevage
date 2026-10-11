"""Génère la source 8 : production de lait et d'œufs (classeur Excel).

Une ligne par exploitation et par jour de production, une feuille par année.
Lait : vaches en lactation (part des femelles bovines reproductrices) x rendement de la région,
       modulé par l'état des pâturages (NDVI) et le stress thermique du mois.
Œufs : pondeuses des lots de ponte (taux de ponte selon l'âge du lot), poules locales moins productives.

Le classeur contient volontairement des défauts typiques d'Excel (dates saisies en texte, virgule décimale,
valeurs aberrantes, litres négatifs), listés dans data/generated/pilotes/defauts_production.csv.

Sorties  data/generated/production/production_lait_oeufs.xlsx
         data/generated/pilotes/production_propre.csv, defauts_production.csv

Lancer depuis la racine du dépôt :  python generators/08_production.py
"""
import numpy as np
import pandas as pd
from openpyxl import Workbook

from common import (JOURS, RACINE, charger_cfg, dossier_ref, dossier_verite, jour, jours, mois_periode, table_mois)


def main():
    cfg = charger_cfg()
    p = cfg["production"]
    rng = np.random.default_rng(cfg["projet"]["graine"] + 7)
    ref, verite = dossier_ref(cfg), dossier_verite(cfg)
    expl = pd.read_csv(ref / "ref_exploitations.csv")
    ids = expl["id_exploitation"].tolist()
    nf, fid = len(ids), {x: i for i, x in enumerate(ids)}
    ani = pd.read_csv(verite / "animal_propre.csv", parse_dates=["date_naissance", "date_entree", "date_sortie"])
    lots = pd.read_csv(verite / "lot_propre.csv", parse_dates=["date_mise_en_place"])
    hebdo = pd.read_csv(RACINE / cfg["cheptel"]["sortie"] / "suivi_lot_semaine.csv", parse_dates=["date_semaine"])
    pil = pd.read_csv(verite / "pilotes_exploitation_mois.csv", parse_dates=["mois"])
    mois = mois_periode(cfg)
    Z = table_mois(pil, "ndvi_z", ids).to_numpy()
    S = table_mois(pil, "jours_stress", ids).to_numpy()
    rend_region = expl["region"].map(p["rendement_litres"]).to_numpy(float)
    effet_ferme = rng.lognormal(0, 0.25, nf)
    D0, D1 = jour(mois[0]), jour(cfg["projet"]["periode"]["fin"])

    # ------------------------------------------------------------------ lait
    b = ani[ani["espece"] == "Bovins"]
    farm = b["id_exploitation"].map(fid).to_numpy()
    entree = jours(b["date_entree"])
    sortie = np.where(b["date_sortie"].notna(), jours(b["date_sortie"]), 10 ** 7)
    naiss = jours(b["date_naissance"])
    femelle = (b["sexe"] == "F").to_numpy()
    age_rep = cfg["cheptel"]["age_reproduction_mois"]["Bovins"]
    lait = []
    for k, ms in enumerate(mois):
        jm = ms.days_in_month
        ms_d = jour(ms)
        rep = femelle & (entree <= ms_d) & (sortie > ms_d) & ((ms_d - naiss) / JOURS >= age_rep)
        n_lact = np.bincount(farm[rep], minlength=nf) * p["part_vaches_laitieres"]
        fi = np.flatnonzero(n_lact >= 1)
        facteur = np.clip(1 + p["sensibilite_ndvi"] * Z[fi, k] - p["sensibilite_chaleur"] * S[fi, k] / jm, 0.3, 1.8)
        base = (n_lact[fi] * rend_region[fi] * effet_ferme[fi] * facteur)[:, None]
        litres = base * rng.lognormal(0, 0.12, (len(fi), jm))
        jours_m = pd.date_range(ms, periods=jm, freq="D")
        lait.append(pd.DataFrame({
            "date": np.tile(jours_m, len(fi)), "id_exploitation": np.repeat(np.array(ids)[fi], jm),
            "litres_lait": litres.ravel().round(1), "nb_vaches_lactation": np.repeat(np.round(n_lact[fi]).astype(int), jm)}))
    lait = pd.concat(lait, ignore_index=True)

    # ------------------------------------------------------------------ œufs
    h = hebdo.merge(lots[lots["type_production"] == "ponte"][["id_lot", "id_exploitation", "race", "date_mise_en_place"]], on="id_lot")
    h = h.loc[h.index.repeat(7)].reset_index(drop=True)
    h["date"] = h["date_semaine"] + pd.to_timedelta(np.tile(np.arange(7), len(h) // 7), unit="D")
    h = h[h["date"] <= pd.Timestamp(cfg["projet"]["periode"]["fin"])]
    age = ((h["date"] - h["date_mise_en_place"]).dt.days / 7).to_numpy()
    po = p["ponte"]
    taux = np.where(age < po["debut_semaine"], 0.0,
                    po["taux_max"] - (po["taux_max"] - po["taux_fin"]) * np.clip((age - po["debut_semaine"]) / (po["fin_semaine"] - po["debut_semaine"]), 0, 1))
    taux = taux * np.where(h["race"] == "Poule locale", po["facteur_poule_locale"], 1.0)
    h["nb_oeufs"] = h["effectif_fin_semaine"].to_numpy() * taux * rng.lognormal(0, 0.06, len(h))
    h["nb_pondeuses"] = np.where(taux > 0, h["effectif_fin_semaine"], 0)
    oeufs = h[h["nb_oeufs"] >= 1].groupby(["date", "id_exploitation"], as_index=False).agg(
        nb_oeufs=("nb_oeufs", "sum"), nb_pondeuses=("nb_pondeuses", "sum"))
    oeufs["nb_oeufs"] = oeufs["nb_oeufs"].round().astype(int)

    prod = lait.merge(oeufs, on=["date", "id_exploitation"], how="outer").sort_values(["date", "id_exploitation"]).reset_index(drop=True)
    prod = prod[["date", "id_exploitation", "litres_lait", "nb_vaches_lactation", "nb_oeufs", "nb_pondeuses"]]
    prod = prod[(prod["date"] >= pd.Timestamp(cfg["projet"]["periode"]["debut"]))].reset_index(drop=True)
    n = len(prod)

    # ------------------------------------------------------------------ défauts typiques d'Excel
    cle = prod["date"].dt.strftime("%Y-%m-%d") + "|" + prod["id_exploitation"]
    k = max(3, int(n * p["defauts"]["taux"] / 4))
    etiq = []
    dates_txt = prod["date"].astype(object)
    litres_obj = prod["litres_lait"].astype(object)
    i1 = rng.choice(n, k, replace=False)
    dates_txt.iloc[i1] = prod["date"].iloc[i1].dt.strftime("%d/%m/%Y")
    etiq += [("production", c, "date_en_texte") for c in cle.iloc[i1]]
    cand = np.flatnonzero(prod["litres_lait"].notna())
    i2 = rng.choice(cand, k, replace=False)
    litres_obj.iloc[i2] = -prod["litres_lait"].iloc[i2]
    etiq += [("production", c, "litres_negatifs") for c in cle.iloc[i2]]
    i3 = rng.choice(np.setdiff1d(cand, i2), k, replace=False)
    litres_obj.iloc[i3] = prod["litres_lait"].iloc[i3] * 10
    etiq += [("production", c, "valeur_aberrante") for c in cle.iloc[i3]]
    i4 = rng.choice(np.setdiff1d(cand, np.concatenate([i2, i3])), k, replace=False)
    litres_obj.iloc[i4] = prod["litres_lait"].iloc[i4].map(lambda v: f"{v:.1f}".replace(".", ","))
    etiq += [("production", c, "decimale_virgule") for c in cle.iloc[i4]]

    # ------------------------------------------------------------------ écriture du classeur
    sortie = RACINE / p["sortie"]
    sortie.mkdir(parents=True, exist_ok=True)
    wb = Workbook(write_only=True)
    entete = ["date", "id_exploitation", "litres_lait", "nb_vaches_lactation", "nb_oeufs", "nb_pondeuses"]
    annees = prod["date"].dt.year
    for an in sorted(annees.unique()):
        ws = wb.create_sheet(f"Production_{an}")
        ws.append(entete)
        idx = np.flatnonzero(annees.to_numpy() == an)
        for r in idx:
            d = dates_txt.iat[r]
            ws.append([d.date() if hasattr(d, "date") else d, prod["id_exploitation"].iat[r],
                       None if pd.isna(litres_obj.iat[r]) else litres_obj.iat[r],
                       None if pd.isna(prod["nb_vaches_lactation"].iat[r]) else int(prod["nb_vaches_lactation"].iat[r]),
                       None if pd.isna(prod["nb_oeufs"].iat[r]) else int(prod["nb_oeufs"].iat[r]),
                       None if pd.isna(prod["nb_pondeuses"].iat[r]) else int(prod["nb_pondeuses"].iat[r])])
    wb.save(sortie / "production_lait_oeufs.xlsx")
    prod.to_csv(verite / "production_propre.csv", index=False, encoding="utf-8")
    pd.DataFrame(etiq, columns=["table", "identifiant", "type_defaut"]).to_csv(verite / "defauts_production.csv", index=False)

    # ------------------------------------------------------------------ contrôles
    print(f"=== {n} lignes de production ({prod['litres_lait'].notna().sum()} avec lait, {prod['nb_oeufs'].notna().sum()} avec œufs) ===")
    print("Lignes par année :", annees.value_counts().sort_index().to_dict(), "| défauts volontaires :", len(etiq))
    pr = prod.merge(expl[["id_exploitation", "region"]], on="id_exploitation")
    print("\nLait produit (milliers de litres) par région et par année :")
    print((pr.pivot_table(index="region", columns=pr["date"].dt.year, values="litres_lait", aggfunc="sum") / 1000).round(0).to_string())
    m = pr.groupby(pr["date"].dt.month)["litres_lait"].mean().round(1)
    print("\nLitres par exploitation et par jour, selon le mois (saisonnalité) :", m.to_dict())
    print("Œufs par jour de production, en moyenne :", int(prod["nb_oeufs"].mean()))
    print("Écrit dans", sortie.relative_to(RACINE))


if __name__ == "__main__":
    main()
