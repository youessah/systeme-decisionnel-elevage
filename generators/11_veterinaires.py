"""Génère la source 13 : vétérinaires et interventions (un fichier XML).

Les interventions naissent des événements sanitaires du cheptel :
  - A : décès par maladie (un vétérinaire est appelé pour le groupe de décès du mois) ;
  - B : épisodes sans décès, plus fréquents quand le multiplicateur de mortalité est élevé ;
  - C : semaines de forte mortalité dans un lot de volailles.
Le délai entre le signalement et l'intervention provient du facteur caché « délai vétérinaire »
(selon le vétérinaire, public ou privé, et le système d'élevage).

Chaque intervention contient un COMPTE RENDU en texte libre, en français, avec des tournures variées,
des abréviations, des négations (« pas de diarrhée ») et quelques fautes de frappe : c'est la matière du NLP 1
(extraction des symptômes et des maladies). Les vraies réponses sont conservées à part pour évaluer le modèle.

Sorties  data/generated/veterinaires/veterinaires_interventions.xml  (avec défauts volontaires)
         data/generated/pilotes/intervention_propre.csv, gold_comptes_rendus.csv, echantillon_a_verifier.csv,
         defauts_veterinaires.csv

Lancer depuis la racine du dépôt :  python generators/11_veterinaires.py
"""
import re
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

from common import (ESP, RACINE, charger_cfg, dossier_ref, dossier_verite, taux_usd, valeur_mois)

# ----------------------------------------------------------------------------
# Lexique : symptômes canoniques et formulations possibles dans un compte rendu
# ----------------------------------------------------------------------------
SYMPTOMES = {
    "fièvre": ["fièvre", "hyperthermie", "température élevée ({t}°C)", "T° {t}°C", "état fébrile"],
    "salivation": ["salivation abondante", "hypersalivation", "bave filante"],
    "aphtes": ["aphtes buccaux", "vésicules sur la langue", "lésions aphteuses"],
    "boiterie": ["boiteries", "claudication", "animaux qui boitent"],
    "lésions podales": ["lésions entre les onglons", "plaies aux pieds", "lésions podales"],
    "baisse de lait": ["baisse de la production laitière", "chute de la production de lait", "moins de lait"],
    "anorexie": ["anorexie", "refus de s'alimenter", "perte d'appétit"],
    "toux": ["toux", "toux sèche", "quintes de toux"],
    "dyspnée": ["difficultés respiratoires", "dyspnée", "respiration difficile"],
    "jetage": ["jetage nasal", "écoulement nasal", "jetage mucopurulent"],
    "amaigrissement": ["amaigrissement", "perte de poids", "animaux maigres"],
    "diarrhée": ["diarrhée", "selles liquides", "diarrhées profuses"],
    "abattement": ["abattement", "prostration", "animaux abattus"],
    "érosions buccales": ["érosions buccales", "lésions dans la bouche", "ulcères buccaux"],
    "avortement": ["avortements", "femelles qui avortent", "mises bas prématurées"],
    "nodules cutanés": ["nodules cutanés", "nodules sur la peau", "lésions nodulaires"],
    "œdème": ["œdème des membres", "gonflement des pattes", "œdèmes"],
    "anémie": ["anémie", "muqueuses pâles", "pâleur des muqueuses"],
    "ganglions": ["ganglions hypertrophiés", "gonflement des ganglions"],
    "rétention placentaire": ["rétention placentaire", "non-délivrance"],
    "orchite": ["orchite", "testicules enflés"],
    "arthrite": ["arthrite", "articulations gonflées"],
    "torticolis": ["torticolis", "cou tordu"],
    "paralysie": ["paralysie des pattes", "paralysie", "incoordination motrice"],
    "baisse de ponte": ["baisse de ponte", "chute de ponte", "ponte en diminution"],
    "éternuements": ["éternuements", "oiseaux qui éternuent"],
    "râles": ["râles trachéaux", "bruits respiratoires"],
    "mortalité brutale": ["mortalité brutale", "morts subites", "forte mortalité"],
    "œdème de la tête": ["œdème de la tête", "tête gonflée"],
    "crête cyanosée": ["crête cyanosée", "crête bleutée"],
    "plumes ébouriffées": ["plumes ébouriffées", "plumage hérissé"],
}
SYMPT_MALADIE = {
    "FA": ["fièvre", "salivation", "aphtes", "boiterie", "lésions podales", "baisse de lait", "anorexie"],
    "PPCB": ["toux", "dyspnée", "jetage", "fièvre", "amaigrissement", "anorexie"],
    "PPR": ["fièvre", "diarrhée", "jetage", "érosions buccales", "toux", "avortement", "abattement"],
    "DNC": ["nodules cutanés", "fièvre", "ganglions", "œdème", "baisse de lait"],
    "TRYP": ["anémie", "amaigrissement", "fièvre", "œdème", "abattement", "avortement"],
    "BRU": ["avortement", "rétention placentaire", "orchite", "arthrite"],
    "NEW": ["diarrhée", "torticolis", "paralysie", "dyspnée", "baisse de ponte", "mortalité brutale"],
    "BIA": ["éternuements", "râles", "jetage", "baisse de ponte"],
    "IAHP": ["mortalité brutale", "œdème de la tête", "crête cyanosée", "diarrhée", "baisse de ponte", "plumes ébouriffées"],
    None: ["abattement", "anorexie", "amaigrissement", "diarrhée", "toux", "fièvre"],
}
MALADIES_ESP = {
    "Bovins": [("FA", 0.28), ("PPCB", 0.22), ("DNC", 0.10), ("TRYP", 0.20), ("BRU", 0.08), (None, 0.12)],
    "Ovins": [("PPR", 0.50), ("FA", 0.10), ("TRYP", 0.10), (None, 0.30)],
    "Caprins": [("PPR", 0.50), ("FA", 0.10), ("TRYP", 0.10), (None, 0.30)],
    "Volailles": [("NEW", 0.42), ("BIA", 0.28), ("IAHP", 0.08), (None, 0.22)],
}
MOD_REGION = {"Adamaoua": {"TRYP": 1.6}, "Extrême-Nord": {"PPCB": 1.3, "FA": 1.2}, "Ouest": {"BRU": 1.5, "NEW": 1.2}}
NOMS_ESP = {"Bovins": ["bovins", "zébus", "bêtes"], "Ovins": ["moutons", "ovins", "brebis"],
            "Caprins": ["chèvres", "caprins"], "Volailles": ["poulets", "volailles", "sujets"]}
