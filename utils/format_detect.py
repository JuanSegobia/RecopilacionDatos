# utils/format_detect.py
import pandas as pd

TEMPORADA_REQUIRED = {"cliente","codigo_del_articulo","descripcion_del_producto","cantidad_vendida"}
LOCALES_REQUIRED   = {"codigo_del_articulo","descripcion_del_producto","cantidad_vendida"}

def detect_format(df: pd.DataFrame) -> str:
    """Retrocompatibilidad: devuelve 'temporada' | 'locales' | 'desconocido'."""
    info = detect_format_v2(df)
    return info["family"]

def detect_format_v2(df: pd.DataFrame) -> dict:
    """
    Devuelve un dict extensible con familia y versión.
    {
      "family": "temporada" | "locales" | "desconocido",
      "version": "v1"
    }
    """
    cols = set(map(str.lower, df.columns))
    if TEMPORADA_REQUIRED.issubset(cols):
        return {"family": "temporada", "version": "v1"}
    if LOCALES_REQUIRED.issubset(cols):
        return {"family": "locales", "version": "v1"}
    return {"family": "desconocido", "version": "v1"}
