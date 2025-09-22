import pandas as pd
from functions.schemas import canonicalize
from functions.typology_analysis import add_typology_column

REQUIRED = ['cliente','cantidad_vendida','codigo_del_articulo','descripcion_del_producto']


def parse_temporada(df: pd.DataFrame) -> pd.DataFrame:
    df, missing = canonicalize(df, REQUIRED)
    if missing:
        raise ValueError(f"Columnas faltantes en formato temporada: {missing}")
    df = add_typology_column(df)
    # ventas normales: excluir códigos especiales definidos en typology module si aplica
    df['cuenta_ventas'] = True
    return df