TRAITEMENTS = {
    None: ["Traitement symptomatique instauré.", "Antibiotique à large spectre administré.", "Anti-inflammatoire et vitamines administrés."],
    "TRYP": ["Trypanocide administré.", "Traitement trypanocide et antianémique."],
    "FA": ["Soins locaux des lésions et antibiotique contre les surinfections.", "Isolement des malades, soins locaux."],
    "NEW": ["Vitamines et antibiotique contre les surinfections.", "Désinfection du bâtiment, isolement des sujets malades."],
}
RECOS = ["Recommande la vaccination de rappel du troupeau.", "Contrôle à renouveler dans 7 jours.",
         "Restriction des mouvements du troupeau.", "Revoir l'alimentation et l'eau de boisson.", "", ""]
ABREV = [("exploitation", "expl."), ("Traitement", "TTT"), ("animaux", "anx"), ("température", "T°"), ("Suspicion", "Susp."),
         ("Recommande", "Reco :"), ("production", "prod."), ("difficultés", "diff.")]


def surface(sympt, rng, t):
    return rng.choice(SYMPTOMES[sympt]).replace("{t}", f"{t:.1f}".replace(".", ","))


def liste(items, rng):
    if len(items) == 1:
        return items[0]
    if rng.random() < 0.5:
        return ", ".join(items[:-1]) + " et " + items[-1]
    return "; ".join(items)


def accents_perdus(texte):
    return texte.translate(str.maketrans("éèêëàâîïôùûçÉÈ", "eeeeaaiiouuceE"))


