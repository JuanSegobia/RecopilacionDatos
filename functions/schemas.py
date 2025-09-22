import unicodedata
import pandas as pd
from typing import Dict, List, Tuple

CANONICAL_COLUMNS = [
    'cliente', 'nombre_cliente', 'localidad',
    'codigo_del_articulo', 'descripcion_del_producto',
    'cantidad_vendida', 'total'
]

ALIASES: Dict[str, List[str]] = {
    'cliente': ['cliente','cod_cliente','codigo_cliente','cód_cliente','id_cliente'],
    'nombre_cliente': ['nombre_cliente','nombre','cliente_nombre','nom_cliente'],
    'localidad': ['localidad','ciudad','local','lugar'],
    'codigo_del_articulo': ['artículo','articulo','codigo_articulo','cod_articulo','código_artículo','codigo','item','codigo_del_articulo'],
    'descripcion_del_producto': ['descripción_original','descripcion_original','descripción','descripcion','producto','desc_producto','articulo_desc','descripcion_del_producto','descripción_artículo','descripcion_artículo'],
    'cantidad_vendida': ['unidades','cantidad','cant','cantidad_vendida','units','qty'],
    'total': ['total','importe','monto','precio_total']
}

REQUIRED_BASE = {'cliente','cantidad_vendida'}


def normalize_text(s: str) -> str:
    if s is None:
        return ''
    # quitar tildes, pasar a minúsculas y reemplazar espacios por _
    s = ''.join(c for c in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(c))
    s = s.strip().lower().replace(' ', '_')
    return s


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [normalize_text(c) for c in df.columns]
    return df


def map_aliases_to_canonical(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str,str]]:
    df = df.copy()
    rename_map: Dict[str,str] = {}
    cols_set = set(df.columns)
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            if alias in cols_set:
                rename_map[alias] = canonical
                break
    df = df.rename(columns=rename_map)
    return df, rename_map


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if 'cliente' in df.columns:
        df['cliente'] = df['cliente'].astype(str).str.strip()
    if 'nombre_cliente' in df.columns:
        df['nombre_cliente'] = df['nombre_cliente'].astype(str).str.strip()
    if 'localidad' in df.columns:
        df['localidad'] = df['localidad'].astype(str).str.strip()
    if 'codigo_del_articulo' in df.columns:
        df['codigo_del_articulo'] = df['codigo_del_articulo'].astype(str).str.strip()
    if 'descripcion_del_producto' in df.columns:
        df['descripcion_del_producto'] = df['descripcion_del_producto'].astype(str).str.strip()
    if 'cantidad_vendida' in df.columns:
        df['cantidad_vendida'] = pd.to_numeric(df['cantidad_vendida'], errors='coerce')
    if 'total' in df.columns:
        df['total'] = pd.to_numeric(df['total'], errors='coerce')
    return df


def validate_required(df: pd.DataFrame, required: List[str]) -> List[str]:
    return [c for c in required if c not in df.columns]


def canonicalize(df: pd.DataFrame, required: List[str] = None) -> Tuple[pd.DataFrame, List[str]]:
    df = normalize_columns(df)
    df, _ = map_aliases_to_canonical(df)
    df = coerce_types(df)
    missing = validate_required(df, list(required) if required else list(REQUIRED_BASE))
    return df, missing
