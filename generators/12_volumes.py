"""Bilan des volumes : nombre de lignes de chacune des 15 sources, format et total.

Preuve chiffrée pour le dossier : au moins 15 sources, au moins 4 formats, au moins 1 million de lignes.
Le résultat est enregistré dans docs/volumes_sources.csv.

Lancer depuis la racine du dépôt :  python generators/12_volumes.py
"""
import json
import xml.etree.ElementTree as ET

import pandas as pd

from common import RACINE, charger_cfg


def lignes_csv(chemin):
    if not chemin.exists():
        return 0
    with open(chemin, "rb") as f:
        return max(sum(1 for _ in f) - 1, 0)


def lignes_json(chemin):
    if not chemin.exists():
        return 0
    d = json.loads(chemin.read_text(encoding="utf-8"))
    return len(d) if isinstance(d, list) else 0


def main():
    cfg = charger_cfg()
    raw, gen = RACINE / "data" / "raw", RACINE / "data" / "generated"
    lig = []

    def ajoute(n, nom, fmt, origine, nb):
        lig.append((n, nom, fmt, origine, int(nb)))

    ajoute(1, "FAOSTAT élevage", "CSV", "Public", lignes_csv(raw / "faostat_elevage_cameroun.csv"))
    ajoute(2, "FAOSTAT prix producteurs", "CSV", "Public", lignes_csv(raw / "faostat_prix_cameroun.csv"))
    wahis = [pd.read_csv(f, encoding="utf-8-sig", dtype=str) for f in sorted(raw.glob("wahis_quantitatif*.csv"))]
    ajoute(3, "WAHIS foyers de maladies", "CSV", "Public", len(pd.concat(wahis).drop_duplicates()) if wahis else 0)
    ch = RACINE / cfg["cheptel"]["sortie"]
    ajoute(4, "Cheptel par exploitation", "PostgreSQL", "Généré",
           sum(lignes_csv(ch / f"{t}.csv") for t in ("exploitation", "animal", "lot_volaille", "suivi_lot_semaine")))
    va = RACINE / cfg["vaccinations"]["sortie"]
    ajoute(5, "Vaccinations", "MySQL", "Généré", lignes_csv(va / "vaccination.csv") + lignes_csv(va / "vaccin.csv"))
    mo = RACINE / cfg["mouvements"]["sortie"]
    ajoute(6, "Mouvements et transhumance", "JSON", "Généré", sum(lignes_json(f) for f in mo.glob("mouvements_*.json")))
    ajoute(7, "Abattages", "CSV", "Généré", lignes_csv(RACINE / cfg["abattages"]["sortie"] / "abattage.csv"))
    xl = RACINE / cfg["production"]["sortie"] / "production_lait_oeufs.xlsx"
    n_xl = 0
    if xl.exists():
        x = pd.ExcelFile(xl)
        n_xl = sum(len(pd.read_excel(x, s)) for s in x.sheet_names)
    ajoute(8, "Production de lait et d'œufs", "Excel", "Généré", n_xl)
    ajoute(9, "Alimentation et fourrage", "CSV", "Généré", lignes_csv(RACINE / cfg["alimentation"]["sortie"] / "alimentation.csv"))
    ma = RACINE / cfg["marche"]["sortie"]
    ajoute(10, "Prix du marché à bétail", "CSV", "Généré", lignes_csv(ma / "vente.csv") + lignes_csv(ma / "releve_prix.csv"))
    ajoute(11, "Pâturages (NDVI)", "CSV", "Public", lignes_csv(raw / "ndvi_cmr_full.csv"))
    nb_meteo = 0
    for f in (raw / "meteo").glob("*.json"):
        nb_meteo += len(json.loads(f.read_text(encoding="utf-8"))["hourly"]["time"])
    ajoute(12, "Météo (Open-Meteo)", "API JSON", "Public", nb_meteo)
    xml = RACINE / cfg["interventions"]["sortie"] / "veterinaires_interventions.xml"
    n_xml = 0
    if xml.exists():
        r = ET.parse(xml).getroot()
        n_xml = len(r.findall("./veterinaires/veterinaire")) + len(r.findall("./interventions/intervention"))
    ajoute(13, "Vétérinaires et interventions", "XML", "Généré", n_xml)
    gp = RACINE / cfg["gps"]["sortie"]
    ajoute(14, "Colliers GPS", "JSON", "Généré", sum(lignes_json(f) for f in gp.glob("gps_*.json")))
    ajoute(15, "Taux de change", "API JSON", "Public", lignes_csv(raw / "faostat_change_cameroun.csv"))

    df = pd.DataFrame(lig, columns=["n", "source", "format", "origine", "lignes"])
    total = int(df["lignes"].sum())
    pd.set_option("display.width", 200)
    print(df.to_string(index=False, formatters={"lignes": "{:,}".format}))
    print(f"\nTOTAL : {total:,} lignes".replace(",", " "))
    print(f"Sources non vides : {(df['lignes'] > 0).sum()} sur 15 | formats distincts : {df.loc[df['lignes'] > 0, 'format'].nunique()}")
    print("Exigences : 15 sources %s | 4 formats %s | 1 000 000 de lignes %s" % (
        "OK" if (df["lignes"] > 0).sum() >= 15 else "MANQUE",
        "OK" if df.loc[df["lignes"] > 0, "format"].nunique() >= 4 else "MANQUE",
        "OK" if total >= 1_000_000 else f"MANQUE ({1_000_000 - total:,})".replace(",", " ")))
    out = RACINE / "docs"
    out.mkdir(exist_ok=True)
    df.to_csv(out / "volumes_sources.csv", index=False, encoding="utf-8")
    print("Écrit : docs/volumes_sources.csv")


if __name__ == "__main__":
    main()
