"""Vérification globale des 15 sources avant l'ETL.

1. Intégrité référentielle entre sources : chaque identifiant (exploitation, animal, lot, vétérinaire, marché,
   transaction) utilisé dans une source existe-t-il dans la source de référence ?
2. Cohérence métier entre sources (ventes, abattages, mouvements, GPS, interventions).
3. Défauts de qualité : nombre observé par règle, comparé au nombre injecté (étiquettes de vérité).
   Un défaut observé en moins que prévu signifie que la règle ne le détecte pas ; en plus, qu'il existe des
   anomalies non étiquetées.

Le rapport est aussi enregistré dans docs/verification_sources.txt.
Lancer depuis la racine du dépôt :  python generators/14_verif_sources.py
"""
import json
import sys
import xml.etree.ElementTree as ET

import pandas as pd

from common import RACINE, charger_cfg, dossier_ref, dossier_verite

LIGNES = []


def sortie(texte=""):
    print(texte)
    LIGNES.append(texte)


def json_dossier(dossier, motif):
    morceaux = [pd.DataFrame(json.loads(f.read_text(encoding="utf-8"))) for f in sorted(dossier.glob(motif))]
    return pd.concat(morceaux, ignore_index=True) if morceaux else pd.DataFrame()


def main():
    cfg = charger_cfg()
    ref, ver = dossier_ref(cfg), dossier_verite(cfg)
    fin_periode = pd.Timestamp(cfg["projet"]["periode"]["fin"])
    ch, va = RACINE / cfg["cheptel"]["sortie"], RACINE / cfg["vaccinations"]["sortie"]

    expl = pd.read_csv(ch / "exploitation.csv")
    ani = pd.read_csv(ch / "animal.csv", parse_dates=["date_naissance", "date_entree", "date_sortie"])
    lot = pd.read_csv(ch / "lot_volaille.csv")
    suivi = pd.read_csv(ch / "suivi_lot_semaine.csv")
    vac = pd.read_csv(va / "vaccination.csv", parse_dates=["date_vaccination"])
    ab = pd.read_csv(RACINE / cfg["abattages"]["sortie"] / "abattage.csv", parse_dates=["date_abattage"])
    vente = pd.read_csv(RACINE / cfg["marche"]["sortie"] / "vente.csv", parse_dates=["date_transaction"])
    ali = pd.read_csv(RACINE / cfg["alimentation"]["sortie"] / "alimentation.csv")
    prod = pd.concat(pd.read_excel(RACINE / cfg["production"]["sortie"] / "production_lait_oeufs.xlsx", sheet_name=None).values(), ignore_index=True)
    mouv = json_dossier(RACINE / cfg["mouvements"]["sortie"], "mouvements_*.json")
    gps = json_dossier(RACINE / cfg["gps"]["sortie"], "gps_*.json")
    racine_xml = ET.parse(RACINE / cfg["interventions"]["sortie"] / "veterinaires_interventions.xml").getroot()
    vets = pd.DataFrame([{"id": v.get("id"), "pcode": v.find("departement").get("pcode")} for v in racine_xml.findall("./veterinaires/veterinaire")])
    inter = pd.DataFrame([{"id": i.get("id"), "exploitation": i.findtext("exploitation"), "veterinaire": i.findtext("veterinaire"),
                           "signalement": i.findtext("date_signalement"), "intervention": i.findtext("date_intervention"),
                           "cout": i.findtext("cout_medicaments"), "compte_rendu": i.findtext("compte_rendu")}
                          for i in racine_xml.findall("./interventions/intervention")])
    inter["signalement"] = pd.to_datetime(inter["signalement"])
    inter["intervention"] = pd.to_datetime(inter["intervention"])
    marches = pd.read_csv(ref / "ref_marches.csv")
    lieux = pd.read_csv(ref / "ref_lieux.csv")

    def etiquettes(nom):
        f = ver / nom
        return pd.read_csv(f)["type_defaut"].value_counts().to_dict() if f.exists() else {}

    et = {}
    for n in ("defauts_cheptel.csv", "defauts_vaccinations.csv", "defauts_abattages.csv", "defauts_marche.csv",
              "defauts_alimentation.csv", "defauts_production.csv", "defauts_mouvements.csv", "defauts_veterinaires.csv"):
        et.update({n.split("_")[1].split(".")[0] + ":" + k: v for k, v in etiquettes(n).items()})

    # ------------------------------------------------------------------ 1. intégrité référentielle
    sortie("=" * 72)
    sortie("1. INTÉGRITÉ RÉFÉRENTIELLE (valeurs utilisées absentes de la source de référence)")
    sortie("=" * 72)
    controles = [
        ("animal.id_exploitation", ani["id_exploitation"], expl["id_exploitation"]),
        ("lot_volaille.id_exploitation", lot["id_exploitation"], expl["id_exploitation"]),
        ("suivi_lot_semaine.id_lot", suivi["id_lot"], lot["id_lot"]),
        ("vaccination.id_exploitation", vac["id_exploitation"], expl["id_exploitation"]),
        ("vaccination.id_animal", vac["id_animal"], ani["id_animal"]),
        ("vaccination.id_lot", vac["id_lot"], lot["id_lot"]),
        ("vaccination.id_veterinaire", vac["id_veterinaire"], vets["id"]),
        ("abattage.id_exploitation", ab["id_exploitation"], expl["id_exploitation"]),
        ("abattage.id_animal", ab["id_animal"], ani["id_animal"]),
        ("abattage.id_lot", ab["id_lot"], lot["id_lot"]),
        ("vente.id_exploitation", vente["id_exploitation"], expl["id_exploitation"]),
        ("vente.id_animal", vente["id_animal"], ani["id_animal"]),
        ("vente.id_lot", vente["id_lot"], lot["id_lot"]),
        ("vente.id_marche", vente["id_marche"], marches["id_marche"]),
        ("alimentation.id_exploitation", ali["id_exploitation"], expl["id_exploitation"]),
        ("alimentation.id_lot", ali["id_lot"], lot["id_lot"]),
        ("production.id_exploitation", prod["id_exploitation"], expl["id_exploitation"]),
        ("mouvement.id_exploitation", mouv["id_exploitation"], expl["id_exploitation"]),
        ("mouvement.id_transaction", mouv["id_transaction"], vente["id_transaction"]),
        ("gps.id_exploitation", gps["id_exploitation"], expl["id_exploitation"]),
        ("gps.id_animal", gps["id_animal"], ani["id_animal"]),
        ("intervention.exploitation", inter["exploitation"], expl["id_exploitation"]),
        ("intervention.veterinaire", inter["veterinaire"], vets["id"]),
        ("exploitation.pcode_departement", expl["pcode_departement"], lieux["pcode_departement"]),
        ("veterinaire.departement", vets["pcode"], lieux["pcode_departement"]),
    ]
    anomalies = 0
    for nom, valeurs, reference in controles:
        v = valeurs.dropna()
        manque = int((~v.isin(set(reference))).sum())
        anomalies += manque > 0
        sortie(f"  {'OK ' if manque == 0 else 'KO '} {nom:34s} {len(v):>9,} valeurs, {manque} absente(s)".replace(",", " "))

    # ------------------------------------------------------------------ 2. cohérence métier
    sortie("\n" + "=" * 72)
    sortie("2. COHÉRENCE MÉTIER ENTRE SOURCES")
    sortie("=" * 72)
    ids_vendus = set(ani.loc[ani["motif_sortie"] == "vente", "id_animal"])
    ids_abattus = set(ani.loc[ani["motif_sortie"] == "abattage", "id_animal"])
    sortie(f"  Animaux « vendus » (cheptel) absents du marché : {len(ids_vendus - set(vente['id_animal'].dropna()))}")
    sortie(f"  Animaux du marché non « vendus » dans le cheptel : {len(set(vente['id_animal'].dropna()) - ids_vendus)}")
    sortie(f"  Animaux « abattus » (cheptel) absents des abattages : {len(ids_abattus - set(ab['id_animal'].dropna()))}")
    mouv_u = mouv[~mouv.drop(columns=["id_mouvement"]).astype(str).duplicated()]  # sans les doublons injectés
    vente_u = vente.drop_duplicates(subset=[c for c in vente.columns if c not in ("id_transaction", "updated_at")])
    sortie(f"  Mouvements de vente / transactions du marché (hors doublons) : {int((mouv_u['type_mouvement'] == 'vente').sum())} / {len(vente_u)}")
    gps["horodatage"] = pd.to_datetime(gps["horodatage"])
    jour_gps = gps["horodatage"].dt.normalize()
    vraie = pd.read_csv(ver / "animal_propre.csv", parse_dates=["date_sortie"]).set_index("id_animal")["date_sortie"]
    tard_vrai = gps[jour_gps > gps["id_animal"].map(vraie)]
    tard_obs = gps[jour_gps > gps["id_animal"].map(ani.set_index("id_animal")["date_sortie"])]
    alteres = sorted(set(tard_obs["id_animal"]) - set(tard_vrai["id_animal"]))
    sortie(f"  Positions GPS postérieures à la sortie réelle de l'animal : {len(tard_vrai)} (doit valoir 0)")
    sortie(f"  Positions GPS postérieures à la date de sortie OBSERVÉE : {len(tard_obs)}, "
           f"dont {len(alteres)} animal(aux) dont la date de sortie a été altérée par un défaut injecté {alteres[:5]}")
    sortie(f"  Lots de volailles utilisés par l'alimentation sans suivi hebdomadaire : {len(set(ali['id_lot'].dropna()) - set(suivi['id_lot']))}")

    # ------------------------------------------------------------------ 3. défauts : observés / injectés
    sortie("\n" + "=" * 72)
    sortie("3. DÉFAUTS DE QUALITÉ : observés par règle / injectés (étiquettes)")
    sortie("=" * 72)
    cols_vac = [c for c in vac.columns if c not in ("id_vaccination", "updated_at")]
    cols_vente = [c for c in vente.columns if c not in ("id_transaction", "updated_at")]
    cols_mouv = [c for c in mouv.columns if c != "id_mouvement"]
    cols_int = ["exploitation", "veterinaire", "signalement", "compte_rendu"]
    regles = [
        ("animal : date de sortie avant l'entrée", int((ani["date_sortie"] < ani["date_entree"]).sum()), "cheptel:date_sortie_avant_entree"),
        ("animal : sexe manquant", int(ani["sexe"].isna().sum()), "cheptel:sexe_manquant"),
        ("animal : espèce mal écrite", int((~ani["espece"].isin(["Bovins", "Ovins", "Caprins"])).sum()), "cheptel:espece_mal_ecrite"),
        ("vaccination : date dans le futur", int((vac["date_vaccination"] > fin_periode).sum()), "vaccinations:date_future"),
        ("vaccination : vétérinaire manquant", int(vac["id_veterinaire"].isna().sum()), "vaccinations:veterinaire_manquant"),
        ("vaccination : doublons", int(vac.duplicated(subset=cols_vac).sum()), "vaccinations:doublon"),
        ("abattage : poids vif négatif", int((ab["poids_vif_kg"] < 0).sum()), "abattages:poids_negatif"),
        ("abattage : date absente", int(ab["date_abattage"].isna().sum()), "abattages:date_absente"),
        ("marché : prix négatif", int((vente["prix_total"] < 0).sum()), "marche:prix_negatif"),
        ("marché : poids nul", int((vente["poids_total_kg"] == 0).sum()), "marche:poids_nul"),
        ("marché : date dans le futur", int((vente["date_transaction"] > fin_periode).sum()), "marche:date_future"),
        ("marché : doublons", int(vente.duplicated(subset=cols_vente).sum()), "marche:doublon"),
        ("alimentation : quantité négative", int((ali["quantite_kg"] < 0).sum()), "alimentation:quantite_negative"),
        ("alimentation : prix manquant", int(ali["prix_unitaire"].isna().sum()), "alimentation:prix_manquant"),
        ("production Excel : date saisie en texte", int(prod["date"].map(lambda x: isinstance(x, str)).sum()), "production:date_en_texte"),
        ("production Excel : litres en texte (virgule)", int(prod["litres_lait"].map(lambda x: isinstance(x, str)).sum()), "production:decimale_virgule"),
        ("production Excel : litres négatifs", int(pd.to_numeric(prod["litres_lait"], errors="coerce").lt(0).sum()), "production:litres_negatifs"),
        ("mouvement : distance négative", int((mouv["distance_km"] < 0).sum()), "mouvements:distance_negative"),
        ("mouvement : doublons", int(mouv.drop(columns=["id_mouvement"]).astype(str).duplicated().sum()), "mouvements:doublon"),
        ("intervention : date d'intervention absente", int(inter["intervention"].isna().sum()), "veterinaires:date_intervention_absente"),
        ("intervention : intervention avant signalement", int((inter["intervention"] < inter["signalement"]).sum()), "veterinaires:intervention_avant_signalement"),
        ("intervention : compte rendu vide", int(inter["compte_rendu"].fillna("").eq("").sum()), "veterinaires:compte_rendu_vide"),
        ("intervention : doublons", int(inter.duplicated(subset=cols_int).sum()), "veterinaires:doublon"),
    ]
    sortie(f"  {'Règle':48s}{'observé':>9s}{'injecté':>9s}   lecture")
    for nom, obs, cle in regles:
        inj = et.get(cle, 0)
        lecture = "égal" if obs == inj else ("règle plus large : anomalies non étiquetées" if obs > inj else "NON DÉTECTÉ en totalité")
        sortie(f"  {nom:48s}{obs:>9d}{inj:>9d}   {lecture}")

    sortie("\n" + "=" * 72)
    sortie(f"BILAN : {len(controles) - anomalies} contrôles d'intégrité sur {len(controles)} réussis.")
    sortie("Les défauts du paragraphe 3 sont voulus : ton ETL doit les détecter et les écarter (table de rejets).")
    out = RACINE / "docs"
    out.mkdir(exist_ok=True)
    (out / "verification_sources.txt").write_text("\n".join(LIGNES), encoding="utf-8")
    sortie("Rapport enregistré : docs/verification_sources.txt")
    return 1 if anomalies else 0


if __name__ == "__main__":
    sys.exit(main())
