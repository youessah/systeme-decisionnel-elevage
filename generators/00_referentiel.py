"""Génère le référentiel commun du projet 11 (l'« annuaire » partagé par toutes les sources).

Entrées  : config/params.yaml, data/raw/cmr_admin_codes.xlsx, data/raw/ndvi_cmr_full.csv
Sorties  : data/generated/referentiel/*.csv

Chaque source générée (cheptel, vaccinations, ventes, GPS...) réutilisera ces identifiants,
ce qui permettra les jointures dans l'entrepôt.
Lancer depuis la racine du dépôt :  python generators/00_referentiel.py
"""
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RACINE = Path(__file__).resolve().parents[1]

# ----------------------------------------------------------------------------
# Données de référence fixes (hypothèses de simulation, à documenter)
# ----------------------------------------------------------------------------
ESPECES = [
    # code, espèce, groupe, production principale
    ("BOV", "Bovins", "Ruminants", "Viande et lait"),
    ("OVI", "Ovins", "Ruminants", "Viande"),
    ("CAP", "Caprins", "Ruminants", "Viande et lait"),
    ("VOL", "Volailles", "Volailles", "Chair et oeufs"),
]
RACES = {
    "Bovins": ["Goudali", "Mbororo", "Wakwa"],
    "Ovins": ["Peul", "Djallonké"],
    "Caprins": ["Naine de Guinée", "Sahélienne", "Kirdi"],
    "Volailles": ["Poule locale", "Poulet de chair", "Pondeuse"],
}
# Maladies observées dans l'export WAHIS (mot-clé = fragment du nom brut, pour normaliser les graphies)
MALADIES = [
    # code, nom, sigle, catégorie, espèces, mot-clé WAHIS
    ("FA", "Fièvre aphteuse", "FA", "Virale", "Bovins;Ovins;Caprins", "aphteuse"),
    ("PPCB", "Péripneumonie contagieuse bovine", "PPCB", "Bactérienne", "Bovins", "Mycoplasma mycoides"),
    ("PPR", "Peste des petits ruminants", "PPR", "Virale", "Ovins;Caprins", "petits ruminants"),
    ("DNC", "Dermatose nodulaire contagieuse", "DNC", "Virale", "Bovins", "nodulaire"),
    ("TRYP", "Trypanosomose animale", "TRYP", "Parasitaire", "Bovins;Ovins;Caprins", "Trypanosoma"),
    ("BRU", "Brucellose bovine", "BRU", "Bactérienne", "Bovins", "Brucella abortus"),
    ("NEW", "Maladie de Newcastle", "NEW", "Virale", "Volailles", "Newcastle"),
    ("BIA", "Bronchite infectieuse aviaire", "BIA", "Virale", "Volailles", "Bronchite"),
    ("IAHP", "Influenza aviaire hautement pathogène", "IAHP", "Virale", "Volailles", "Influenza aviaire"),
]
# Vaccins simulés (intervalle de rappel = hypothèse de simulation, pas un protocole vétérinaire)
VACCINS = [
    # code, nom, maladie, espèces, rappel en jours (None = dose unique)
    ("V_FA", "Vaccin anti-aphteux", "FA", "Bovins;Ovins;Caprins", 180),
    ("V_PPCB", "Vaccin anti-péripneumonie", "PPCB", "Bovins", 365),
    ("V_PPR", "Vaccin anti-PPR", "PPR", "Ovins;Caprins", 365),
    ("V_DNC", "Vaccin anti-dermatose nodulaire", "DNC", "Bovins", 365),
    ("V_BRU", "Vaccin anti-brucellique", "BRU", "Bovins", None),
    ("V_NEW", "Vaccin anti-Newcastle", "NEW", "Volailles", 90),
    ("V_BIA", "Vaccin anti-bronchite infectieuse", "BIA", "Volailles", 60),
]
DESTINATIONS = [
    # nom, catégorie
    ("Marché local du département", "local"),
    ("Yaoundé", "autre région"),
    ("Douala", "autre région"),
    ("Nigeria", "export"),
    ("Tchad", "export"),
    ("Gabon", "export"),
    ("Guinée équatoriale", "export"),
]
# Noms fictifs, par région (toute ressemblance avec des personnes réelles est fortuite)
NOMS = {
    "Adamaoua": {
        "prenoms": ["Hamadou", "Ibrahim", "Aminatou", "Abdoulaye", "Oumarou", "Fadimatou", "Yaya", "Hadjara", "Moussa", "Aïssatou", "Bouba", "Djibril"],
        "noms": ["Bello", "Abba", "Adamou", "Yerima", "Sanda", "Hayatou", "Boubakari", "Oumarou", "Mohamadou", "Garga"],
    },
    "Extrême-Nord": {
        "prenoms": ["Hamidou", "Zakari", "Ousmanou", "Haoua", "Hadja", "Mama", "Ali", "Bouba", "Djaouro", "Salomon", "Abakar", "Mahamat"],
        "noms": ["Bakary", "Mamoudou", "Gadji", "Mouhaman", "Abakar", "Hamidou", "Bouba", "Zra", "Ousmanou", "Kolyang"],
    },
    "Ouest": {
        "prenoms": ["Paul", "Marie", "Pierre", "Christelle", "Emmanuel", "Brice", "Rose", "Alain", "Nadège", "Joseph", "Sandrine", "Hervé"],
        "noms": ["Fotso", "Kamga", "Tchoumi", "Kenfack", "Njoya", "Talla", "Nana", "Djoumessi", "Tagne", "Wouapi", "Tchinda"],
    },
}


