import pandas as pd
from functions.schemas import canonicalize

REQUIRED = ['cantidad_vendida']


def parse_articulos_mes(df: pd.DataFrame) -> pd.DataFrame:
    df, missing = canonicalize(df, REQUIRED)
    if missing:
        raise ValueError(f"Columnas faltantes en formato articulos_mes: {missing}")

    if 'cantidad_vendida' in df.columns:
        df['cantidad_vendida'] = pd.to_numeric(df['cantidad_vendida'], errors='coerce')

    df['cuenta_ventas'] = True
    return df
