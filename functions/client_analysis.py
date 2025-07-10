import pandas as pd

def products_bought_by_client(df: pd.DataFrame, client: str, n: int = 10) -> pd.DataFrame:
    """
    Devuelve los n productos más comprados por un cliente determinado.
    """
    df = df.copy()
    df['cliente'] = df['cliente'].astype(str).fillna("")
    filtered = df[df['cliente'].str.lower() == client.lower()]
    result = filtered.groupby(['codigo_del_articulo', 'descripcion_del_producto'])['cantidad_vendida'].sum().reset_index()
    return result.sort_values('cantidad_vendida', ascending=False).head(n)

def client_share_of_sales(df: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve el peso (porcentaje) de cada cliente sobre el total neto de unidades vendidas.
    Incluye el nombre del cliente si está disponible. Solo cuenta ventas normales.
    """
    # Filtrar solo las ventas que cuentan (excluir categorías especiales)
    if 'cuenta_ventas' in df.columns:
        df_ventas = df[df['cuenta_ventas'] == True]
    else:
        df_ventas = df  # Si no existe la columna, usar todos los datos
    
    total_unidades = df_ventas['cantidad_vendida'].sum()  # Total neto (incluye devoluciones como valores negativos)
    
    # Agrupar por cliente y obtener el primer nombre_cliente para cada código
    if 'nombre_cliente' in df_ventas.columns:
        resumen = df_ventas.groupby('cliente').agg({
            'cantidad_vendida': 'sum',
            'nombre_cliente': 'first'  # Tomar el primer nombre para cada cliente
        }).reset_index()
    else:
        resumen = df_ventas.groupby('cliente')['cantidad_vendida'].sum().reset_index()
    
    resumen['porcentaje'] = 100 * resumen['cantidad_vendida'] / total_unidades if total_unidades > 0 else 0
    return resumen.sort_values('porcentaje', ascending=False)

def client_returns_count(df: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve la cantidad de devoluciones (filas con cantidad_vendida negativa) por cliente.
    """
    devoluciones = df[df['cantidad_vendida'] < 0]
    resumen = devoluciones.groupby('cliente')['cantidad_vendida'].count().reset_index()
    resumen = resumen.rename(columns={'cantidad_vendida': 'cantidad_devoluciones'})
    return resumen.sort_values('cantidad_devoluciones', ascending=False) 