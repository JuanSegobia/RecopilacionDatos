import pandas as pd
from typing import Optional

def top_selling_product_by_month(df: pd.DataFrame, month: int, year: int) -> pd.DataFrame:
    """
    Devuelve el producto más vendido en un mes y año específico.
    """
    df['fecha_de_la_venta'] = pd.to_datetime(df['fecha_de_la_venta'])
    filtered = df[(df['fecha_de_la_venta'].dt.month == month) & (df['fecha_de_la_venta'].dt.year == year)]
    result = filtered.groupby(['codigo_del_articulo', 'descripcion_del_producto'])['cantidad_vendida'].sum().reset_index()
    return result.sort_values('cantidad_vendida', ascending=False).head(1)

def top_selling_products(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """
    Devuelve los n productos más vendidos en general. Solo cuenta ventas normales.
    """
    # Filtrar solo las ventas que cuentan (excluir categorías especiales)
    if 'cuenta_ventas' in df.columns:
        df_ventas = df[df['cuenta_ventas'] == True]
    else:
        df_ventas = df  # Si no existe la columna, usar todos los datos
        
    result = df_ventas.groupby(['codigo_del_articulo', 'descripcion_del_producto'])['cantidad_vendida'].sum().reset_index()
    return result.sort_values('cantidad_vendida', ascending=False).head(n) 