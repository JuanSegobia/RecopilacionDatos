# utils/format_detect.py
import pandas as pd

# columnas canónicas ya normalizadas (snake_case, sin tildes)
TEMPORADA_NEEDS_ANY_CLIENT = {"cliente"}  # basta que exista 'cliente' para diferenciar
CODE_SYNS = {"codigo_del_articulo", "codigo", "articulo", "codigo_articulo"}
DESC_SYNS = {"descripcion_del_producto", "descripcion", "desc_prod", "detalle"}
QTY_SYNS  = {"cantidad_vendida", "cantidad", "cant"}

def _has_any(cols: set, syns: set) -> bool:
    return not syns.isdisjoint(cols)

def detect_format(df: pd.DataFrame) -> str:
    return detect_format_v2(df)["family"]

def detect_format_v2(df: pd.DataFrame) -> dict:
    cols = set(map(str, df.columns))

    has_code = _has_any(cols, CODE_SYNS)
    has_desc = _has_any(cols, DESC_SYNS)
    has_qty  = _has_any(cols, QTY_SYNS)
    has_client = _has_any(cols, TEMPORADA_NEEDS_ANY_CLIENT)

    if has_code and has_desc and has_qty and has_client:
        return {"family": "temporada", "version": "v1"}
    if has_code and has_desc and has_qty:
        return {"family": "locales", "version": "v1"}
    return {"family": "desconocido", "version": "v1"}
