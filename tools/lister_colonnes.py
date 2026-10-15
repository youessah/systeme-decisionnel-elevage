"""Liste les colonnes réelles de toutes les sources générées (CSV, JSON, Excel, XML).

Sert à écrire le staging et le dictionnaire de données sans deviner les noms de champs.
Sortie : docs/colonnes_sources.txt (à m'envoyer).

Lancer depuis la racine du dépôt :  python tools/lister_colonnes.py
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
DATA = RACINE / "data"
SORTIE = RACINE / "docs" / "colonnes_sources.txt"
vus = set()  # un seul exemple par motif de nom (ex. gps_2025_01.json ... gps_2025_12.json)


def motif(p: Path) -> str:
    return "".join(c for c in p.stem if not c.isdigit()).strip("_-") + p.suffix


def cles_json(obj, niveau=0):
    """Retourne les clés du premier enregistrement d'un JSON (liste ou dictionnaire imbriqué)."""
    if isinstance(obj, list) and obj:
        return cles_json(obj[0], niveau)
    if isinstance(obj, dict):
        if niveau < 2:
            for k, v in obj.items():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    return [f"{k}[] -> {sorted(v[0].keys())}"] + [x for x in obj if x != k]
        return list(obj.keys())
    return [type(obj).__name__]


def main():
    lignes = []
    for p in sorted(DATA.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in {".csv", ".json", ".xlsx", ".xml"}:
            continue
        m = (p.parent.name, motif(p))
        if m in vus:
            continue
        vus.add(m)
        rel = p.relative_to(RACINE)
        try:
            if p.suffix.lower() == ".csv":
                df = pd.read_csv(p, nrows=3)
                lignes.append(f"{rel}\n    colonnes : {list(df.columns)}\n    types    : {dict(df.dtypes.astype(str))}")
            elif p.suffix.lower() == ".xlsx":
                for feuille, df in pd.read_excel(p, sheet_name=None, nrows=3).items():
                    lignes.append(f"{rel} [feuille {feuille}]\n    colonnes : {list(df.columns)}")
            elif p.suffix.lower() == ".json":
                with open(p, encoding="utf-8") as f:
                    lignes.append(f"{rel}\n    structure : {cles_json(json.load(f))}")
            elif p.suffix.lower() == ".xml":
                racine = ET.parse(p).getroot()
                lignes.append(f"{rel}\n    racine : {racine.tag}")
                for enfant in racine:
                    sous = enfant[0] if len(enfant) else None
                    if sous is not None:
                        lignes.append(f"    <{enfant.tag}> contient <{sous.tag}> attributs={list(sous.attrib)} "
                                      f"balises={[c.tag for c in sous]}")
        except Exception as e:  # un fichier illisible ne doit pas bloquer l'inventaire
            lignes.append(f"{rel}\n    ERREUR de lecture : {e}")
    SORTIE.parent.mkdir(exist_ok=True)
    SORTIE.write_text("\n".join(lignes), encoding="utf-8")
    print(f"{len(lignes)} entrées écrites dans {SORTIE.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
