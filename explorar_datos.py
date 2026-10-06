import pandas as pd

ARCHIVO = "Insumos_agricolas_BD_SIPSA-I/Insumos agricolas - BD SIPSA_I 2026.csv"

df = pd.read_csv(ARCHIVO, sep=";", encoding="latin-1", dtype=str)
df.columns = [c.strip() for c in df.columns]
df["PRECIO"] = pd.to_numeric(df["PRECIO"].str.replace(".", "", regex=False))

print("Filas y columnas:", df.shape)
print("\nValores vacíos por columna:\n", df.isna().sum())
print("\nRegistros por mes:\n", df["MES_AÑO"].value_counts())
print("\nDepartamentos:", df["CÓDIGO DIVIPOLA"].nunique())
print("Categorías CPC:", df["CÓDIGO CPC"].nunique())
print("Artículos distintos:", df["ARTÍCULO"].nunique())
print("\nEstadísticas del precio:\n", df["PRECIO"].describe())
print("\nPrimeras filas:\n", df.head())