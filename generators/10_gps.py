"""Génère la source 14 : colliers GPS (fichiers JSON, un par mois).

300 bovins adultes de 60 exploitations pastorales ou transhumantes portent un collier pendant toute l'année
choisie (2025 par défaut) : 4 positions par jour (00h, 06h, 12h, 18h). Chaque animal passe la nuit près du
« kraal » de son exploitation et pâture dans un rayon qui dépend de la région et de l'état des pâturages
(NDVI : plus loin en saison sèche). Les exploitations transhumantes suivent leur troupeau vers le site de
pâturage de saison sèche (mouvements de la source 6).

Anomalies injectées, avec leur étiquette de vérité (pour évaluer le modèle ML 3) :
  - immobilite_maladie       : 4 jours d'immobilité avant le décès d'un animal mort de maladie, activité réduite avant
  - immobilite_sans_deces    : épisodes de 3 jours d'immobilité sans décès
  - sortie_de_zone_vol       : saut de plus de 40 km puis fuite, puis le collier cesse d'émettre
Défauts de qualité : positions non reçues (2 %), pertes de signal de 3 jours, collier qui s'arrête à la sortie
de l'animal (vente, abattage, décès).

Sorties  data/generated/gps/gps_<année>-<mois>.json, colliers.json
         data/generated/pilotes/gps_anomalies_verite.csv

Lancer depuis la racine du dépôt :  python generators/10_gps.py
"""
import numpy as np
import pandas as pd

from common import (JOURS, RACINE, charger_cfg, dossier_ref, dossier_verite, jour, jours, dates, mois_periode, table_mois)

HEURES = np.array([0, 6, 12, 18])


