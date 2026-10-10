"""Génère la source 4 : cheptel par exploitation (base PostgreSQL src_cheptel).

Ruminants : un enregistrement par animal (naissances, achats, ventes, abattages, décès).
Volailles : un enregistrement par lot, plus un suivi hebdomadaire de la mortalité.
La mortalité dépend du « multiplicateur » calculé par 02_pilotes.py (chaleur, pâturages,
pression sanitaire, vaccination, délai vétérinaire).

Sorties (data/generated/cheptel) : exploitation.csv, animal.csv, lot_volaille.csv, suivi_lot_semaine.csv
  -> fichiers « observés », avec quelques défauts de qualité volontaires.
Sorties « vérité » (data/generated/pilotes) : animal_propre.csv, lot_propre.csv, defauts_cheptel.csv
  -> fichiers sans défaut, réutilisés par les générateurs suivants.

Lancer depuis la racine du dépôt :  python generators/03_cheptel.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RACINE = Path(__file__).resolve().parents[1]
ESP = ["Bovins", "Ovins", "Caprins"]
CAUSES = ["maladie", "chaleur", "manque de pâturage", "prédation", "accident", "inconnue"]
MOTIFS = {1: "deces", 2: "vente", 3: "abattage"}
JOURS = 30.44
EPOQUE = pd.Timestamp("1970-01-01")


def jour(ts):
    """Date -> numéro de jour (entier) depuis 1970 : simplifie tous les calculs de dates."""
    return int((pd.Timestamp(ts) - EPOQUE).days)


def dates(jours):
    return pd.to_datetime(np.asarray(jours), unit="D")


def tab(d, esp=ESP):
    return np.array([d[e] for e in esp], dtype=float)


def charger():
    cfg = yaml.safe_load(open(RACINE / "config" / "params.yaml", encoding="utf-8"))
    ref = RACINE / cfg["chemins"]["sortie_referentiel"]
    expl = pd.read_csv(ref / "ref_exploitations.csv")
    eff = pd.read_csv(ref / "ref_exploitation_especes.csv")
    races = pd.read_csv(ref / "ref_races.csv")
    pil = pd.read_csv(RACINE / cfg["signal"]["sortie_pilotes"] / "pilotes_exploitation_mois.csv", parse_dates=["mois"])
    return cfg, expl, eff, races, pil


# ----------------------------------------------------------------------------
def simuler_ruminants(cfg, expl, eff, races, pil, rng):
    c = cfg["cheptel"]
    ids = expl["id_exploitation"].tolist()
    nf = len(ids)
    fid = {x: i for i, x in enumerate(ids)}
    mois = pd.date_range(cfg["projet"]["periode"]["debut"], cfg["projet"]["periode"]["fin"], freq="MS")
    D0, D1 = jour(mois[0]), jour(cfg["projet"]["periode"]["fin"])
    pm = {m: d.set_index("id_exploitation").reindex(ids) for m, d in pil.groupby("mois")}
    tabaski = {jour(x) for x in pd.to_datetime(c["mois_tabaski"])}

    part_f, age_max = tab(c["part_femelles"]), tab(c["age_max_initial_mois"])
    age_rep, age_jeune = tab(c["age_reproduction_mois"]), tab(c["age_jeune_mois"])
    naiss_m, mort_b = tab(c["naissance_mensuelle_par_femelle"]), tab(c["mortalite_mensuelle_base"])
    sortie_b, fact_tab = tab(c["sortie_mensuelle_base"]), tab(c["facteur_tabaski"])

    noms_races = [races[races["espece"] == e]["race"].tolist() for e in ESP]
    nr = np.array([len(x) for x in noms_races])
    pref = np.column_stack([rng.integers(0, nr[s], nf) for s in range(3)])  # race préférée de chaque exploitation

    def race(farm, esp, n):
        return np.where(rng.random(n) < 0.7, pref[farm, esp], rng.integers(0, nr[esp]))

    held = np.zeros((nf, 3), dtype=bool)
    for _, r in eff[eff["espece"].isin(ESP)].iterrows():
        held[fid[r["id_exploitation"]], ESP.index(r["espece"])] = True
    held_key = held.ravel()  # indice = exploitation * 3 + espèce

    # --- troupeau initial (au 1er janvier 2023)
    morceaux = []
    for s, esp in enumerate(ESP):
        e = eff[eff["espece"] == esp]
        farm = np.repeat(e["id_exploitation"].map(fid).to_numpy(), e["effectif_initial"].to_numpy())
        n = len(farm)
        age_mois = 1 + rng.beta(1.0, 1.6, n) * (age_max[s] - 1)
        naiss = D0 - (age_mois * JOURS).astype(int)
        achat = rng.random(n) < 0.10
        entree = np.where(achat, naiss + (rng.random(n) * (age_mois * JOURS - 1)).astype(int), naiss)
        morceaux.append(dict(farm=farm, esp=np.full(n, s), sexe=(rng.random(n) < part_f[s]).astype(int),
                             naiss=naiss, entree=entree, type_e=achat.astype(int),
                             sortie=np.full(n, -1), motif=np.zeros(n, int), cause=np.zeros(n, int),
                             race=race(farm, np.full(n, s), n)))
    A = {k: np.concatenate([m[k] for m in morceaux]) for k in morceaux[0]}

    P = np.zeros((nf, len(mois)))   # animaux présents (pour les contrôles)
    DEC = np.zeros((nf, len(mois)))  # décès
    MULT = np.zeros((nf, len(mois)))

    for k, ms in enumerate(mois):
        jm = ms.days_in_month
        ms_d = jour(ms)
        nxt_d = jour(ms + pd.offsets.MonthBegin(1))
        p = pm[ms]
        mult, sp = p["multiplicateur_mortalite"].to_numpy(), (p["jours_stress"] / jm).to_numpy()
        nz, pz = p["ndvi_z"].to_numpy(), p["pression_z"].to_numpy()
        MULT[:, k] = mult

        pres = np.flatnonzero((A["entree"] <= ms_d) & (A["sortie"] < 0))
        f, s = A["farm"][pres], A["esp"][pres]
        age = (ms_d - A["naiss"][pres]) / JOURS
        fem = A["sexe"][pres] == 1
        P[:, k] = np.bincount(f, minlength=nf)

        # décès et sorties commerciales
        p_dec = np.minimum(mort_b[s] * mult[f] * np.where(age < age_jeune[s], c["facteur_jeune"], 1.0), 0.6)
        fte = np.where(ms_d in tabaski, fact_tab[s], np.where(nxt_d in tabaski, 1 + (fact_tab[s] - 1) / 2, 1.0))
        p_ven = sortie_b[s] * np.where(fem, 0.6, 1.8) * np.where(age < 6, 0.2, 1.0) * fte
        u = rng.random(len(pres))
        dec = u < p_dec
        ven = (~dec) & (u < p_dec + p_ven)
        jr = ms_d + rng.integers(0, jm, len(pres))
        sort = dec | ven
        A["sortie"][pres[sort]] = jr[sort]
        A["motif"][pres[dec]] = 1
        A["motif"][pres[ven]] = np.where(rng.random(ven.sum()) < c["part_abattage_sorties"], 3, 2)
        di = np.flatnonzero(dec)
        if len(di):
            ff = f[di]
            w = np.column_stack([0.40 + 0.10 * np.maximum(pz[ff], 0), 0.04 + 0.50 * sp[ff],
                                 0.08 + 0.08 * np.maximum(-nz[ff], 0), np.full(len(di), 0.05),
                                 np.full(len(di), 0.05), np.full(len(di), 0.10)])
            w = w / w.sum(axis=1, keepdims=True)
            ci = np.minimum((rng.random((len(di), 1)) > np.cumsum(w, axis=1)).sum(axis=1), 5)
            A["cause"][pres[di]] = ci + 1
        DEC[:, k] = np.bincount(f[dec], minlength=nf)

        # naissances (femelles reproductrices présentes au début du mois)
        rep = fem & (age >= age_rep[s])
        n_rep = np.bincount((f * 3 + s)[rep], minlength=nf * 3)
        seas = 1 + 0.25 * np.sin(2 * np.pi * (ms.month - 3) / 12)
        nb = rng.binomial(n_rep, np.minimum(naiss_m[np.arange(nf * 3) % 3] * seas, 1.0))
        kk = np.repeat(np.arange(nf * 3), nb)
        # achats
        n_key = np.bincount(f * 3 + s, minlength=nf * 3)
        lam = c["achats_mensuels_par_tete"] * n_key + np.where((n_key < 5) & held_key, 0.2, 0.0)
        ka = np.repeat(np.arange(nf * 3), rng.poisson(lam))

        nn, na = len(kk), len(ka)
        if nn:
            d = ms_d + rng.integers(0, jm, nn)
            A = {key: np.concatenate([A[key], val]) for key, val in dict(
                farm=kk // 3, esp=kk % 3, sexe=(rng.random(nn) < 0.5).astype(int), naiss=d, entree=d,
                type_e=np.zeros(nn, int), sortie=np.full(nn, -1), motif=np.zeros(nn, int), cause=np.zeros(nn, int),
                race=race(kk // 3, kk % 3, nn)).items()}
        if na:
            d = ms_d + rng.integers(0, jm, na)
            ag = rng.uniform(6, 36, na)
            A = {key: np.concatenate([A[key], val]) for key, val in dict(
                farm=ka // 3, esp=ka % 3, sexe=(rng.random(na) < 0.6).astype(int), naiss=(ms_d - ag * JOURS).astype(int),
                entree=d, type_e=np.ones(na, int), sortie=np.full(na, -1), motif=np.zeros(na, int),
                cause=np.zeros(na, int), race=race(ka // 3, ka % 3, na)).items()}

    # --- tableau final
    ordre = np.lexsort((A["entree"], A["esp"], A["farm"]))
    A = {k: v[ordre] for k, v in A.items()}
    n = len(A["farm"])
    fin = np.where(A["sortie"] >= 0, A["sortie"], D1)
    statut = (A["sexe"] == 1) & ((fin - A["naiss"]) / JOURS >= age_rep[A["esp"]])
    maj = np.where(A["sortie"] >= 0, A["sortie"], A["entree"])
    noms_race = np.empty(n, dtype=object)
    for s in range(3):
        m = A["esp"] == s
        noms_race[m] = np.array(noms_races[s], dtype=object)[A["race"][m]]
    ani = pd.DataFrame({
        "id_animal": [f"ANI-{i:06d}" for i in range(1, n + 1)],
        "id_exploitation": np.array(ids)[A["farm"]],
        "espece": np.array(ESP)[A["esp"]],
        "race": noms_race,
        "sexe": np.where(A["sexe"] == 1, "F", "M"),
        "date_naissance": dates(A["naiss"]),
        "type_entree": np.where(A["type_e"] == 1, "achat", "naissance"),
        "date_entree": dates(A["entree"]),
        "date_sortie": dates(np.where(A["sortie"] >= 0, A["sortie"], 0)).where(A["sortie"] >= 0),
        "motif_sortie": pd.Series([MOTIFS.get(m) for m in A["motif"]]),
        "cause_deces": pd.Series([CAUSES[x - 1] if x > 0 else None for x in A["cause"]]),
        "statut_reproducteur": np.where(statut, "Oui", "Non"),
        "updated_at": dates(maj) + pd.to_timedelta(rng.integers(0, 86400, n), unit="s"),
    })
    return ani, dict(P=P, DEC=DEC, MULT=MULT, mois=mois, ids=ids)


# ----------------------------------------------------------------------------
def simuler_volailles(cfg, expl, eff, pil, rng):
    c = cfg["cheptel"]["volailles"]
    ids = expl["id_exploitation"].tolist()
    fid = {x: i for i, x in enumerate(ids)}
    mois = pd.date_range(cfg["projet"]["periode"]["debut"], cfg["projet"]["periode"]["fin"], freq="MS")
    D0, D1 = jour(mois[0]), jour(cfg["projet"]["periode"]["fin"])
    Mmat = pil.pivot(index="id_exploitation", columns="mois", values="multiplicateur_mortalite").reindex(ids).to_numpy()
    vol = eff[eff["espece"] == "Volailles"].merge(expl[["id_exploitation", "espece_principale"]], on="id_exploitation")

    def mi(d):
        t = pd.Timestamp("1970-01-01") + pd.Timedelta(days=int(d))
        return int(np.clip((t.year - mois[0].year) * 12 + t.month - mois[0].month, 0, len(mois) - 1))

    lots, hebdo, nl = [], [], 0
    for _, r in vol.iterrows():
        f, cap = fid[r["id_exploitation"]], int(r["effectif_initial"])
        principale = r["espece_principale"] == "Volailles"
        chair = principale and rng.random() < c["part_chair_si_principale"]
        cfg_t = c["chair"] if chair else c["ponte"]
        race = "Poulet de chair" if chair else ("Pondeuse" if principale else "Poule locale")
        cyc0 = cfg_t["cycle_jours"]
        start = D0 - int(rng.integers(0, (cyc0[1] if chair else cyc0) + 20))
        while start <= D1:
            cyc = int(rng.integers(cyc0[0], cyc0[1] + 1)) if chair else int(cyc0)
            taille = max(5, int(cap * rng.uniform(0.7, 1.0)))
            nl += 1
            lot = f"LOT-{nl:05d}"
            eff_c, morts_tot, epi, epi_p = taille, 0, 0, 0.0
            for w in range(cyc // 7):
                d = start + 7 * w
                if d > D1:
                    break
                m = Mmat[f, mi(d)]
                p = cfg_t["mortalite_hebdo_base"] * m * (3.0 if (chair and w == 0) else 1.0)
                if epi > 0:
                    p, epi = epi_p * (1.0 if epi == 2 else 0.5), epi - 1
                elif rng.random() < c["probabilite_epidemie_hebdo"] * m ** 2:
                    epi_p = rng.uniform(0.10, 0.35)  # semaine d'épidémie : forte mortalité, atténuée la semaine suivante
                    p, epi = epi_p, 1
                morts = int(rng.binomial(eff_c, min(p, 0.9)))
                eff_c -= morts
                morts_tot += morts
                if d >= D0:
                    hebdo.append((lot, d, morts, eff_c))
            fin = start + cyc
            lots.append((lot, ids[f], "Volailles", "chair" if chair else "ponte", race, start, taille,
                         fin if fin <= D1 else -1, morts_tot, ("abattage" if chair else "reforme") if fin <= D1 else None,
                         min(fin, D1)))
            start = fin + int(rng.integers(cfg_t["pause_jours"][0], cfg_t["pause_jours"][1] + 1))

    L = pd.DataFrame(lots, columns=["id_lot", "id_exploitation", "espece", "type_production", "race", "date_mise_en_place",
                                    "effectif_initial", "date_sortie", "nb_morts_total", "motif_sortie", "maj"])
    L["date_mise_en_place"] = dates(L["date_mise_en_place"])
    L["date_sortie"] = dates(np.where(L["date_sortie"] >= 0, L["date_sortie"], 0)).where(L["date_sortie"] >= 0)
    L["updated_at"] = dates(L["maj"]) + pd.to_timedelta(rng.integers(0, 86400, len(L)), unit="s")
    L = L.drop(columns="maj")
    H = pd.DataFrame(hebdo, columns=["id_lot", "date_semaine", "nb_morts", "effectif_fin_semaine"])
    H["date_semaine"] = dates(H["date_semaine"])
    H.insert(0, "id_suivi", np.arange(1, len(H) + 1))
    return L, H


# ----------------------------------------------------------------------------
def injecter_defauts(ani, rng, taux):
    """Introduit des erreurs de saisie volontaires (3 types) et les consigne dans un fichier d'étiquettes."""
    obs = ani.copy()
    n = len(obs)
    k = max(3, int(n * taux / 3))
    etiquettes = []
    idx = rng.choice(obs.index[obs["date_sortie"].notna()], k, replace=False)
    obs.loc[idx, "date_sortie"] = obs.loc[idx, "date_entree"] - pd.to_timedelta(rng.integers(1, 30, k), unit="D")
    etiquettes += [("animal", i, "date_sortie_avant_entree") for i in obs.loc[idx, "id_animal"]]
    idx = rng.choice(obs.index, k, replace=False)
    obs.loc[idx, "sexe"] = None
    etiquettes += [("animal", i, "sexe_manquant") for i in obs.loc[idx, "id_animal"]]
    idx = rng.choice(obs.index, k, replace=False)
    obs.loc[idx, "espece"] = obs.loc[idx, "espece"].str.lower().str.rstrip("s")
    etiquettes += [("animal", i, "espece_mal_ecrite") for i in obs.loc[idx, "id_animal"]]
    return obs, pd.DataFrame(etiquettes, columns=["table", "identifiant", "type_defaut"])


