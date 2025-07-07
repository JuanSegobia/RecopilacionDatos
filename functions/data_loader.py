import pandas as pd
from typing import BinaryIO
import os

def load_and_clean_data(file: BinaryIO) -> pd.DataFrame:
    """
    Carga un archivo Excel (.xlsx o .xls), renombra columnas a estándar y realiza limpieza básica de datos.
    Args:
        file: Archivo Excel subido por el usuario (BinaryIO).
    Returns:
        pd.DataFrame: DataFrame limpio y con nombres estándar.
    """
    filename = getattr(file, 'name', None)
    if filename and filename.lower().endswith('.xls'):
        df = pd.read_excel(file, engine='xlrd')
    else:
        df = pd.read_excel(file, engine='openpyxl')
    # Limpieza básica: eliminar filas vacías y columnas irrelevantes
    df = df.dropna(how='all')
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]  # Quitar columnas sin nombre
    # Normalizar nombres de columnas
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    # Renombrar columnas a estándar
    rename_dict = {
        'cliente': 'cliente',
        'nombre_cliente': 'nombre_cliente',
        'artículo': 'codigo_del_articulo',
        'descripción_original': 'descripcion_del_producto',
        'vendedor': 'vendedor',
        'nombre': 'nombre_vendedor',
        'unidades': 'cantidad_vendida',
        'total': 'total'
    }
    df = df.rename(columns=rename_dict)
    return df 