def norm(texte):
    """Minuscules, sans accents, tirets pour les espaces : sert à comparer les noms."""
    t = unicodedata.normalize("NFKD", str(texte)).encode("ascii", "ignore").decode()
    return t.lower().replace(" ", "-").strip()


def nom_complet(rng, region):
    p, n = NOMS[region]["prenoms"], NOMS[region]["noms"]
    return rng.choice(p), rng.choice(n)


def tirage(rng, probas):
    """Tire une clé d'un dictionnaire {clé: probabilité} (les probabilités sont renormalisées)."""
    cles = list(probas)
    p = np.array([probas[c] for c in cles], dtype=float)
    return cles[rng.choice(len(cles), p=p / p.sum())]


# ----------------------------------------------------------------------------
# Construction des tables
# ----------------------------------------------------------------------------
def construire_lieux(cfg):
    adm2 = pd.read_excel(RACINE / cfg["chemins"]["admin_codes"], sheet_name="cmr_admin2")
    nom = adm2[["adm2_name1", "adm2_name", "adm2_name2"]].bfill(axis=1).iloc[:, 0]
    adm2["cle"] = nom.map(norm)
    adm2["departement_officiel"] = nom

    regions = cfg["geographie"]["regions"]
    lignes, manquants = [], []
    for i, d in enumerate(cfg["geographie"]["departements"], start=1):
        trouve = adm2[adm2["cle"] == norm(d["nom"])]
        if trouve.empty:
            manquants.append(d["nom"])
            continue
        r = trouve.iloc[0]
        pcode_region = str(r["adm1_pcode"])
        if pcode_region not in regions:
            raise SystemExit(f"Région {pcode_region} absente de params.yaml (departement {d['nom']}).")
        lignes.append({
            "id_lieu": f"L{i:02d}",
            "departement": d["nom"],
            "pcode_departement": r["adm2_pcode"],
            "region": regions[pcode_region],
            "pcode_region": pcode_region,
            "chef_lieu": d["chef_lieu"],
            "latitude": round(float(r["center_lat"]), 5),
            "longitude": round(float(r["center_lon"]), 5),
        })
    if manquants:
        raise SystemExit(f"Départements introuvables dans la table COD-AB : {manquants}")
    return pd.DataFrame(lignes)


