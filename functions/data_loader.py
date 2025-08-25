import pandas as pd
from typing import BinaryIO, Union
import io

def load_and_clean_data(file: Union[BinaryIO, io.BytesIO]) -> pd.DataFrame:
    """
    Carga un archivo Excel (.xlsx o .xls), renombra columnas a estándar y realiza limpieza básica de datos.
    Args:
        file: Archivo Excel subido por el usuario (BinaryIO) o BytesIO de archivo guardado.
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
    
    # Función para buscar columna por múltiples variaciones
    def find_column(possible_names, df_columns):
        """Busca la primera columna que coincida con alguna de las variaciones"""
        for name in possible_names:
            if name in df_columns:
                return name
        return None
    
    # Mapeo más robusto de columnas con múltiples variaciones
    column_mappings = {
        'cliente': ['cliente', 'cod_cliente', 'codigo_cliente', 'cód_cliente'],
        'nombre_cliente': ['nombre_cliente', 'nombre', 'cliente_nombre', 'nom_cliente'],
        'localidad': ['localidad', 'ciudad', 'local', 'lugar'],
        'codigo_del_articulo': ['artículo', 'articulo', 'codigo_articulo', 'cod_articulo', 'código_artículo', 'codigo_del_articulo', 'codigo', 'item'],
        'descripcion_del_producto': ['descripción_original', 'descripcion_original', 'descripción', 'descripcion', 'producto', 'desc_producto', 'articulo_desc'],
        'vendedor': ['vendedor', 'cod_vendedor', 'codigo_vendedor'],
        'nombre_vendedor': ['nombre', 'nombre_vendedor', 'vendedor_nombre'],
        'cantidad_vendida': ['unidades', 'cantidad', 'cant', 'cantidad_vendida', 'units', 'qty'],
        'total': ['total', 'importe', 'monto', 'precio_total']
    }
    
    # Aplicar renombrado usando el mapeo robusto
    rename_dict = {}
    for standard_name, possible_names in column_mappings.items():
        found_column = find_column(possible_names, df.columns)
        if found_column:
            rename_dict[found_column] = standard_name
    
    df = df.rename(columns=rename_dict)
    
    # Convertir tipos de datos para evitar errores de Arrow
    if 'codigo_del_articulo' in df.columns:
        df['codigo_del_articulo'] = df['codigo_del_articulo'].astype(str)
    if 'cantidad_vendida' in df.columns:
        df['cantidad_vendida'] = pd.to_numeric(df['cantidad_vendida'], errors='coerce')
    if 'cliente' in df.columns:
        df['cliente'] = df['cliente'].astype(str)
    if 'localidad' in df.columns:
        df['localidad'] = df['localidad'].astype(str)
    
    return df 