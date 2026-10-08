"""Retrouve les 6 departements du projet dans la table COD-AB et verifie le NDVI."""
import unicodedata
import pandas as pd

CIBLES = {"vina", "mbere", "diamare", "mayo-tsanaga", "mifi", "menoua"}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.lower().replace(" ", "-").strip()


def premier_non_vide(df, colonnes):
    """Retourne, ligne par ligne, la premiere valeur non vide parmi les colonnes."""
    colonnes = [c for c in colonnes if c in df.columns]
    return df[colonnes].bfill(axis=1).iloc[:, 0]


adm2 = pd.read_excel("data/raw/cmr_admin_codes.xlsx", sheet_name="cmr_admin2")
adm2["departement"] = premier_non_vide(adm2, ["adm2_name1", "adm2_name", "adm2_name2"])
adm2["region"] = premier_non_vide(adm2, ["adm1_name1", "adm1_name", "adm1_name2"])
adm2["cle"] = adm2["departement"].map(norm)

sel = adm2[adm2["cle"].isin(CIBLES)].copy()
sel = sel.rename(columns={"adm2_pcode": "pcode_dep", "adm1_pcode": "pcode_region"})

cols = ["departement", "pcode_dep", "region", "pcode_region", "center_lat", "center_lon"]
print(sel[cols].to_string(index=False))
print(f"\n{len(sel)} departement(s) trouve(s) sur 6")
manquants = CIBLES - set(sel["cle"])
if manquants:
    print("A verifier (noms non trouves) :", manquants)
print(f"Departements au total dans la table : {len(adm2)}")

ndvi = pd.read_csv("data/raw/ndvi_cmr_full.csv")
n = ndvi[ndvi["PCODE"].isin(sel["pcode_dep"])]
print("\nNDVI pour ces departements :")
print(n.groupby("PCODE")["date"].agg(["count", "min", "max"]).to_string())

sel[cols].to_csv("data/generated/ref_departements.csv", index=False, encoding="utf-8")
print("\nEcrit : data/generated/ref_departements.csv")
