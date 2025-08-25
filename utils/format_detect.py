# utils/format_detect.py
import pandas as pd

TEMPORADA_REQUIRED = {"cliente","codigo_del_articulo","descripcion_del_producto","cantidad_vendida"}
LOCALES_REQUIRED   = {"local","fecha","codigo_del_articulo","cantidad_vendida"}  # ajustá a tus columnas reales

def detect_format(df: pd.DataFrame) -> str:
    cols = set(map(str.lower, df.columns))
    if TEMPORADA_REQUIRED.issubset(cols):
        return "temporada"
    if LOCALES_REQUIRED.issubset(cols):
        return "locales"
    return "desconocido"
