"""Génère la source 9 : alimentation et fourrage (CSV).

Une ligne par exploitation, par espèce (ou par lot de volailles), par type d'aliment et par semaine.
Ruminants : fourrage acheté (plus quand les pâturages sont secs : NDVI bas), concentré, sel minéral.
Volailles : aliment démarrage / croissance / finition (chair), pondeuse (ponte), grains (poules locales).
Les prix augmentent avec l'inflation et, pour le fourrage, en saison sèche. Une petite part de l'aliment
volaille est facturée en dollars (aliment importé), pour exercer la conversion de devises.

Sorties  data/generated/alimentation/alimentation.csv  (avec défauts volontaires)
         data/generated/pilotes/alimentation_propre.csv, defauts_alimentation.csv

Lancer depuis la racine du dépôt :  python generators/07_alimentation.py
"""
import numpy as np
import pandas as pd

from common import (EPOQUE, ESP, RACINE, charger_cfg, dossier_ref, dossier_verite, jour, jours, mois_periode,
                    table_mois, taux_usd)

LIBELLES = {"fourrage": "Fourrage (foin, résidus de culture)", "concentre": "Concentré (tourteau de coton)",
            "sel": "Sel et minéraux", "demarrage": "Aliment volaille démarrage", "croissance": "Aliment volaille croissance",
            "finition": "Aliment volaille finition", "pondeuse": "Aliment volaille pondeuse", "local": "Grains et déchets (poules locales)"}


