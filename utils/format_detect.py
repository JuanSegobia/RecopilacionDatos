# utils/format_detect.py
import pandas as pd
import unicodedata
import re

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

    # locales: detectar sublocal (prioridad sobre "articulos" si hay mención de local)
    if "local" in name or "sucursal" in name or any(k in name for v in LOCAL_KEYS.values() for k in v):
        for loc, keys in LOCAL_KEYS.items():
            if any(k in name for k in keys):
                return f"locales:{loc}"
        return "locales"

    # artículos más vendidos por mes (por nombre)
    # Reglas:
    #  - contiene "articulos" y además una pista de mensualidad: "mes"/"mensual"/"mas_vendidos"
    #  - o contiene "articulos" y un mes en español + año (ej: articulos_junio2025)
    #  - o contiene "articulos" y un patrón AAAA-MM o AAAAMM
    if "articulos" in name:
        month_tokens = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "setiembre", "octubre",
            "noviembre", "diciembre"
        ]
        has_month_word = any(m in name for m in month_tokens)
        # patrones de fecha: 2025-07, 2025_07, 202507
        has_year_month_num = bool(re.search(r"(?:19|20)\\d{2}[-_ ]?(0?[1-9]|1[0-2])", name)) or bool(re.search(r"(0?[1-9]|1[0-2])[-_ ]?(?:19|20)\\d{2}", name))
        has_month_hint = ("mes" in name or "mensual" in name or "mas_vendidos" in name or "más_vendidos" in name or has_month_word or has_year_month_num)
        if has_month_hint:
            return "articulos_mes"
    return ""


def detect_format_smart(df: pd.DataFrame, filename: str | None) -> str:
    """Combina heurística por nombre con detección por columnas."""
    by_name = detect_from_filename(filename or "")
    if by_name:
        return by_name
    by_cols = detect_format(df)
    return by_cols
