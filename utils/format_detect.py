# utils/format_detect.py
import pandas as pd
import unicodedata

TEMPORADA_REQUIRED = {"cliente","codigo_del_articulo","descripcion_del_producto","cantidad_vendida"}
LOCALES_REQUIRED   = {"local","fecha","codigo_del_articulo","cantidad_vendida"}  # ajustá a tus columnas reales

LOCAL_KEYS = {
    "centenario": ["centenario"],
    "55": [" 55 ", "_55", "-55", "local55", "sucursal55"],
    "49": [" 49 ", "_49", "-49", "local49", "sucursal49"],
    "5":  [" 5 ",  "_5",  "-5",  "local5",  "sucursal5"],
}


def _norm(s: str) -> str:
    if s is None:
        return ""
    s = ''.join(c for c in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(c))
    return s.strip().lower()


def detect_format(df: pd.DataFrame) -> str:
    cols = set(map(str.lower, df.columns))
    if TEMPORADA_REQUIRED.issubset(cols):
        return "temporada"
    if LOCALES_REQUIRED.issubset(cols):
        return "locales"
    return "desconocido"


def detect_from_filename(filename: str) -> str:
    name = _norm(filename)
    if not name:
        return ""
    # temporada
    if "temporada" in name:
        return "temporada"
    # artículos más vendidos por mes
    if "articulos" in name and ("mes" in name or "mensual" in name or "mas_vendidos" in name or "más_vendidos" in name):
        return "articulos_mes"
    # locales: detectar sublocal
    if "local" in name or "sucursal" in name or any(k in name for v in LOCAL_KEYS.values() for k in v):
        for loc, keys in LOCAL_KEYS.items():
            if any(k in name for k in keys):
                return f"locales:{loc}"
        return "locales"
    return ""


def detect_format_smart(df: pd.DataFrame, filename: str | None) -> str:
    """Combina heurística por nombre con detección por columnas."""
    by_name = detect_from_filename(filename or "")
    if by_name:
        return by_name
    by_cols = detect_format(df)
    return by_cols
