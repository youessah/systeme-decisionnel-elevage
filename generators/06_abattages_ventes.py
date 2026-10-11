"""Génère la source 7 (abattages, CSV) et la source 10 (marché à bétail, CSV).

Ces deux sources dérivent des sorties du cheptel (source 4) : un animal qui sort avec le motif « abattage »
apparaît dans les abattages, un animal « vendu » apparaît dans le marché. Les lots de volailles suivent la même
logique (lots de chair en partie abattus, en partie vendus vivants ; poules de réforme vendues).

Sorties  data/generated/abattages/abattage.csv
         data/generated/marche/vente.csv, releve_prix.csv      (avec défauts volontaires)
         data/generated/pilotes/abattage_propre.csv, vente_propre.csv, defauts_abattages.csv, defauts_marche.csv

Lancer depuis la racine du dépôt :  python generators/06_abattages_ventes.py
"""
import numpy as np
import pandas as pd

from common import (ESP, JOURS, RACINE, charger_cfg, dossier_ref, dossier_verite, taux_usd, valeur_mois)


def poids_vif(df, cfg, rng, ndvi_z):
    """Poids vif d'un animal à sa sortie : poids adulte de sa race x courbe de croissance x sexe x saison."""
    a = cfg["abattages"]
    adulte = {f"{e}|{r}": p for e, d in a["poids_adulte_kg"].items() for r, p in d.items()}
    moy = df["espece"].map({e: float(np.mean(list(d.values()))) for e, d in a["poids_adulte_kg"].items()})
    base = (df["espece"] + "|" + df["race"]).map(adulte).fillna(moy).to_numpy(float)
    age = ((df["date_sortie"] - df["date_naissance"]).dt.days / JOURS).to_numpy()
    tau = df["espece"].map(a["tau_croissance_mois"]).to_numpy(float)
    sexe = np.where(df["sexe"].to_numpy() == "F", 0.85, 1.0)
    w = base * (1 - 0.9 * np.exp(-age / tau)) * sexe * (1 + 0.03 * np.nan_to_num(ndvi_z)) * rng.lognormal(0, 0.08, len(df))
    return np.maximum(w, 4.0)


def facteur_prix(esp, d, cfg):
    """Facteur multiplicatif du prix : inflation, saison (bovins), Tabaski (petits ruminants)."""
    m = cfg["marche"]
    d = pd.to_datetime(pd.Series(d)).reset_index(drop=True)
    infl = (1 + m["inflation_annuelle"]) ** (((d - pd.Timestamp("2023-01-01")).dt.days / 365.25).to_numpy())
    sais = np.where(esp == "Bovins", 1 + m["amplitude_saison"] * np.sin(2 * np.pi * (d.dt.month.to_numpy() - 4) / 12), 1.0)
    fete = {pd.Timestamp(x).to_period("M") for x in cfg["cheptel"]["mois_tabaski"]}
    per = d.dt.to_period("M")
    est_fete = per.isin(fete).to_numpy()
    est_veille = (per + 1).isin(fete).to_numpy()
    f = np.ones(len(d))
    for e, ft in m["facteur_tabaski"].items():
        sel = esp == e
        f = np.where(sel & est_fete, ft, np.where(sel & est_veille, 1 + (ft - 1) * 0.35, f))
    return infl * sais * f