def construire_exploitations(cfg, lieux, rng):
    ex = cfg["exploitations"]
    esp_noms = [e[1] for e in ESPECES]
    d_min = pd.Timestamp(ex["date_creation_min"])
    n_jours = (pd.Timestamp(ex["date_creation_max"]) - d_min).days
    exploitations, effectifs = [], []
    compteur = 0
    for region, n in ex["repartition_regions"].items():
        prof = ex["profils"][region]
        deps = lieux[lieux["region"] == region].reset_index(drop=True)
        for _ in range(n):
            compteur += 1
            id_exp = f"EXP-{compteur:04d}"
            dep = deps.iloc[rng.integers(len(deps))]
            principale = tirage(rng, prof["principale"])
            detenues = [principale] + [
                e for e in esp_noms if e != principale and rng.random() < prof["secondaire"][e]
            ]
            # effectif initial par espèce (log-normale bornée)
            eff_init = {}
            for e in detenues:
                med, sigma, vmin, vmax = prof["effectif"][e]
                eff_init[e] = int(np.clip(round(rng.lognormal(np.log(med), sigma)), vmin, vmax))
            s1, s2 = ex["seuils_taille"][principale]
            eff_p = eff_init[principale]
            taille = "Petite" if eff_p < s1 else ("Grande" if eff_p > s2 else "Moyenne")
            prenom, nom = nom_complet(rng, region)
            jit = cfg["geographie"]["jitter_degres"]
            exploitations.append({
                "id_exploitation": id_exp,
                "nom_exploitation": f"Élevage {nom} ({dep['departement']})",
                "proprietaire": f"{prenom} {nom}",
                "pcode_departement": dep["pcode_departement"],
                "departement": dep["departement"],
                "region": region,
                "espece_principale": principale,
                "systeme_elevage": tirage(rng, prof["systeme"]),
                "taille": taille,
                "date_creation": (d_min + pd.Timedelta(days=int(rng.integers(n_jours)))).date().isoformat(),
                "latitude": round(float(dep["latitude"] + rng.normal(0, jit)), 5),
                "longitude": round(float(dep["longitude"] + rng.normal(0, jit)), 5),
                "statut": "Actif",
            })
            for e, eff in eff_init.items():
                effectifs.append({"id_exploitation": id_exp, "espece": e, "effectif_initial": eff})
    return pd.DataFrame(exploitations), pd.DataFrame(effectifs)


def construire_veterinaires(cfg, lieux, rng):
    v = cfg["veterinaires"]
    specialites = ["Grands ruminants", "Petits ruminants", "Volailles", "Mixte"]
    lignes, compteur = [], 0
    for _, dep in lieux.iterrows():
        for _ in range(v["par_departement"]):
            compteur += 1
            prenom, nom = nom_complet(rng, dep["region"])
            lignes.append({
                "id_veterinaire": f"VET-{compteur:03d}",
                "nom": nom,
                "prenom": prenom,
                "statut": "Public" if rng.random() < v["part_public"] else "Privé",
                "pcode_departement": dep["pcode_departement"],
                "departement": dep["departement"],
                "specialite": rng.choice(specialites),
                "date_prise_poste": (pd.Timestamp("2005-01-01") + pd.Timedelta(days=int(rng.integers(0, 6200)))).date().isoformat(),
            })
    return pd.DataFrame(lignes)


def construire_marches(lieux):
    return pd.DataFrame([{
        "id_marche": f"MAR-{i:02d}",
        "nom_marche": f"Marché à bétail de {r['chef_lieu']}",
        "ville": r["chef_lieu"],
        "pcode_departement": r["pcode_departement"],
        "departement": r["departement"],
        "region": r["region"],
        "latitude": r["latitude"],
        "longitude": r["longitude"],
    } for i, (_, r) in enumerate(lieux.iterrows(), start=1)])