def main():
    cfg, expl, eff, races, pil = charger()
    rng = np.random.default_rng(cfg["projet"]["graine"] + 3)
    ani, aux = simuler_ruminants(cfg, expl, eff, races, pil, rng)
    lots, hebdo = simuler_volailles(cfg, expl, eff, pil, rng)

    sortie = RACINE / cfg["cheptel"]["sortie"]
    verite = RACINE / cfg["signal"]["sortie_pilotes"]
    sortie.mkdir(parents=True, exist_ok=True)
    verite.mkdir(parents=True, exist_ok=True)

    ani.to_csv(verite / "animal_propre.csv", index=False, encoding="utf-8")
    lots.to_csv(verite / "lot_propre.csv", index=False, encoding="utf-8")
    obs, etiq = injecter_defauts(ani, rng, cfg["cheptel"]["defauts"]["taux"])
    etiq.to_csv(verite / "defauts_cheptel.csv", index=False, encoding="utf-8")

    exploitation = expl[["id_exploitation", "nom_exploitation", "proprietaire", "pcode_departement", "departement", "region",
                         "espece_principale", "systeme_elevage", "taille", "date_creation", "latitude", "longitude", "statut"]].copy()
    exploitation["updated_at"] = pd.to_datetime(exploitation["date_creation"]) + pd.to_timedelta(rng.integers(0, 86400, len(exploitation)), unit="s")
    exploitation.to_csv(sortie / "exploitation.csv", index=False, encoding="utf-8")
    obs.to_csv(sortie / "animal.csv", index=False, encoding="utf-8")
    lots.to_csv(sortie / "lot_volaille.csv", index=False, encoding="utf-8")
    hebdo.to_csv(sortie / "suivi_lot_semaine.csv", index=False, encoding="utf-8")

    # ------------------------------------------------------------------ contrôles
    P, DEC, MULT, mois = aux["P"], aux["DEC"], aux["MULT"], aux["mois"]
    print("=== FICHIERS (data/generated/cheptel) ===")
    for nom, df in [("exploitation", exploitation), ("animal", obs), ("lot_volaille", lots), ("suivi_lot_semaine", hebdo)]:
        print(f"{nom:20s}{len(df):8d} lignes")
    print(f"Défauts volontaires : {len(etiq)} ({etiq['type_defaut'].value_counts().to_dict()})")

    print("\n=== RUMINANTS : effectifs et mouvements ===")
    D0, D1 = pd.Timestamp(cfg["projet"]["periode"]["debut"]), pd.Timestamp(cfg["projet"]["periode"]["fin"])
    rec = []
    for esp in ESP:
        a = ani[ani["espece"] == esp]
        for an in (2023, 2024, 2025):
            debut_an, fin_an = pd.Timestamp(f"{an}-01-01"), pd.Timestamp(f"{an}-12-31")
            eff_d = ((a["date_entree"] <= debut_an) & (a["date_sortie"].isna() | (a["date_sortie"] >= debut_an))).sum()
            eff_f = ((a["date_entree"] <= fin_an) & (a["date_sortie"].isna() | (a["date_sortie"] > fin_an))).sum()
            nais = ((a["type_entree"] == "naissance") & (a["date_entree"].dt.year == an)).sum()
            dec = ((a["motif_sortie"] == "deces") & (a["date_sortie"].dt.year == an)).sum()
            ven = ((a["motif_sortie"].isin(["vente", "abattage"])) & (a["date_sortie"].dt.year == an)).sum()
            rec.append((esp, an, eff_d, eff_f, nais, dec, ven, round(100 * dec / max(eff_d, 1), 1), round(100 * (eff_f - eff_d) / max(eff_d, 1), 1)))
    print(pd.DataFrame(rec, columns=["espece", "annee", "effectif_debut", "effectif_fin", "naissances", "deces", "ventes_abattages",
                                     "mortalite_%", "croissance_%"]).to_string(index=False))

    print("\nCauses de décès :", ani["cause_deces"].value_counts().to_dict())
    print("Motifs de sortie :", ani["motif_sortie"].value_counts().to_dict())

    print("\n=== SIGNAL : mortalité mensuelle selon le multiplicateur (quartiles) ===")
    taux = (DEC / np.maximum(P, 1)).ravel()
    q = pd.qcut(MULT.ravel(), 4, labels=["Q1 (faible)", "Q2", "Q3", "Q4 (fort)"])
    print((pd.Series(taux).groupby(q, observed=True).mean() * 100).round(3).rename("mortalité mensuelle (%)").to_string())

    print("\n=== VOLAILLES ===")
    print(lots.groupby("type_production").agg(lots=("id_lot", "size"), effectif_moyen=("effectif_initial", "mean"),
                                              morts_totaux=("nb_morts_total", "sum")).round(0).to_string())
    print("Mortalité hebdomadaire moyenne (%) :",
          (hebdo.groupby(hebdo["id_lot"].map(lots.set_index("id_lot")["type_production"]))["nb_morts"].sum()
           / hebdo.groupby(hebdo["id_lot"].map(lots.set_index("id_lot")["type_production"]))["effectif_fin_semaine"].sum() * 100).round(2).to_dict())
    print("\nÉcrit dans", sortie.relative_to(RACINE), "et", verite.relative_to(RACINE))


if __name__ == "__main__":
    main()