def faute(texte, rng):
    mots = texte.split(" ")
    longs = [i for i, m in enumerate(mots) if len(m) >= 6 and m.isalpha()]
    for i in rng.choice(longs, min(2, len(longs)), replace=False) if longs else []:
        m = list(mots[i])
        j = int(rng.integers(1, len(m) - 2))
        m[j], m[j + 1] = m[j + 1], m[j]
        mots[i] = "".join(m)
    return " ".join(mots)


def compte_rendu(esp, code, nom_maladie, sigle, region, n_mal, n_dec, date, rng, tcfg):
    """Retourne (texte, symptômes présents, symptômes niés)."""
    liste_s = SYMPT_MALADIE[code]
    k = int(rng.integers(2, min(5, len(liste_s)) + 1))
    presents = list(rng.choice(liste_s, k, replace=False))
    t = float(rng.uniform(39.6, 41.2))
    formes = [surface(s, rng, t) for s in presents]
    nies = []
    neg = ""
    if rng.random() < tcfg["part_negations"]:
        autres = [s for s in SYMPTOMES if s not in liste_s and s not in presents]
        s = str(rng.choice(autres))
        nies.append(s)
        neg = str(rng.choice(["Pas de {x}.", "Absence de {x}.", "{x} non observé.", "Aucun signe de {x}."])).replace(
            "{x}", rng.choice(SYMPTOMES[s]).replace("{t}", "40,0"))
    noun = str(rng.choice(NOMS_ESP[esp]))
    zone = f"région {region}"
    d = date.strftime("%d/%m/%Y")
    mod = int(rng.integers(0, 4))
    sy = liste(formes, rng)
    if mod == 0:
        deb = f"Visite du {d} à l'exploitation. {n_mal} {noun} présentent {sy}."
    elif mod == 1:
        deb = f"Intervention suite à l'appel de l'éleveur ({d}). Constat : {sy} chez {n_mal} {noun}."
    elif mod == 2:
        deb = f"{noun.capitalize()} : {n_mal} sujets atteints. Signes cliniques : {sy}."
    else:
        deb = f"Rapport de tournée ({zone}). {n_mal} {noun} malades, {n_dec} mort(s). Symptômes relevés : {sy}."
    if code:
        diag = str(rng.choice([f"Suspicion de {sigle} ({nom_maladie.lower()}).", f"Tableau clinique compatible avec : {nom_maladie.lower()}.",
                               f"{sigle} probable."]))
    else:
        diag = str(rng.choice(["Diagnostic à préciser, prélèvements envoyés au laboratoire.", "Pas de diagnostic formel pour le moment."]))
    trait = str(rng.choice(TRAITEMENTS.get(code, TRAITEMENTS[None])))
    reco = str(rng.choice(RECOS))
    texte = " ".join(x for x in [deb, neg, diag, trait, reco] if x)
    texte = re.sub(r"\b([Dd])e (?=[AEIOUYaeiouyéèêàâîïôûœ])", r"\1'", texte)  # élision : « de orchite » -> « d'orchite »
    if rng.random() < tcfg["part_abreviations"]:
        for a, b in ABREV:
            texte = texte.replace(a, b)
    if rng.random() < tcfg["part_fautes"]:
        texte = faute(texte, rng)
        if rng.random() < 0.5:
            texte = accents_perdus(texte)
    return texte, presents, nies