def main():
    cfg = charger_cfg()
    a = cfg["alimentation"]
    rng = np.random.default_rng(cfg["projet"]["graine"] + 6)
    ref, verite = dossier_ref(cfg), dossier_verite(cfg)
    expl = pd.read_csv(ref / "ref_exploitations.csv")
    ids = expl["id_exploitation"].tolist()
    nf, fid = len(ids), {x: i for i, x in enumerate(ids)}
    ani = pd.read_csv(verite / "animal_propre.csv", parse_dates=["date_entree", "date_sortie"])
    lots = pd.read_csv(verite / "lot_propre.csv", parse_dates=["date_mise_en_place"])
    hebdo = pd.read_csv(RACINE / cfg["cheptel"]["sortie"] / "suivi_lot_semaine.csv", parse_dates=["date_semaine"])
    pil = pd.read_csv(verite / "pilotes_exploitation_mois.csv", parse_dates=["mois"])
    Z = table_mois(pil, "ndvi_z", ids).to_numpy()
    mois = mois_periode(cfg)
    nm = len(mois)
    usd = taux_usd(cfg)
    D0, D1 = jour(mois[0]), jour(cfg["projet"]["periode"]["fin"])
    semaines = np.arange(D0, D1 + 1, 7)

    def idx_mois(ts):
        return int(np.clip((ts.year - mois[0].year) * 12 + ts.month - mois[0].month, 0, nm - 1))

    def prix(cle, ts):
        base = a["prix_kg_xaf"][cle] * (1 + a["inflation_annuelle"]) ** ((ts - pd.Timestamp("2023-01-01")).days / 365.25)
        if cle == "fourrage":
            base *= 1 + a["amplitude_saison_fourrage"] * np.cos(2 * np.pi * (ts.month - 3) / 12)
        return base

    # ------------------------------------------------------------------ ruminants (par semaine)
    farm = ani["id_exploitation"].map(fid).to_numpy()
    esp = ani["espece"].map({e: i for i, e in enumerate(ESP)}).to_numpy()
    entree = jours(ani["date_entree"])
    sortie = np.where(ani["date_sortie"].notna(), jours(ani["date_sortie"]), 10 ** 7)
    key = farm * 3 + esp
    part0 = expl["systeme_elevage"].map(a["part_achetee_fourrage"]).to_numpy(float)
    kgj = np.array([a["kg_tete_jour"][e] for e in ESP])
    conc = np.array([a["concentre_kg_tete_jour"][e] for e in ESP])
    sel = np.array([a["sel_kg_tete_semaine"][e] for e in ESP])
    morceaux = []
    for k, w in enumerate(semaines):
        ts = EPOQUE + pd.Timedelta(days=int(w))
        mi = idx_mois(ts)
        n_key = np.bincount(key[(entree <= w) & (sortie > w)], minlength=nf * 3).reshape(nf, 3)
        fi, si = np.nonzero(n_key > 0)
        n = n_key[fi, si]
        part = np.clip(part0[fi] + a["sensibilite_ndvi"] * (-Z[fi, mi]), 0.0, 0.9)
        qtes = [("fourrage", n * kgj[si] * 7 * part), ("concentre", n * a["part_troupeau_concentre"] * conc[si] * 7 * np.ones(len(n)))]
        if k % 4 == 0:
            qtes.append(("sel", n * sel[si] * 4))
        for cle, q in qtes:
            morceaux.append(pd.DataFrame({
                "date_semaine": ts, "id_exploitation": np.array(ids)[fi], "espece": np.array(ESP)[si], "id_lot": None,
                "cle": cle, "quantite_kg": q * rng.lognormal(0, 0.10, len(q)), "prix_xaf": prix(cle, ts)}))

    # ------------------------------------------------------------------ volailles (par lot et par semaine)
    h = hebdo.merge(lots[["id_lot", "id_exploitation", "type_production", "race", "date_mise_en_place"]], on="id_lot")
    age = ((h["date_semaine"] - h["date_mise_en_place"]).dt.days / 7).to_numpy()
    chair = (h["type_production"] == "chair").to_numpy()
    locale = (h["race"] == "Poule locale").to_numpy()
    cle = np.where(chair, np.where(age < 3, "demarrage", np.where(age < 6, "croissance", "finition")),
                   np.where(locale, "local", np.where(age < 18, "croissance", "pondeuse")))
    kg = np.array([a["kg_oiseau_jour"][c] for c in cle])
    prix_v = np.array([prix(c, t) for c, t in zip(cle, h["date_semaine"])])
    morceaux.append(pd.DataFrame({
        "date_semaine": h["date_semaine"].to_numpy(), "id_exploitation": h["id_exploitation"].to_numpy(), "espece": "Volailles",
        "id_lot": h["id_lot"].to_numpy(), "cle": cle, "quantite_kg": h["effectif_fin_semaine"].to_numpy() * kg * 7 * rng.lognormal(0, 0.08, len(h)),
        "prix_xaf": prix_v}))

    df = pd.concat(morceaux, ignore_index=True)
    df = df[df["quantite_kg"] > 0].copy()
    n = len(df)
    df["prix_xaf"] = df["prix_xaf"] * rng.lognormal(0, 0.05, n)
    usd_ligne = (df["espece"] == "Volailles").to_numpy() & (rng.random(n) < a["part_volaille_usd"])
    taux = np.array([usd(t.year, t.month) for t in df["date_semaine"]])
    df["prix_unitaire"] = np.where(usd_ligne, df["prix_xaf"] / taux, df["prix_xaf"])
    df["devise"] = np.where(usd_ligne, "USD", "XAF")
    df["quantite_kg"] = df["quantite_kg"].round(1)
    df["prix_unitaire"] = np.where(usd_ligne, df["prix_unitaire"].round(3), df["prix_unitaire"].round(1))
    df["cout_total"] = np.round(df["quantite_kg"] * df["prix_unitaire"], 2)
    df["type_aliment"] = df["cle"].map(LIBELLES)
    df = df.sort_values(["date_semaine", "id_exploitation", "espece", "type_aliment"]).reset_index(drop=True)
    df.insert(0, "id_alimentation", [f"ALI-{i:07d}" for i in range(1, n + 1)])
    df["updated_at"] = pd.to_datetime(df["date_semaine"]) + pd.to_timedelta(rng.integers(0, 86400, n), unit="s")
    cols = ["id_alimentation", "date_semaine", "id_exploitation", "espece", "id_lot", "type_aliment", "quantite_kg",
            "prix_unitaire", "devise", "cout_total", "updated_at"]
    propre = df[cols].copy()

    # ------------------------------------------------------------------ défauts volontaires
    obs, etiq = propre.copy(), []
    k = max(3, int(n * a["defauts"]["taux"] / 3))
    i = rng.choice(obs.index, k, replace=False)
    obs.loc[i, "quantite_kg"] = -obs.loc[i, "quantite_kg"]
    etiq += [("alimentation", x, "quantite_negative") for x in obs.loc[i, "id_alimentation"]]
    i = rng.choice(obs.index, k, replace=False)
    obs.loc[i, "quantite_kg"] = obs.loc[i, "quantite_kg"] / 1000  # quantité saisie en tonnes au lieu de kilos
    etiq += [("alimentation", x, "unite_en_tonnes") for x in obs.loc[i, "id_alimentation"]]
    i = rng.choice(obs.index, k, replace=False)
    obs.loc[i, "prix_unitaire"] = None
    etiq += [("alimentation", x, "prix_manquant") for x in obs.loc[i, "id_alimentation"]]

    sortie_d = RACINE / a["sortie"]
    sortie_d.mkdir(parents=True, exist_ok=True)
    obs.to_csv(sortie_d / "alimentation.csv", index=False, encoding="utf-8")
    propre.to_csv(verite / "alimentation_propre.csv", index=False, encoding="utf-8")
    pd.DataFrame(etiq, columns=["table", "identifiant", "type_defaut"]).to_csv(verite / "defauts_alimentation.csv", index=False)

    # ------------------------------------------------------------------ contrôles
    print(f"=== {len(obs)} lignes d'alimentation (dont {len(etiq)} défauts volontaires) ===")
    print("\nQuantités et coûts par type d'aliment :")
    t = propre.groupby("type_aliment").agg(lignes=("id_alimentation", "size"), tonnes=("quantite_kg", lambda s: s.sum() / 1000))
    print(t.round(0).to_string())
    print("\nLignes facturées en dollars :", int((propre["devise"] == "USD").sum()))
    f = propre[propre["type_aliment"] == LIBELLES["fourrage"]].copy()
    f["mois"] = f["date_semaine"].dt.month
    nb = f.groupby("mois")["quantite_kg"].mean().round(1)
    print("\nFourrage acheté par ligne et par mois (doit monter en saison sèche) :", nb.to_dict())
    print("Écrit dans", sortie_d.relative_to(RACINE))


if __name__ == "__main__":
    main()
