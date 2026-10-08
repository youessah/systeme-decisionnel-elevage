import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)

fichiers = {
    "05/10": "data/raw/wahis_quantitatif_2026-10-05.csv",
    "07/10": "data/raw/wahis_quantitatif_complet.csv",
}
data = {}
for nom, f in fichiers.items():
    df = pd.read_csv(f, encoding="utf-8-sig", dtype=str)
    data[nom] = df
    print("=" * 20, nom, df.shape)
    print("Annees :", df["Année"].min(), "-", df["Année"].max())
    print(df.groupby("Division administrative")["Année"].agg(["min", "max", "count"]).to_string())
    print("Especes :")
    print(df["Espèce"].value_counts(dropna=False).to_string())
    print("Maladies :")
    print(df["Maladie"].str.slice(0, 60).value_counts().to_string())

a, b = data["05/10"], data["07/10"]
m = b.merge(a.drop_duplicates(), on=list(a.columns), how="left", indicator=True)
print("\nLignes du 07/10 absentes du 05/10 :", (m["_merge"] == "left_only").sum(), "sur", len(b))
