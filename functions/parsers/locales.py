import pandas as pd
from functions.schemas import canonicalize

REQUIRED = ['cantidad_vendida']  # Solo cantidad es requerida


def parse_locales(df: pd.DataFrame) -> pd.DataFrame:
    df, missing = canonicalize(df, REQUIRED)
    if missing:
        raise ValueError(f"Columnas faltantes en formato locales: {missing}")
    
    # Mapear columnas específicas de locales si existen
    rename_map = {}
    if 'artículo' in df.columns and 'codigo_del_articulo' not in df.columns:
        rename_map['artículo'] = 'codigo_del_articulo'
    if 'descripción_artículo' in df.columns and 'descripcion_del_producto' not in df.columns:
        rename_map['descripción_artículo'] = 'descripcion_del_producto'
    if 'cantidad' in df.columns and 'cantidad_vendida' not in df.columns:
        rename_map['cantidad'] = 'cantidad_vendida'
    
    if rename_map:
        df = df.rename(columns=rename_map)
    
    # Asegurar que cantidad_vendida sea numérico
    if 'cantidad_vendida' in df.columns:
        df['cantidad_vendida'] = pd.to_numeric(df['cantidad_vendida'], errors='coerce')
    
    # Para locales, no hay tipología ni cuenta_ventas compleja
    df['cuenta_ventas'] = True
    return df