def haversine(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def main():
    cfg = charger_cfg()
    g = cfg["gps"]
    rng = np.random.default_rng(cfg["projet"]["graine"] + 9)
    ref, verite = dossier_ref(cfg), dossier_verite(cfg)
    expl = pd.read_csv(ref / "ref_exploitations.csv")
    ids = expl["id_exploitation"].tolist()
    ani = pd.read_csv(verite / "animal_propre.csv", parse_dates=["date_naissance", "date_entree", "date_sortie"])
    mouv = pd.read_csv(verite / "mouvements_propre.csv", parse_dates=["date_depart", "date_arrivee"])
    pil = pd.read_csv(verite / "pilotes_exploitation_mois.csv", parse_dates=["mois"])
    mois0 = mois_periode(cfg)[0]
    an = int(g["annee"])
    D0, D1 = jour(f"{an}-01-01"), jour(f"{an}-12-31")
    nd = D1 - D0 + 1
    d0 = pd.Timestamp(f"{an}-01-01")

    # ------------------------------------------------------------------ choix des animaux équipés
    present = ani[(ani["espece"] == "Bovins") & (ani["date_entree"] <= d0) & (ani["date_sortie"].isna() | (ani["date_sortie"] > d0))
                  & ((d0 - ani["date_naissance"]).dt.days / JOURS >= 12)]
    pasto = set(expl.loc[expl["systeme_elevage"].isin(["Pastoral", "Transhumant"]), "id_exploitation"])
    present = present[present["id_exploitation"].isin(pasto)]
    n_par = present.groupby("id_exploitation").size()
    fermes = n_par[n_par >= 5].index.to_numpy()
    fermes = rng.choice(fermes, min(g["exploitations_equipees"], len(fermes)), replace=False)
    quota = int(np.ceil(g["colliers"] / len(fermes)))
    choisis = pd.concat([present[present["id_exploitation"] == f].sample(min(quota, n_par[f]), random_state=int(rng.integers(1e6)))
                         for f in fermes]).head(g["colliers"]).reset_index(drop=True)
    nc = len(choisis)
    colliers = pd.DataFrame({"id_collier": [f"COL-{i:03d}" for i in range(1, nc + 1)], "id_animal": choisis["id_animal"],
                             "id_exploitation": choisis["id_exploitation"], "espece": "Bovins", "date_pose": d0.strftime("%Y-%m-%d")})
    fx = expl.set_index("id_exploitation")
    sortie_j = np.where(choisis["date_sortie"].notna(), jours(choisis["date_sortie"]), D1 + 1)
    idx_sortie = np.clip(sortie_j - D0, 0, nd)  # nombre de jours de présence

    # ------------------------------------------------------------------ centre de vie de chaque exploitation, jour par jour
    farms = sorted(set(colliers["id_exploitation"]))
    fi = {f: i for i, f in enumerate(farms)}
    Dmin = D0 - 400
    nall = D1 - Dmin + 1
    Clat = np.tile(fx.loc[farms, "latitude"].to_numpy()[:, None], (1, nall))
    Clon = np.tile(fx.loc[farms, "longitude"].to_numpy()[:, None], (1, nall))
    trans = mouv[mouv["type_mouvement"].str.startswith("transhumance")]
    for f in farms:
        for e in trans[trans["id_exploitation"] == f].sort_values("date_depart").drop_duplicates(["date_depart", "type_mouvement"]).itertuples():
            d1, d2 = jour(e.date_depart), jour(e.date_arrivee)
            for d in range(max(d1, Dmin), min(d2, D1) + 1):
                t = (d - d1) / max(d2 - d1, 1)
                Clat[fi[f], d - Dmin] = e.lat_o + t * (e.lat_d - e.lat_o)
                Clon[fi[f], d - Dmin] = e.lon_o + t * (e.lon_d - e.lon_o)
            if d2 + 1 <= D1:
                Clat[fi[f], max(d2 + 1, Dmin) - Dmin:] = e.lat_d
                Clon[fi[f], max(d2 + 1, Dmin) - Dmin:] = e.lon_d
    fc = np.array([fi[f] for f in colliers["id_exploitation"]])
    C_lat = Clat[fc, D0 - Dmin:] + rng.normal(0, 0.001, (nc, 1))
    C_lon = Clon[fc, D0 - Dmin:] + rng.normal(0, 0.001, (nc, 1))

    # ------------------------------------------------------------------ rayon de pâturage (plus large quand les pâturages sont secs)
    Z = table_mois(pil, "ndvi_z", ids).to_numpy()
    jr = dates(np.arange(D0, D1 + 1))
    m_idx = np.clip((jr.year - mois0.year) * 12 + jr.month - mois0.month, 0, Z.shape[1] - 1)
    Zday = Z[[ids.index(f) for f in colliers["id_exploitation"]]][:, np.asarray(m_idx)]
    r_base = colliers["id_exploitation"].map(fx["region"]).map(g["rayon_paturage_km"]).to_numpy(float)
    rdry = 1 + 0.3 * np.clip(-Zday, -1, 2)

    # ------------------------------------------------------------------ anomalies : épisodes d'immobilité liés à la maladie
    imm = np.zeros((nc, nd), bool)
    red = np.zeros((nc, nd), bool)
    anomalies, mort_maladie = [], np.zeros(nc, bool)
    for c in range(nc):
        mort = choisis["motif_sortie"].iat[c] == "deces" and choisis["cause_deces"].iat[c] == "maladie" and sortie_j[c] <= D1
        if mort:
            mort_maladie[c] = True
            dd = sortie_j[c] - D0
            imm[c, max(dd - 4, 0):max(dd, 0)] = True
            red[c, max(dd - 8, 0):max(dd - 4, 0)] = True
            if dd - 4 >= 0:
                anomalies.append((colliers["id_collier"].iat[c], colliers["id_animal"].iat[c], "immobilite_maladie",
                                  dates([D0 + dd - 4])[0], dates([D0 + dd])[0]))
    autres = np.flatnonzero((idx_sortie >= nd) & ~mort_maladie)
    rng.shuffle(autres)
    episodes = []
    for c in autres[:g["immobilites_sans_deces"]]:
        s = int(rng.integers(10, nd - 10))
        imm[c, s:s + 3] = True
        episodes.append((c, s, s + 3))
        anomalies.append((colliers["id_collier"].iat[c], colliers["id_animal"].iat[c], "immobilite_sans_deces",
                          dates([D0 + s])[0], dates([D0 + s + 3])[0]))

    # ------------------------------------------------------------------ positions (nc x jours x 4 créneaux)
    fslot = np.array([0.15, 0.15, 1.0, 0.7])
    rr = (r_base[:, None, None] * rdry[:, :, None] * fslot[None, None, :] * rng.lognormal(0, 0.25, (nc, nd, 4))
          * np.where(red[:, :, None], 0.4, 1.0))
    ang = rng.uniform(0, 2 * np.pi, (nc, nd, 4))
    lat = C_lat[:, :, None] + rr * np.sin(ang) / 111.0
    lon = C_lon[:, :, None] + rr * np.cos(ang) / (111.0 * np.cos(np.radians(C_lat))[:, :, None])
    for c, s, e in episodes:  # l'animal reste au même endroit pendant tout l'épisode
        lat[c, s:e, :], lon[c, s:e, :] = lat[c, s, 2], lon[c, s, 2]
    for c in np.flatnonzero(mort_maladie):
        d = np.flatnonzero(imm[c])
        if len(d):
            lat[c, d, :], lon[c, d, :] = lat[c, d[0], 2], lon[c, d[0], 2]
    sigma = g["bruit_m"] / 1000.0
    lat = lat + rng.normal(0, sigma / 111.0, lat.shape)
    lon = lon + rng.normal(0, sigma / 111.0, lon.shape)
    LAT, LON = lat.reshape(nc, nd * 4).copy(), lon.reshape(nc, nd * 4).copy()
    valid = np.ones((nc, nd * 4), bool)

    # vols : saut de plus de 40 km puis fuite, le collier s'arrête au bout de 8 créneaux
    candidats = np.setdiff1d(autres[g["immobilites_sans_deces"]:], [])
    for c in candidats[:g["vols"]]:
        t = int(rng.integers(40, nd * 4 - 40))
        theta = rng.uniform(0, 2 * np.pi)
        for j in range(8):
            km = rng.uniform(40, 80) if j == 0 else rng.uniform(15, 25)
            cap = theta + rng.normal(0, 0.15)
            LAT[c, t + j] = LAT[c, t + j - 1] + km * np.cos(cap) / 111.0
            LON[c, t + j] = LON[c, t + j - 1] + km * np.sin(cap) / (111.0 * np.cos(np.radians(LAT[c, t + j - 1])))
        valid[c, t + 8:] = False
        anomalies.append((colliers["id_collier"].iat[c], colliers["id_animal"].iat[c], "sortie_de_zone_vol",
                          dates([D0 + t // 4])[0] + pd.Timedelta(hours=int(HEURES[t % 4])), dates([D0 + (t + 8) // 4])[0]))
    # pertes de signal de 3 jours
    libres = np.setdiff1d(np.arange(nc), np.concatenate([np.flatnonzero(mort_maladie), candidats[:g["vols"]]]))
    pertes = []
    for c in rng.choice(libres, min(g["pertes_longues"], len(libres)), replace=False):
        s = int(rng.integers(5, nd - 5))
        valid[c, 4 * s:4 * (s + 3)] = False
        pertes.append((colliers["id_collier"].iat[c], colliers["id_animal"].iat[c], "perte_signal_longue",
                       dates([D0 + s])[0], dates([D0 + s + 3])[0]))
    valid &= rng.random(valid.shape) >= g["perte_signal"]
    for c in range(nc):  # le collier s'arrête quand l'animal sort du troupeau
        if idx_sortie[c] < nd:
            valid[c, 4 * (int(idx_sortie[c]) + 1):] = False

    # ------------------------------------------------------------------ vitesse, batterie, écriture
    dist = haversine(LAT[:, 1:], LON[:, 1:], LAT[:, :-1], LON[:, :-1])
    VIT = np.concatenate([np.zeros((nc, 1)), dist / 6.0], axis=1)
    batterie = 100 - ((rng.uniform(0, 85, (nc, 1)) + 0.2 * np.arange(nd * 4)[None, :]) % 85)
    horo = pd.to_datetime((np.arange(D0, D1 + 1)[:, None] * 24 + HEURES[None, :]).ravel(), unit="h")
    cc, tt = np.nonzero(valid)
    df = pd.DataFrame({
        "id_collier": colliers["id_collier"].to_numpy()[cc], "id_animal": colliers["id_animal"].to_numpy()[cc],
        "id_exploitation": colliers["id_exploitation"].to_numpy()[cc], "horodatage": horo[tt],
        "latitude": LAT[cc, tt].round(5), "longitude": LON[cc, tt].round(5),
        "vitesse_kmh": VIT[cc, tt].round(3), "batterie_pct": batterie[cc, tt].round(1)})
    df = df.sort_values(["horodatage", "id_collier"]).reset_index(drop=True)

    sortie = RACINE / g["sortie"]
    sortie.mkdir(parents=True, exist_ok=True)
    for periode, sub in df.groupby(df["horodatage"].dt.to_period("M")):
        out = sub.assign(horodatage=sub["horodatage"].dt.strftime("%Y-%m-%dT%H:%M:%S"))
        out.to_json(sortie / f"gps_{periode}.json", orient="records", force_ascii=False)
    colliers.to_json(sortie / "colliers.json", orient="records", force_ascii=False)
    et = pd.DataFrame(anomalies + pertes, columns=["id_collier", "id_animal", "type_anomalie", "debut", "fin"])
    et.to_csv(verite / "gps_anomalies_verite.csv", index=False, encoding="utf-8")

    # ------------------------------------------------------------------ contrôles
    print(f"=== {len(df)} positions GPS ({nc} colliers, {len(farms)} exploitations, année {an}) ===")
    print("Positions par mois :", df.groupby(df["horodatage"].dt.month).size().to_dict())
    print(f"Positions théoriques non reçues (pertes de signal, vols, animaux sortis du troupeau) : {100 * (1 - len(df) / (nc * nd * 4)):.1f} %")
    print("Anomalies étiquetées :", et["type_anomalie"].value_counts().to_dict())
    d_home = haversine(LAT, LON, np.repeat(fx.loc[colliers["id_exploitation"], "latitude"].to_numpy()[:, None], nd * 4, 1),
                       np.repeat(fx.loc[colliers["id_exploitation"], "longitude"].to_numpy()[:, None], nd * 4, 1))
    syst = colliers["id_exploitation"].map(fx["systeme_elevage"]).to_numpy()
    mois_t = np.repeat(jr.month.to_numpy(), 4)
    print("\nDistance moyenne au kraal (km), selon le système d'élevage :")
    t = pd.DataFrame({m: [d_home[syst == s][:, mois_t == m].mean() for s in ("Pastoral", "Transhumant")] for m in (2, 4, 8, 11)},
                     index=["Pastoral", "Transhumant"]).round(1)
    t.columns = [f"mois {m}" for m in t.columns]
    print(t.to_string())
    print(f"Vitesse moyenne : {np.nanmean(VIT[valid]):.2f} km/h ; maximum : {VIT[valid].max():.1f} km/h")
    print("Écrit dans", sortie.relative_to(RACINE))


if __name__ == "__main__":
    main()