def main():
    cfg = charger_cfg()
    ic = cfg["interventions"]
    rng = np.random.default_rng(cfg["projet"]["graine"] + 10)
    ref, verite = dossier_ref(cfg), dossier_verite(cfg)
    expl = pd.read_csv(ref / "ref_exploitations.csv")
    eff = pd.read_csv(ref / "ref_exploitation_especes.csv")
    vets = pd.read_csv(ref / "ref_veterinaires.csv")
    mal = pd.read_csv(ref / "ref_maladies.csv").set_index("code_maladie")
    aff = pd.read_csv(verite / "affectation_veterinaire.csv").set_index("id_exploitation")["id_veterinaire"]
    ani = pd.read_csv(verite / "animal_propre.csv", parse_dates=["date_sortie"])
    lots = pd.read_csv(verite / "lot_propre.csv")
    hebdo = pd.read_csv(RACINE / cfg["cheptel"]["sortie"] / "suivi_lot_semaine.csv", parse_dates=["date_semaine"])
    pil = pd.read_csv(verite / "pilotes_exploitation_mois.csv", parse_dates=["mois"])
    usd = taux_usd(cfg)
    debut = pd.Timestamp(cfg["projet"]["periode"]["debut"])
    fin_p = pd.Timestamp(cfg["projet"]["periode"]["fin"])
    fx = expl.set_index("id_exploitation")
    vstat = vets.set_index("id_veterinaire")["statut"]

    # ------------------------------------------------------------------ événements sanitaires
    ev = []
    dm = ani[(ani["motif_sortie"] == "deces") & (ani["cause_deces"] == "maladie")]
    for (f, e, per), g in dm.groupby(["id_exploitation", "espece", dm["date_sortie"].dt.to_period("M")]):
        sig = max(g["date_sortie"].min() - pd.Timedelta(days=int(rng.integers(0, 4))), debut)
        n_dec = len(g)
        ev.append((f, e, sig, n_dec + int(rng.poisson(max(1, 2 * n_dec))), n_dec, "A"))
    mult = pil.set_index(["id_exploitation", "mois"])["multiplicateur_mortalite"]
    eff0 = eff.groupby("id_exploitation")["effectif_initial"].sum()
    for (f, mois), m in mult.items():
        lam = ic["taux_episodes_sans_deces"] * m * np.sqrt(eff0.get(f, 20) / 20)
        for _ in range(int(rng.poisson(lam))):
            sp = eff[eff["id_exploitation"] == f]
            e = str(rng.choice(sp["espece"].to_numpy(), p=(sp["effectif_initial"] / sp["effectif_initial"].sum()).to_numpy()))
            sig = mois + pd.Timedelta(days=int(rng.integers(0, mois.days_in_month)))
            ev.append((f, e, sig, int(max(1, round(rng.lognormal(np.log(6), 0.7)))), int(rng.poisson(0.2)), "B"))
    h = hebdo.merge(lots[["id_lot", "id_exploitation"]], on="id_lot")
    h["ratio"] = h["nb_morts"] / (h["effectif_fin_semaine"] + h["nb_morts"]).clip(lower=1)
    for r in h[(h["ratio"] >= ic["seuil_mortalite_hebdo_lot"]) & (h["nb_morts"] >= 5)].itertuples():
        mal_n = min(r.effectif_fin_semaine + r.nb_morts, int(round(r.nb_morts * rng.uniform(1.5, 4))))
        ev.append((r.id_exploitation, "Volailles", r.date_semaine + pd.Timedelta(days=int(rng.integers(0, 6))), mal_n, int(r.nb_morts), "C"))
    E = pd.DataFrame(ev, columns=["id_exploitation", "espece", "date_signalement", "nb_malades", "nb_deces", "origine"])
    E = E[(E["date_signalement"] >= debut) & (E["date_signalement"] <= fin_p)].reset_index(drop=True)
    n = len(E)
    E["date_signalement"] = E["date_signalement"].dt.normalize() + pd.to_timedelta(rng.integers(6, 18, n), unit="h") + pd.to_timedelta(rng.integers(0, 60, n), unit="m")
    E["region"] = E["id_exploitation"].map(fx["region"])
    E["pcode"] = E["id_exploitation"].map(fx["pcode_departement"])

    # ------------------------------------------------------------------ maladie, vétérinaire, délai, coûts
    codes = []
    for r in E.itertuples():
        base = MALADIES_ESP[r.espece]
        w = np.array([p * MOD_REGION.get(r.region, {}).get(c, 1.0) for c, p in base])
        codes.append(base[rng.choice(len(base), p=w / w.sum())][0])
    E["code_maladie"] = codes
    vet = E["id_exploitation"].map(aff).to_numpy(dtype=object)
    autre = rng.random(n) < 0.15
    for pc, g in vets.groupby("pcode_departement"):
        m = autre & (E["pcode"].to_numpy() == pc)
        if m.any():
            vet[m] = rng.choice(g["id_veterinaire"].to_numpy(), m.sum())
    E["id_veterinaire"] = vet
    delai = valeur_mois(pil.set_index(["id_exploitation", "mois"])["delai_veto_h"], E["id_exploitation"], E["date_signalement"])
    E["delai_h"] = np.clip(np.nan_to_num(delai, nan=30.0) * rng.lognormal(0, 0.3, n), 1, 400)
    E["date_intervention"] = E["date_signalement"] + pd.to_timedelta(E["delai_h"], unit="h").dt.round("min")
    E["nb_traites"] = np.minimum(E["nb_malades"], np.round(E["nb_malades"] * rng.uniform(0.6, 1.0, n))).astype(int)
    cout_u = E["espece"].map(ic["cout_medicament_par_animal"]).to_numpy(float)
    medic = E["nb_traites"].to_numpy() * cout_u * rng.lognormal(0, 0.25, n)
    hono = E["id_veterinaire"].map(vstat).map(ic["honoraires_xaf"]).to_numpy(float) * rng.lognormal(0, 0.2, n)
    en_usd = rng.random(n) < ic["part_cout_usd"]
    taux = np.array([usd(d.year, d.month) for d in E["date_intervention"]])
    E["devise"] = np.where(en_usd, "USD", "XAF")
    E["cout_medicaments"] = np.where(en_usd, np.round(medic / taux, 2), np.round(medic, 0))
    E["honoraires"] = np.where(en_usd, np.round(hono / taux, 2), np.round(hono, 0))

    # ------------------------------------------------------------------ comptes rendus
    textes, golds, negs = [], [], []
    for r in E.itertuples():
        c = r.code_maladie if isinstance(r.code_maladie, str) else None  # None = diagnostic non précisé
        t, pres, nie = compte_rendu(r.espece, c, mal.loc[c, "maladie"] if c else "", mal.loc[c, "sigle"] if c else "", r.region,
                                    r.nb_malades, r.nb_deces, r.date_intervention, rng, ic["texte"])
        textes.append(t)
        golds.append("; ".join(pres))
        negs.append("; ".join(nie))
    E["compte_rendu"], E["symptomes_reels"], E["symptomes_nies"] = textes, golds, negs
    E = E.sort_values("date_signalement").reset_index(drop=True)
    E.insert(0, "id_intervention", [f"INT-{i:06d}" for i in range(1, n + 1)])

    propre_cols = ["id_intervention", "id_exploitation", "id_veterinaire", "espece", "code_maladie", "date_signalement",
                   "date_intervention", "nb_malades", "nb_traites", "nb_deces", "cout_medicaments", "honoraires", "devise",
                   "compte_rendu", "origine"]
    E[propre_cols].to_csv(verite / "intervention_propre.csv", index=False, encoding="utf-8")
    gold = E[["id_intervention", "code_maladie", "symptomes_reels", "symptomes_nies", "compte_rendu"]].rename(columns={"code_maladie": "maladie_reelle"})
    gold.to_csv(verite / "gold_comptes_rendus.csv", index=False, encoding="utf-8")
    gold.sample(min(ic["echantillon_verification"], n), random_state=1).to_csv(verite / "echantillon_a_verifier.csv", index=False, encoding="utf-8")

    # ------------------------------------------------------------------ défauts volontaires
    obs = E.copy()
    k = max(3, int(n * ic["defauts"]["taux"] / 4))
    etiq = []
    i1 = rng.choice(n, k, replace=False)
    obs.loc[i1, "date_intervention"] = pd.NaT
    etiq += [("intervention", x, "date_intervention_absente") for x in obs.loc[i1, "id_intervention"]]
    i2 = rng.choice(np.setdiff1d(np.arange(n), i1), k, replace=False)
    obs.loc[i2, "date_intervention"] = obs.loc[i2, "date_signalement"] - pd.Timedelta(days=2)
    etiq += [("intervention", x, "intervention_avant_signalement") for x in obs.loc[i2, "id_intervention"]]
    i3 = rng.choice(n, k, replace=False)
    obs.loc[i3, "cout_medicaments"] = -obs.loc[i3, "cout_medicaments"]
    etiq += [("intervention", x, "cout_negatif") for x in obs.loc[i3, "id_intervention"]]
    i4 = rng.choice(n, k, replace=False)
    obs.loc[i4, "compte_rendu"] = ""
    etiq += [("intervention", x, "compte_rendu_vide") for x in obs.loc[i4, "id_intervention"]]
    i5 = rng.choice(n, k, replace=False)
    dup = obs.loc[i5].copy()
    dup["id_intervention"] = [f"INT-{n + j + 1:06d}" for j in range(k)]
    etiq += [("intervention", x, "doublon") for x in dup["id_intervention"]]
    obs = pd.concat([obs, dup], ignore_index=True)

    # ------------------------------------------------------------------ écriture XML
    racine = ET.Element("reseau_veterinaire", {"extraction": pd.Timestamp.now().strftime("%Y-%m-%d")})
    xv = ET.SubElement(racine, "veterinaires")
    for r in vets.itertuples():
        v = ET.SubElement(xv, "veterinaire", {"id": r.id_veterinaire})
        for tag, val in [("nom", r.nom), ("prenom", r.prenom), ("statut", r.statut), ("specialite", r.specialite),
                         ("date_prise_poste", r.date_prise_poste)]:
            ET.SubElement(v, tag).text = str(val)
        ET.SubElement(v, "departement", {"pcode": r.pcode_departement}).text = r.departement
    xi = ET.SubElement(racine, "interventions")
    for r in obs.itertuples():
        i = ET.SubElement(xi, "intervention", {"id": r.id_intervention})
        ET.SubElement(i, "exploitation").text = r.id_exploitation
        ET.SubElement(i, "veterinaire").text = r.id_veterinaire
        ET.SubElement(i, "espece").text = r.espece
        code = r.code_maladie if isinstance(r.code_maladie, str) else None
        m = ET.SubElement(i, "maladie", {"code": code or ""})
        m.text = mal.loc[code, "maladie"] if code else ""
        ET.SubElement(i, "date_signalement").text = r.date_signalement.strftime("%Y-%m-%dT%H:%M:%S")
        if pd.notna(r.date_intervention):
            ET.SubElement(i, "date_intervention").text = r.date_intervention.strftime("%Y-%m-%dT%H:%M:%S")
        ET.SubElement(i, "nb_animaux_malades").text = str(int(r.nb_malades))
        ET.SubElement(i, "nb_animaux_traites").text = str(int(r.nb_traites))
        ET.SubElement(i, "nb_deces").text = str(int(r.nb_deces))
        ET.SubElement(i, "cout_medicaments", {"devise": r.devise}).text = f"{r.cout_medicaments:g}"
        ET.SubElement(i, "honoraires", {"devise": r.devise}).text = f"{r.honoraires:g}"
        ET.SubElement(i, "compte_rendu").text = r.compte_rendu
    ET.indent(racine, space="  ")
    sortie = RACINE / ic["sortie"]
    sortie.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(racine).write(sortie / "veterinaires_interventions.xml", encoding="utf-8", xml_declaration=True)
    pd.DataFrame(etiq, columns=["table", "identifiant", "type_defaut"]).to_csv(verite / "defauts_veterinaires.csv", index=False)

    # ------------------------------------------------------------------ contrôles
    print(f"=== {len(vets)} vétérinaires et {len(obs)} interventions (dont {len(etiq)} défauts volontaires) ===")
    print("Origine des interventions :", E["origine"].value_counts().to_dict(), "(A = décès par maladie, B = épisode, C = lot de volailles)")
    print("\nMaladie par espèce :")
    print(pd.crosstab(E["espece"], E["code_maladie"].fillna("non précisée")).to_string())
    print("\nDélai signalement -> intervention (heures), par région :")
    print(E.groupby("region")["delai_h"].describe()[["count", "mean", "50%", "max"]].round(1).to_string())
    print(f"\nTextes : {np.mean([len(t) for t in textes]):.0f} caractères en moyenne ; {(E['symptomes_nies'] != '').mean() * 100:.0f} % avec une négation")
    print("\nExemples de comptes rendus :")
    for t in E["compte_rendu"].sample(4, random_state=3):
        print(" -", t)
    print("\nÉcrit dans", sortie.relative_to(RACINE))


if __name__ == "__main__":
    main()
