"""Génère la source 5 : vaccinations (base MySQL src_vaccinations).

Ruminants : une ligne par dose et par animal. Volailles : une ligne par dose et par lot.
Chaque dose due est réalisée à l'heure avec une probabilité égale à la « conformité vaccinale »
de l'exploitation (facteur caché calculé par 02_pilotes.py) ; sinon elle est rattrapée en retard
(part_retard_rattrape) ou jamais faite. La couverture mesurée plus tard dans l'entrepôt
retrouvera donc ce comportement.

Entrées  : data/generated/pilotes/animal_propre.csv, lot_propre.csv, pilotes_exploitation_mois.csv,
           affectation_veterinaire.csv ; référentiel (vaccins, maladies, exploitations, vétérinaires)
Sorties  : data/generated/vaccinations/vaccination.csv, vaccin.csv  (avec défauts volontaires)
           data/generated/pilotes/vaccination_propre.csv, defauts_vaccinations.csv

Lancer depuis la racine du dépôt :  python generators/04_vaccinations.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RACINE = Path(__file__).resolve().parents[1]
ESP = ["Bovins", "Ovins", "Caprins"]
EPOQUE = pd.Timestamp("1970-01-01")


def jour(ts):
    return int((pd.Timestamp(ts) - EPOQUE).days)


def jours(s, defaut=0):
    """Série de dates -> numéros de jour (entiers) ; valeur manquante -> défaut."""
    return ((pd.to_datetime(s) - EPOQUE).dt.days.fillna(defaut)).astype(int).to_numpy()


def dates(j):
    return pd.to_datetime(np.asarray(j), unit="D")


def charger():
    cfg = yaml.safe_load(open(RACINE / "config" / "params.yaml", encoding="utf-8"))
    ref = RACINE / cfg["chemins"]["sortie_referentiel"]
    verite = RACINE / cfg["signal"]["sortie_pilotes"]
    d = dict(
        vaccins=pd.read_csv(ref / "ref_vaccins.csv"),
        maladies=pd.read_csv(ref / "ref_maladies.csv"),
        expl=pd.read_csv(ref / "ref_exploitations.csv"),
        vets=pd.read_csv(ref / "ref_veterinaires.csv"),
        ani=pd.read_csv(verite / "animal_propre.csv", parse_dates=["date_naissance", "date_entree", "date_sortie"]),
        lots=pd.read_csv(verite / "lot_propre.csv", parse_dates=["date_mise_en_place", "date_sortie"]),
        pil=pd.read_csv(verite / "pilotes_exploitation_mois.csv", parse_dates=["mois"]),
        aff=pd.read_csv(verite / "affectation_veterinaire.csv"),
    )
    return cfg, d


def main():
    cfg, d = charger()
    v = cfg["vaccinations"]
    rng = np.random.default_rng(cfg["projet"]["graine"] + 4)
    expl, ani, lots, vaccins, maladies = d["expl"], d["ani"], d["lots"], d["vaccins"], d["maladies"]
    ids = expl["id_exploitation"].tolist()
    nf, fid = len(ids), {x: i for i, x in enumerate(ids)}
    mois = pd.date_range(cfg["projet"]["periode"]["debut"], cfg["projet"]["periode"]["fin"], freq="MS")
    nm = len(mois)
    D0, D1 = jour(mois[0]), jour(cfg["projet"]["periode"]["fin"])
    C = d["pil"].pivot(index="id_exploitation", columns="mois", values="conformite_vaccinale").reindex(ids).to_numpy()

    # table de correspondance « numéro de jour -> indice de mois »
    base = D0 - 900
    t = dates(np.arange(base, D1 + 900))
    LOOK = np.clip(np.asarray((t.year - mois[0].year) * 12 + t.month - mois[0].month), 0, nm - 1)

    def mi(x):
        return LOOK[np.asarray(x) - base]

    nom_vaccin = dict(zip(vaccins["code_vaccin"], vaccins["vaccin"]))
    mal_vaccin = dict(zip(vaccins["code_vaccin"], vaccins["code_maladie"]))
    nom_maladie = dict(zip(maladies["code_maladie"], maladies["maladie"]))
    rappel = dict(zip(vaccins["code_vaccin"], vaccins["rappel_jours"]))

    # ------------------------------------------------------------------ ruminants
    farm = ani["id_exploitation"].map(fid).to_numpy()
    naiss, entree = jours(ani["date_naissance"]), jours(ani["date_entree"])
    a_sortie = ani["date_sortie"].notna().to_numpy()
    w_end = np.minimum(np.where(a_sortie, jours(ani["date_sortie"]), D1), D1)
    w_start = np.maximum(entree, D0)
    recs, stats = [], []

    for _, vv in vaccins.iterrows():
        code = vv["code_vaccin"]
        for esp in str(vv["especes_cibles"]).split(";"):
            if esp not in ESP:
                continue
            mask = (ani["espece"] == esp).to_numpy() & (w_end >= w_start)
            if code == "V_BRU":
                mask &= (ani["sexe"] == "F").to_numpy()
            mask &= (rng.random(nf) < v["participation_ferme"].get(f"{code}|{esp}", 1.0))[farm]
            pos = np.flatnonzero(mask)
            if len(pos) == 0:
                continue
            we = w_end[pos]
            if pd.isna(vv["rappel_jours"]):  # dose unique (brucellose : à 6 mois)
                due = naiss[pos] + 180
                ok = (due >= w_start[pos]) & (due <= we)
                pos, due, we = pos[ok], due[ok], we[ok]
                on = rng.random(len(pos)) < C[farm[pos], mi(due)]
                date = due + rng.integers(0, 15, len(pos))
                fait = on & (date <= we) & (date <= D1)
                stats.append((farm[pos], on))
                recs.append(dict(pos=pos[fait], code=code, date=date[fait], numero=np.ones(fait.sum(), int), rappel=np.nan))
                continue
            I = int(vv["rappel_jours"])
            initial = (entree[pos] <= D0) & ((D0 - naiss[pos]) >= 90)
            due = np.where(initial, D0 + rng.integers(0, I, len(pos)),
                           np.maximum(entree[pos], naiss[pos] + 90) + rng.integers(0, 30, len(pos)))
            numero = np.where(initial, 1, 0)  # doses déjà reçues avant 2023 pour le cheptel initial
            while True:
                ix = np.flatnonzero(due <= we)
                if len(ix) == 0:
                    break
                on = rng.random(len(ix)) < C[farm[pos[ix]], mi(due[ix])]
                tard = (~on) & (rng.random(len(ix)) < v["part_retard_rattrape"])
                date = np.where(on, due[ix] + rng.integers(0, 15, len(ix)), due[ix] + rng.integers(30, 150, len(ix)))
                fait = (on | tard) & (date <= we[ix]) & (date <= D1)
                stats.append((farm[pos[ix]], on))
                sel = ix[fait]
                recs.append(dict(pos=pos[sel], code=code, date=date[fait], numero=numero[sel] + 1, rappel=float(I)))
                numero[sel] += 1
                due[ix] = np.where(fait, date, due[ix]) + I

    lignes = []
    for r in recs:
        if len(r["pos"]) == 0:
            continue
        a = ani.iloc[r["pos"]]
        lignes.append(pd.DataFrame({
            "id_exploitation": a["id_exploitation"].to_numpy(), "id_animal": a["id_animal"].to_numpy(), "id_lot": None,
            "espece": a["espece"].to_numpy(), "code_vaccin": r["code"], "numero_dose": r["numero"],
            "date_vaccination": r["date"], "rappel_j": r["rappel"], "nb_animaux_vaccines": 1}))

    # ------------------------------------------------------------------ volailles (lots)
    vol = []
    for _, L in lots.iterrows():
        f = fid[L["id_exploitation"]]
        start = jour(L["date_mise_en_place"])
        fin = min(jour(L["date_sortie"]) if pd.notna(L["date_sortie"]) else D1, D1)
        if L["type_production"] == "chair":
            plan = [("V_BIA", start + 5, 1, np.nan), ("V_NEW", start + 7, 1, 14.0), ("V_NEW", start + 21, 2, np.nan)]
        else:
            plan = []
            for code in ("V_NEW", "V_BIA"):
                dd, k = start + 7, 1
                while dd <= fin:
                    plan.append((code, dd, k, float(rappel[code])))
                    dd, k = dd + int(rappel[code]), k + 1
        for code, dd, num, rj in plan:
            if dd < D0 or dd > fin:
                continue
            on = rng.random() < C[f, mi(dd)]
            stats.append((np.array([f]), np.array([on])))
            if on:
                vol.append((L["id_exploitation"], L["id_lot"], code, num, dd, rj,
                            int(L["effectif_initial"] * rng.uniform(0.92, 1.0))))
    if vol:
        w = pd.DataFrame(vol, columns=["id_exploitation", "id_lot", "code_vaccin", "numero_dose", "date_vaccination",
                                       "rappel_j", "nb_animaux_vaccines"])
        w["id_animal"], w["espece"] = None, "Volailles"
        lignes.append(w)

    df = pd.concat(lignes, ignore_index=True)
    df["sujet"] = df["id_animal"].fillna(df["id_lot"])
    df = df.sort_values(["date_vaccination", "sujet", "code_vaccin"]).reset_index(drop=True)
    df["date_rappel_prevue"] = dates(df["date_vaccination"] + df["rappel_j"].fillna(0)).where(df["rappel_j"].notna())
    suiv = df.groupby(["sujet", "code_vaccin"])["date_vaccination"].shift(-1)
    df["date_rappel_realisee"] = dates(suiv.fillna(0)).where(suiv.notna() & df["rappel_j"].notna())
    df["date_vaccination"] = dates(df["date_vaccination"])
    df["vaccin"] = df["code_vaccin"].map(nom_vaccin)
    df["maladie_ciblee"] = df["code_vaccin"].map(mal_vaccin).map(nom_maladie)

    # vétérinaire : celui de l'exploitation (90 %), sinon un autre vétérinaire du même département
    vet = df["id_exploitation"].map(d["aff"].set_index("id_exploitation")["id_veterinaire"]).to_numpy(dtype=object)
    autre = rng.random(len(df)) < v["part_autre_veterinaire"]
    dep = df["id_exploitation"].map(expl.set_index("id_exploitation")["pcode_departement"]).to_numpy()
    for pc, g in d["vets"].groupby("pcode_departement"):
        m = autre & (dep == pc)
        if m.any():
            vet[m] = rng.choice(g["id_veterinaire"].to_numpy(), m.sum())
    df["id_veterinaire"] = vet
    df["updated_at"] = df["date_vaccination"] + pd.to_timedelta(rng.integers(0, 86400, len(df)), unit="s")
    df.insert(0, "id_vaccination", [f"VAC-{i:07d}" for i in range(1, len(df) + 1)])
    cols = ["id_vaccination", "id_exploitation", "id_animal", "id_lot", "espece", "code_vaccin", "vaccin", "maladie_ciblee",
            "numero_dose", "date_vaccination", "date_rappel_prevue", "date_rappel_realisee", "id_veterinaire",
            "nb_animaux_vaccines", "updated_at"]
    propre = df[cols].copy()

    # ------------------------------------------------------------------ défauts volontaires
    obs = propre.copy()
    k = max(3, int(len(obs) * v["defauts"]["taux"] / 3))
    etiq = []
    i1 = rng.choice(obs.index, k, replace=False)
    obs.loc[i1, "date_vaccination"] = obs.loc[i1, "date_vaccination"] + pd.Timedelta(days=730)
    etiq += [("vaccination", x, "date_future") for x in obs.loc[i1, "id_vaccination"]]
    i2 = rng.choice(obs.index, k, replace=False)
    obs.loc[i2, "id_veterinaire"] = None
    etiq += [("vaccination", x, "veterinaire_manquant") for x in obs.loc[i2, "id_vaccination"]]
    i3 = rng.choice(obs.index, k, replace=False)
    dup = obs.loc[i3].copy()
    dup["id_vaccination"] = [f"VAC-{len(propre) + i + 1:07d}" for i in range(k)]
    etiq += [("vaccination", x, "doublon") for x in dup["id_vaccination"]]
    obs = pd.concat([obs, dup], ignore_index=True)

    sortie = RACINE / v["sortie"]
    verite = RACINE / cfg["signal"]["sortie_pilotes"]
    sortie.mkdir(parents=True, exist_ok=True)
    obs.to_csv(sortie / "vaccination.csv", index=False, encoding="utf-8")
    vaccins.assign(maladie=vaccins["code_maladie"].map(nom_maladie)).to_csv(sortie / "vaccin.csv", index=False, encoding="utf-8")
    propre.to_csv(verite / "vaccination_propre.csv", index=False, encoding="utf-8")
    pd.DataFrame(etiq, columns=["table", "identifiant", "type_defaut"]).to_csv(verite / "defauts_vaccinations.csv", index=False, encoding="utf-8")

    # ------------------------------------------------------------------ contrôles
    print(f"=== {len(obs)} lignes de vaccination (dont {len(etiq)} défauts volontaires) ===")
    print("\nDoses par vaccin :")
    print(propre["code_vaccin"].value_counts().to_string())
    print("\nDoses par année :", propre["date_vaccination"].dt.year.value_counts().sort_index().to_dict())
    print("Lots : %d lignes ; animaux : %d lignes" % (propre["id_lot"].notna().sum(), propre["id_animal"].notna().sum()))
    sf = np.concatenate([s[0] for s in stats])
    so = np.concatenate([s[1] for s in stats])
    reg = expl["region"].to_numpy()[sf]
    conf = d["pil"].groupby("region")["conformite_vaccinale"].mean()
    tab = pd.DataFrame({"doses_a_temps_%": pd.Series(so).groupby(reg).mean() * 100, "conformite_moyenne_%": conf * 100}).round(1)
    print("\nDoses dues réalisées à temps, par région (doit suivre la conformité moyenne) :")
    print(tab.to_string())
    an = 2024
    fin_an = pd.Timestamp(f"{an}-12-31")
    b = ani[ani["espece"] == "Bovins"]
    pres = b[(b["date_entree"] <= fin_an - pd.Timedelta(days=90)) & (b["date_sortie"].isna() | (b["date_sortie"] > fin_an))]
    fa = propre[(propre["code_vaccin"] == "V_FA") & (propre["espece"] == "Bovins") & (propre["date_vaccination"] <= fin_an)]
    derniere = fa.groupby("id_animal")["date_vaccination"].max()
    ecart = (fin_an - pres["id_animal"].map(derniere)).dt.days
    a_jour = (ecart <= 210).sum()  # rappel tous les 180 jours + 30 jours de tolérance
    print(f"\nCouverture anti-aphteuse au 31/12/{an} (bovins présents depuis plus de 90 jours) : "
          f"{100 * a_jour / len(pres):.1f} % ({a_jour} animaux à jour sur {len(pres)})")
    print("\nÉcrit dans", sortie.relative_to(RACINE))


if __name__ == "__main__":
    main()