def main():
    cfg = charger_cfg()
    rng = np.random.default_rng(cfg["projet"]["graine"] + 5)
    ref, verite = dossier_ref(cfg), dossier_verite(cfg)
    expl = pd.read_csv(ref / "ref_exploitations.csv")
    marches = pd.read_csv(ref / "ref_marches.csv")
    ani = pd.read_csv(verite / "animal_propre.csv", parse_dates=["date_naissance", "date_entree", "date_sortie"])
    lots = pd.read_csv(verite / "lot_propre.csv", parse_dates=["date_mise_en_place", "date_sortie"])
    pil = pd.read_csv(verite / "pilotes_exploitation_mois.csv", parse_dates=["mois"])
    ndvi = pil.set_index(["id_exploitation", "mois"])["ndvi_z"]
    usd = taux_usd(cfg)
    region_de = expl.set_index("id_exploitation")["region"]
    dep_de = expl.set_index("id_exploitation")["pcode_departement"]
    ville_de = marches.set_index("pcode_departement")["ville"]
    ab_cfg, m_cfg = cfg["abattages"], cfg["marche"]

    # ----------------------------------------------------------------- sorties de ruminants
    sort = ani[ani["motif_sortie"].isin(["abattage", "vente"])].copy()
    sort["poids"] = poids_vif(sort, cfg, rng, valeur_mois(ndvi, sort["id_exploitation"], sort["date_sortie"]))
    ruminants = pd.DataFrame({
        "id_exploitation": sort["id_exploitation"], "id_animal": sort["id_animal"], "id_lot": None,
        "espece": sort["espece"], "nb": 1, "date": sort["date_sortie"], "poids_total": sort["poids"],
        "motif": sort["motif_sortie"]})

    # ----------------------------------------------------------------- lots de volailles
    debut_periode = pd.Timestamp(cfg["projet"]["periode"]["debut"])
    fin = lots[lots["date_sortie"].notna() & (lots["date_sortie"] >= debut_periode)].copy()  # sorties de la période seulement
    surv = np.maximum(fin["effectif_initial"] - fin["nb_morts_total"], 1)
    cycle = (fin["date_sortie"] - fin["date_mise_en_place"]).dt.days
    chair = (fin["type_production"] == "chair").to_numpy()
    poids = np.where(chair, surv * ab_cfg["poids_poulet_par_jour_kg"] * cycle, surv * 1.8) * rng.normal(1, 0.05, len(fin))
    abattu = chair & (rng.random(len(fin)) < ab_cfg["part_lots_chair_abattus"])
    volailles = pd.DataFrame({
        "id_exploitation": fin["id_exploitation"], "id_animal": None, "id_lot": fin["id_lot"], "espece": "Volailles",
        "nb": surv, "date": fin["date_sortie"], "poids_total": poids,
        "motif": np.where(abattu, "abattage", "vente"), "reforme": ~chair})
    volailles["reforme"] = volailles["reforme"].fillna(False)
    ruminants["reforme"] = False
    tout = pd.concat([ruminants, volailles], ignore_index=True)
    tout["region"] = tout["id_exploitation"].map(region_de)
    tout["pcode"] = tout["id_exploitation"].map(dep_de)

    # ----------------------------------------------------------------- SOURCE 7 : abattages
    ab = tout[tout["motif"] == "abattage"].sort_values(["date", "id_exploitation"]).reset_index(drop=True).copy()
    rend = ab["espece"].map(ab_cfg["rendement_carcasse"]).to_numpy(float)
    carcasse = ab["poids_total"] * rend * rng.normal(1, 0.04, len(ab))
    u = rng.random(len(ab))
    t = ab_cfg["taux_saisie"]
    statut = np.where(u < t * 0.17, "Saisie totale", np.where(u < t, "Saisie partielle", "Conforme"))
    carcasse = np.where(statut == "Saisie totale", 0.0, carcasse)
    S7 = pd.DataFrame({
        "id_abattage": [f"ABT-{i:06d}" for i in range(1, len(ab) + 1)],
        "id_exploitation": ab["id_exploitation"], "id_animal": ab["id_animal"], "id_lot": ab["id_lot"],
        "espece": ab["espece"], "nb_animaux": ab["nb"].astype(int), "date_abattage": ab["date"].dt.normalize(),
        "poids_vif_kg": ab["poids_total"].round(1), "poids_carcasse_kg": np.round(carcasse, 1),
        "abattoir": "Abattoir de " + ab["pcode"].map(ville_de), "region": ab["region"], "statut_inspection": statut})
    S7["updated_at"] = S7["date_abattage"] + pd.to_timedelta(rng.integers(0, 86400, len(S7)), unit="s")

    # ----------------------------------------------------------------- SOURCE 10 : ventes sur marché
    v = tout[tout["motif"] == "vente"].sort_values(["date", "id_exploitation"]).reset_index(drop=True).copy()
    n = len(v)
    esp = v["espece"].to_numpy()
    prix_kg = np.array([m_cfg["prix_base_kg_vif"][e] for e in esp], dtype=float)
    prix_kg = prix_kg * np.where(v["reforme"].to_numpy(bool), m_cfg["facteur_poule_reforme"], 1.0)
    # destination : catégorie puis lieu
    cat = np.empty(n, dtype=object)
    for (region, e_volaille), idx in v.groupby(["region", v["espece"] == "Volailles"]).groups.items():
        probas = dict(m_cfg["destinations"][region])
        if e_volaille:
            probas.pop("export", None)
        k = list(probas)
        p = np.array([probas[c] for c in k], dtype=float)
        cat[idx] = rng.choice(k, size=len(idx), p=p / p.sum())
    lieu = np.empty(n, dtype=object)
    for i in range(n):
        if cat[i] == "local":
            lieu[i] = "Marché local du département"
        elif cat[i] == "autre région":
            lieu[i] = rng.choice(m_cfg["villes_autre_region"])
        else:
            lieu[i] = rng.choice(m_cfg["pays_export"][v["region"].iat[i]])
    prime = np.array([m_cfg["prime_destination"][c] for c in cat])
    prix_kg = prix_kg * facteur_prix(esp, v["date"], cfg) * prime * rng.lognormal(0, 0.08, n)
    prix_xaf = prix_kg * v["poids_total"].to_numpy()
    # marché
    id_marche = np.array([marches.loc[marches["pcode_departement"] == p, "id_marche"].iloc[0] for p in v["pcode"]], dtype=object)
    autre = rng.random(n) > m_cfg["part_marche_departement"]
    for i in np.flatnonzero(autre):
        possibles = marches[(marches["region"] == v["region"].iat[i]) & (marches["id_marche"] != id_marche[i])]["id_marche"].tolist()
        if possibles:
            id_marche[i] = rng.choice(possibles)
    nom_marche = pd.Series(id_marche).map(marches.set_index("id_marche")["nom_marche"]).to_numpy()
    # devise
    en_usd = (cat == "export") & (rng.random(n) < m_cfg["part_export_en_usd"])
    taux = np.array([usd(d.year, d.month) for d in v["date"]])
    total = np.where(en_usd, prix_xaf / taux, prix_xaf)
    S10 = pd.DataFrame({
        "id_transaction": [f"TRX-{i:06d}" for i in range(1, n + 1)],
        "date_transaction": v["date"].dt.normalize(), "id_marche": id_marche, "marche": nom_marche,
        "region": v["region"], "id_exploitation": v["id_exploitation"], "id_animal": v["id_animal"], "id_lot": v["id_lot"],
        "espece": esp, "nb_tetes": v["nb"].astype(int), "poids_total_kg": v["poids_total"].round(1),
        "prix_total": np.where(en_usd, np.round(total, 2), np.round(total, 0)),
        "devise": np.where(en_usd, "USD", "XAF"), "destination_categorie": cat, "destination": lieu})
    S10["updated_at"] = S10["date_transaction"] + pd.to_timedelta(rng.integers(0, 86400, n), unit="s")

    # ----------------------------------------------------------------- relevé hebdomadaire des prix
    semaines = pd.date_range(cfg["projet"]["periode"]["debut"], cfg["projet"]["periode"]["fin"], freq="W-MON")
    taille = pd.Series(rng.lognormal(0, m_cfg["taille_marche_sigma"], len(marches)), index=marches["id_marche"])
    effet = {(mk, e): rng.lognormal(0, 0.05) for mk in marches["id_marche"] for e in ESP + ["Volailles"]}
    vol_base = {"Bovins": 120, "Ovins": 140, "Caprins": 150, "Volailles": 400}
    lignes = []
    for e in ESP + ["Volailles"]:
        f = facteur_prix(np.array([e] * len(semaines)), semaines, cfg)
        mois_fete = [pd.Timestamp(x).to_period("M") for x in cfg["cheptel"]["mois_tabaski"]]
        fete = np.where(pd.Series(semaines).dt.to_period("M").isin(mois_fete).to_numpy(), 2.2, 1.0)
        fete = fete if e in ("Ovins", "Caprins") else np.ones(len(semaines))
        for mk in marches["id_marche"]:
            moyen = m_cfg["prix_base_kg_vif"][e] * f * effet[(mk, e)] * rng.lognormal(0, 0.03, len(semaines))
            lignes.append(pd.DataFrame({
                "semaine": semaines, "id_marche": mk, "espece": e, "prix_moyen_kg_vif": np.round(moyen, 0),
                "prix_min_kg_vif": np.round(moyen * rng.uniform(0.85, 0.95, len(semaines)), 0),
                "prix_max_kg_vif": np.round(moyen * rng.uniform(1.07, 1.18, len(semaines)), 0),
                "nb_presentes": rng.poisson(vol_base[e] * taille[mk] * fete), "devise": "XAF"}))
    S10b = pd.concat(lignes, ignore_index=True).sort_values(["semaine", "id_marche", "espece"]).reset_index(drop=True)
    S10b.insert(0, "id_releve", [f"REL-{i:06d}" for i in range(1, len(S10b) + 1)])

    # ----------------------------------------------------------------- défauts volontaires
    def choisir(df, taux_, k_min=3):
        return rng.choice(df.index, max(k_min, int(len(df) * taux_ / 3)), replace=False)

    obs7, et7 = S7.copy(), []
    i = choisir(obs7, ab_cfg["defauts"]["taux"])
    obs7.loc[i, "poids_vif_kg"] = -obs7.loc[i, "poids_vif_kg"]
    et7 += [("abattage", x, "poids_negatif") for x in obs7.loc[i, "id_abattage"]]
    i = choisir(obs7, ab_cfg["defauts"]["taux"])
    obs7.loc[i, "poids_carcasse_kg"] = obs7.loc[i, "poids_vif_kg"].abs() * 1.4
    et7 += [("abattage", x, "carcasse_superieure_au_poids_vif") for x in obs7.loc[i, "id_abattage"]]
    i = choisir(obs7, ab_cfg["defauts"]["taux"])
    obs7.loc[i, "date_abattage"] = pd.NaT
    et7 += [("abattage", x, "date_absente") for x in obs7.loc[i, "id_abattage"]]

    obs10, et10 = S10.copy(), []
    i = choisir(obs10, m_cfg["defauts"]["taux"])
    obs10.loc[i, "prix_total"] = -obs10.loc[i, "prix_total"]
    et10 += [("vente", x, "prix_negatif") for x in obs10.loc[i, "id_transaction"]]
    i = choisir(obs10, m_cfg["defauts"]["taux"])
    obs10.loc[i, "poids_total_kg"] = 0
    et10 += [("vente", x, "poids_nul") for x in obs10.loc[i, "id_transaction"]]
    i = choisir(obs10, m_cfg["defauts"]["taux"])
    obs10.loc[i, "date_transaction"] = obs10.loc[i, "date_transaction"] + pd.Timedelta(days=730)
    et10 += [("vente", x, "date_future") for x in obs10.loc[i, "id_transaction"]]
    i = choisir(obs10, m_cfg["defauts"]["taux"])
    dup = obs10.loc[i].copy()
    dup["id_transaction"] = [f"TRX-{n + j + 1:06d}" for j in range(len(dup))]
    et10 += [("vente", x, "doublon") for x in dup["id_transaction"]]
    obs10 = pd.concat([obs10, dup], ignore_index=True)

    # ----------------------------------------------------------------- écriture
    d7, d10 = RACINE / ab_cfg["sortie"], RACINE / m_cfg["sortie"]
    d7.mkdir(parents=True, exist_ok=True)
    d10.mkdir(parents=True, exist_ok=True)
    obs7.to_csv(d7 / "abattage.csv", index=False, encoding="utf-8")
    obs10.to_csv(d10 / "vente.csv", index=False, encoding="utf-8")
    S10b.to_csv(d10 / "releve_prix.csv", index=False, encoding="utf-8")
    S7.to_csv(verite / "abattage_propre.csv", index=False, encoding="utf-8")
    S10.to_csv(verite / "vente_propre.csv", index=False, encoding="utf-8")
    pd.DataFrame(et7, columns=["table", "identifiant", "type_defaut"]).to_csv(verite / "defauts_abattages.csv", index=False)
    pd.DataFrame(et10, columns=["table", "identifiant", "type_defaut"]).to_csv(verite / "defauts_marche.csv", index=False)

    # ----------------------------------------------------------------- contrôles
    print(f"=== SOURCE 7 : {len(obs7)} abattages | SOURCE 10 : {len(obs10)} transactions + {len(S10b)} relevés de prix ===")
    print(f"Défauts volontaires : abattages {len(et7)}, marché {len(et10)}")
    print("\nPoids vif moyen par animal à l'abattage (kg) :")
    print(S7.groupby("espece").apply(lambda g: g["poids_vif_kg"].sum() / g["nb_animaux"].sum(), include_groups=False).round(1).to_string())
    print("\nPrix moyen au kg vif (XAF, ventes en francs CFA) par espèce et par année :")
    x = S10[S10["devise"] == "XAF"].assign(prix_kg=lambda d: d["prix_total"] / d["poids_total_kg"], an=lambda d: d["date_transaction"].dt.year)
    print(x.pivot_table(index="espece", columns="an", values="prix_kg", aggfunc="mean").round(0).to_string())
    print("\nDestination des ventes par région (%) :")
    print((pd.crosstab(S10["region"], S10["destination_categorie"], normalize="index") * 100).round(1).to_string())
    print(f"\nVentes à l'export facturées en dollars : {100 * (S10['devise'] == 'USD').sum() / max((S10['destination_categorie'] == 'export').sum(), 1):.0f} %")
    pt = S10[S10["espece"].isin(["Ovins", "Caprins"])].groupby(S10["date_transaction"].dt.month).size()
    print("Ventes de petits ruminants par mois (pic de juin = Tabaski) :", pt.to_dict())
    print(f"\nCohérence avec le cheptel : {S10['id_animal'].notna().sum()} animaux vendus dans le marché, "
          f"{(ani['motif_sortie'] == 'vente').sum()} dans le cheptel (doit être égal)")
    print("Écrit dans", d7.relative_to(RACINE), "et", d10.relative_to(RACINE))


if __name__ == "__main__":
    main()
