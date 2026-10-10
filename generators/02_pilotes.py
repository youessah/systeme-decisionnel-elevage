"""Construit les « facteurs cachés » de la simulation : un risque de mortalité par exploitation et par mois.

Le risque combine :
  - le stress thermique réel      (météo Open-Meteo, THI > seuil)
  - l'état réel des pâturages     (NDVI mensuel)
  - la pression sanitaire         (WAHIS réel jusqu'en 2023, simulé ensuite à partir de l'historique)
  - la conformité vaccinale       (simulée, propre à chaque exploitation)
  - le délai d'intervention       (simulé, selon le vétérinaire et le système d'élevage)
  - un effet propre à l'exploitation (aléatoire)

Ces fichiers servent de « vérité cachée » aux générateurs (cheptel, vaccinations, interventions).
Ils ne sont PAS chargés dans l'entrepôt : le ML devra retrouver leur influence à partir des données visibles.

Lancer depuis la racine du dépôt :  python generators/02_pilotes.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RACINE = Path(__file__).resolve().parents[1]


def thi(t, hr):
    return (1.8 * t + 32) - (0.55 - 0.0055 * hr) * (1.8 * t - 26)


def mois_periode(cfg):
    p = cfg["projet"]["periode"]
    return pd.date_range(p["debut"], p["fin"], freq="MS")


# ----------------------------------------------------------------------------
def stress_thermique(cfg, mois):
    m = pd.read_csv(RACINE / cfg["climat"]["fichier_meteo"], parse_dates=["horodatage"])
    m["thi"] = thi(m["temperature_c"], m["humidite_pct"])
    m["jour"] = m["horodatage"].dt.floor("D")
    j = m.groupby(["pcode_departement", "jour"])["thi"].max().reset_index()
    j["mois"] = j["jour"].dt.to_period("M").dt.to_timestamp()
    j["stress"] = j["thi"] > cfg["climat"]["seuil_thi"]
    j["stress_severe"] = j["thi"] > cfg["climat"]["seuil_thi_severe"]
    r = j.groupby(["pcode_departement", "mois"]).agg(
        jours=("stress", "size"), jours_stress=("stress", "sum"),
        jours_stress_severe=("stress_severe", "sum"), thi_max_moyen=("thi", "mean")).reset_index()
    r["part_jours_stress"] = r["jours_stress"] / r["jours"]
    return r[r["mois"].isin(mois)]


def ndvi_mensuel(cfg, lieux, mois):
    n = pd.read_csv(RACINE / cfg["chemins"]["ndvi"], usecols=["date", "PCODE", "vim"], parse_dates=["date"])
    n = n[n["PCODE"].isin(lieux["pcode_departement"])].copy()
    n["mois"] = n["date"].dt.to_period("M").dt.to_timestamp()
    n = n[n["mois"].isin(mois)]
    r = n.groupby(["PCODE", "mois"])["vim"].mean().reset_index()
    r = r.rename(columns={"PCODE": "pcode_departement", "vim": "ndvi"})
    g = r.groupby("pcode_departement")["ndvi"]
    r["ndvi_z"] = ((r["ndvi"] - g.transform("mean")) / g.transform("std").replace(0, np.nan)).fillna(0.0)
    return r


def pression_foyers(cfg, mois, rng):
    """Nouveaux foyers par région et par mois : WAHIS réel puis simulé pour les années non publiées."""
    fichiers = sorted((RACINE / "data" / "raw").glob("wahis_quantitatif*.csv"))
    if not fichiers:
        raise SystemExit("Aucun fichier data/raw/wahis_quantitatif*.csv trouvé.")
    w = pd.concat([pd.read_csv(f, encoding="utf-8-sig", dtype=str) for f in fichiers]).drop_duplicates()
    regions = list(cfg["exploitations"]["repartition_regions"])
    w = w[w["Division administrative"].isin(regions) & w["Espèce"].isna()].copy()  # lignes portant les nouveaux foyers
    w["foyers"] = pd.to_numeric(w["Nouveaux foyers"], errors="coerce").fillna(0)
    w["annee"] = pd.to_numeric(w["Année"])
    w["moitie"] = np.where(w["Semestre"].str.startswith("Jan"), 1, 2)
    reel = w.groupby(["Division administrative", "annee", "moitie"])["foyers"].sum()
    annee_max = int(w["annee"].max())
    moyenne_globale = float(reel.mean())

    lignes = []
    for region in regions:
        for annee in sorted({d.year for d in mois}):
            for moitie in (1, 2):
                if annee <= annee_max:
                    valeur, origine = float(reel.get((region, annee, moitie), 0.0)), "WAHIS"
                else:
                    ref = [reel.get((region, a, moitie)) for a in (annee_max - 1, annee_max)]
                    ref = [v for v in ref if v is not None]
                    if not ref:
                        ref = [v for (r, a, mo), v in reel.items() if r == region] or [moyenne_globale]
                    valeur = float(np.mean(ref) * rng.lognormal(0, 0.30))
                    origine = "SIMULE"
                lignes.append({"region": region, "annee": annee, "moitie": moitie,
                               "foyers_semestre": round(valeur, 1), "origine": origine})
    sem = pd.DataFrame(lignes)
    m = pd.DataFrame({"mois": mois})
    m["annee"], m["moitie"] = m["mois"].dt.year, np.where(m["mois"].dt.month <= 6, 1, 2)
    r = m.merge(sem, on=["annee", "moitie"])
    r["foyers_mois"] = r["foyers_semestre"] / 6
    r["pression_z"] = (r["foyers_mois"] - r["foyers_mois"].mean()) / (r["foyers_mois"].std() or 1.0)
    return r[["region", "mois", "foyers_mois", "pression_z", "origine"]], sem


# ----------------------------------------------------------------------------
def main():
    cfg = yaml.safe_load(open(RACINE / "config" / "params.yaml", encoding="utf-8"))
    sig = cfg["signal"]
    rng = np.random.default_rng(cfg["projet"]["graine"] + 1)
    ref = RACINE / cfg["chemins"]["sortie_referentiel"]
    lieux = pd.read_csv(ref / "ref_lieux.csv")
    expl = pd.read_csv(ref / "ref_exploitations.csv")
    vets = pd.read_csv(ref / "ref_veterinaires.csv")
    mois = mois_periode(cfg)

    stress = stress_thermique(cfg, mois)
    ndvi = ndvi_mensuel(cfg, lieux, mois)
    foyers, sem_foyers = pression_foyers(cfg, mois, rng)

    # --- affectation d'un vétérinaire à chaque exploitation (même département) et traits propres à l'exploitation
    ids_vet = []
    for _, e in expl.iterrows():
        v = vets[vets["pcode_departement"] == e["pcode_departement"]]
        ids_vet.append(v.iloc[rng.integers(len(v))]["id_veterinaire"])
    expl["id_veterinaire"] = ids_vet
    expl = expl.merge(vets[["id_veterinaire", "statut"]].rename(columns={"statut": "statut_veto"}), on="id_veterinaire")
    a, b = cfg["vaccination"]["conformite_beta"]
    expl["conformite_base"] = np.clip(rng.beta(a, b, len(expl)), 0.05, 0.98)
    mediane = expl["statut_veto"].map(cfg["delais_veterinaires"]["mediane_heures"])
    facteur = expl["systeme_elevage"].map(cfg["delais_veterinaires"]["facteur_systeme"])
    expl["delai_base_h"] = mediane * facteur * np.exp(rng.normal(0, 0.25, len(expl)))
    expl["effet_exploitation"] = rng.normal(0, sig["ecart_type_exploitation"], len(expl))

    # --- exploitation x mois
    df = expl.merge(pd.DataFrame({"mois": mois}), how="cross")
    df = df.merge(stress[["pcode_departement", "mois", "jours_stress", "jours_stress_severe", "part_jours_stress", "thi_max_moyen"]],
                  on=["pcode_departement", "mois"], how="left")
    df = df.merge(ndvi[["pcode_departement", "mois", "ndvi", "ndvi_z"]], on=["pcode_departement", "mois"], how="left")
    df = df.merge(foyers, on=["region", "mois"], how="left")
    manquants = df[["part_jours_stress", "ndvi_z", "pression_z"]].isna().sum()
    if manquants.any():
        raise SystemExit(f"Valeurs manquantes dans les facteurs (météo, NDVI ou WAHIS) :\n{manquants}")

    n = len(df)
    mnum = df["mois"].dt.month
    saison = cfg["vaccination"]["amplitude_saison"] * np.sin(2 * np.pi * (mnum - 3) / 12)
    df["conformite_vaccinale"] = np.clip(df["conformite_base"] + saison + rng.normal(0, 0.04, n), 0.05, 0.99)
    df["delai_veto_h"] = np.clip(df["delai_base_h"] * np.exp(rng.normal(0, 0.35, n)), 2, 240)

    risque = (sig["coef_stress_thermique"] * df["part_jours_stress"]
              + sig["coef_non_vaccination"] * (1 - df["conformite_vaccinale"])
              + sig["coef_delai_veto"] * np.log(df["delai_veto_h"] / 24)
              + sig["coef_pression_foyers"] * df["pression_z"]
              - sig["coef_pature"] * df["ndvi_z"]
              + df["effet_exploitation"])
    df["risque_latent"] = risque - risque.mean()
    mult = np.exp(df["risque_latent"])
    mult = mult / mult.mean()  # le multiplicateur moyen vaut 1 : le taux de base de chaque espèce reste interprétable
    df["multiplicateur_mortalite"] = np.clip(mult, sig["multiplicateur_min"], sig["multiplicateur_max"])

    # --- écriture
    sortie = RACINE / sig["sortie_pilotes"]
    sortie.mkdir(parents=True, exist_ok=True)
    cols = ["id_exploitation", "mois", "pcode_departement", "region", "id_veterinaire", "systeme_elevage",
            "jours_stress", "jours_stress_severe", "thi_max_moyen", "ndvi", "ndvi_z", "foyers_mois", "pression_z",
            "origine", "conformite_vaccinale", "delai_veto_h", "effet_exploitation", "risque_latent",
            "multiplicateur_mortalite"]
    sortie_df = df[cols].copy()
    num = sortie_df.select_dtypes("number").columns
    sortie_df[num] = sortie_df[num].round(4)
    sortie_df.to_csv(sortie / "pilotes_exploitation_mois.csv", index=False, encoding="utf-8")
    expl[["id_exploitation", "id_veterinaire", "statut_veto", "conformite_base", "delai_base_h"]].round(4).to_csv(
        sortie / "affectation_veterinaire.csv", index=False, encoding="utf-8")
    sem_foyers.to_csv(sortie / "pression_foyers_semestre.csv", index=False, encoding="utf-8")

    # --- contrôles
    print(f"=== {len(df)} lignes ({expl['id_exploitation'].nunique()} exploitations x {len(mois)} mois) ===")
    print("\nFoyers WAHIS par semestre et par région (réel puis simulé) :")
    print(sem_foyers.pivot_table(index=["annee", "moitie"], columns="region", values="foyers_semestre").round(1).to_string())
    print("\nOrigine par année :", sem_foyers.groupby("annee")["origine"].first().to_dict())
    print("\nMoyennes par région :")
    print(df.groupby("region")[["part_jours_stress", "ndvi", "conformite_vaccinale", "delai_veto_h",
                                "pression_z", "multiplicateur_mortalite"]].mean().round(2).to_string())
    print("\nMultiplicateur moyen par mois (saisonnalité) :")
    print(df.groupby(df["mois"].dt.month)["multiplicateur_mortalite"].mean().round(2).to_string())
    print("\nMultiplicateur : moyenne %.2f ; minimum %.2f ; maximum %.2f ; 95e centile %.2f" % (
        df["multiplicateur_mortalite"].mean(), df["multiplicateur_mortalite"].min(),
        df["multiplicateur_mortalite"].max(), df["multiplicateur_mortalite"].quantile(0.95)))
    print("\nCorrélation du risque avec chaque facteur :")
    for c in ["part_jours_stress", "conformite_vaccinale", "delai_veto_h", "pression_z", "ndvi_z"]:
        print(f"  {c:22s} {df['risque_latent'].corr(df[c]):+.2f}")
    print("\nÉcrit dans", sortie.relative_to(RACINE))


if __name__ == "__main__":
    main()