def verifier(cfg, lieux, exploitations, effectifs, veterinaires):
    print("\n=== CONTRÔLES ===")
    for nom, df, cle in [("lieux", lieux, "id_lieu"), ("exploitations", exploitations, "id_exploitation"),
                         ("vétérinaires", veterinaires, "id_veterinaire")]:
        assert df[cle].is_unique, f"Identifiants en double dans {nom}"
    print("Identifiants uniques : OK")
    print("\nExploitations par région et département :")
    print(exploitations.groupby(["region", "departement"]).size().to_string())
    print("\nEspèce principale par région :")
    print(pd.crosstab(exploitations["region"], exploitations["espece_principale"]).to_string())
    print("\nSystème d'élevage par région :")
    print(pd.crosstab(exploitations["region"], exploitations["systeme_elevage"]).to_string())
    print("\nEffectif initial total par région et espèce :")
    t = effectifs.merge(exploitations[["id_exploitation", "region"]], on="id_exploitation")
    print(t.pivot_table(index="region", columns="espece", values="effectif_initial", aggfunc="sum").to_string())

    # La jointure avec le NDVI doit donner 872 décades par département
    chemin = RACINE / cfg["chemins"]["ndvi"]
    if chemin.exists():
        ndvi = pd.read_csv(chemin, usecols=["PCODE", "date"])
        n = ndvi[ndvi["PCODE"].isin(lieux["pcode_departement"])].groupby("PCODE").size()
        print("\nLignes NDVI par département (872 attendues) :")
        print(lieux[["departement", "pcode_departement"]].assign(
            lignes_ndvi=lieux["pcode_departement"].map(n).fillna(0).astype(int)).to_string(index=False))
    else:
        print("\n(fichier NDVI absent : contrôle ignoré)")


def main():
    with open(RACINE / "config" / "params.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    rng = np.random.default_rng(cfg["projet"]["graine"])
    sortie = RACINE / cfg["chemins"]["sortie_referentiel"]
    sortie.mkdir(parents=True, exist_ok=True)

    lieux = construire_lieux(cfg)
    exploitations, effectifs = construire_exploitations(cfg, lieux, rng)
    veterinaires = construire_veterinaires(cfg, lieux, rng)
    marches = construire_marches(lieux)

    especes = pd.DataFrame(ESPECES, columns=["code_espece", "espece", "groupe", "production_principale"])
    races = pd.DataFrame([(f"{especes.loc[especes.espece == e, 'code_espece'].iloc[0]}-{i:02d}", e, r)
                          for e, rs in RACES.items() for i, r in enumerate(rs, start=1)],
                         columns=["code_race", "espece", "race"])
    maladies = pd.DataFrame(MALADIES, columns=["code_maladie", "maladie", "sigle", "categorie",
                                               "especes_concernees", "mot_cle_wahis"])
    vaccins = pd.DataFrame(VACCINS, columns=["code_vaccin", "vaccin", "code_maladie",
                                             "especes_cibles", "rappel_jours"])
    destinations = pd.DataFrame(DESTINATIONS, columns=["destination", "categorie"])
    destinations.insert(0, "id_destination", [f"DST-{i:02d}" for i in range(1, len(destinations) + 1)])

    tables = {
        "ref_lieux": lieux, "ref_exploitations": exploitations, "ref_exploitation_especes": effectifs,
        "ref_especes": especes, "ref_races": races, "ref_maladies": maladies, "ref_vaccins": vaccins,
        "ref_veterinaires": veterinaires, "ref_marches": marches, "ref_destinations": destinations,
    }
    print("=== FICHIERS ÉCRITS dans", sortie.relative_to(RACINE), "===")
    for nom, df in tables.items():
        df.to_csv(sortie / f"{nom}.csv", index=False, encoding="utf-8-sig")
        print(f"{nom:28s} {len(df):5d} lignes")

    print("\nLieux retenus :")
    print(lieux.to_string(index=False))
    verifier(cfg, lieux, exploitations, effectifs, veterinaires)


if __name__ == "__main__":
    main()
