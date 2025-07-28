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
    Incluye ranking y porcentaje formateado.
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
    
    # Ordenar por cantidad vendida y agregar ranking
    resumen = resumen.sort_values('cantidad_vendida', ascending=False).reset_index(drop=True)
    resumen.insert(0, 'Ranking', range(1, len(resumen) + 1))
    
    # Formatear porcentaje
    resumen['Porcentaje'] = resumen['porcentaje'].apply(lambda x: f"{x:.1f}%")
    
    # Reordenar columnas para mejor presentación
    if 'nombre_cliente' in resumen.columns:
        resumen = resumen[['Ranking', 'cliente', 'nombre_cliente', 'cantidad_vendida', 'Porcentaje']]
    else:
        resumen = resumen[['Ranking', 'cliente', 'cantidad_vendida', 'Porcentaje']]
    
    return resumen

def client_returns_count(df: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve la cantidad de devoluciones por cliente con porcentaje, nombre del cliente y ranking.
    Incluye el porcentaje de devoluciones sobre el total de movimientos del cliente.
    """
    # Calcular devoluciones (cantidad negativa)
    devoluciones = df[df['cantidad_vendida'] < 0].copy()
    devoluciones['cantidad_vendida'] = devoluciones['cantidad_vendida'].abs()  # Convertir a positivo para el conteo
    
    if devoluciones.empty:
        return pd.DataFrame(columns=['Ranking', 'cliente', 'nombre_cliente', 'cantidad_devoluciones', 'total_vendido', 'Porcentaje devoluciones'])
    
    # Agrupar devoluciones por cliente
    if 'nombre_cliente' in devoluciones.columns:
        returns_by_client = devoluciones.groupby(['cliente', 'nombre_cliente'])['cantidad_vendida'].sum().reset_index()
    else:
        returns_by_client = devoluciones.groupby('cliente')['cantidad_vendida'].sum().reset_index()
    
    returns_by_client = returns_by_client.rename(columns={'cantidad_vendida': 'cantidad_devoluciones'})
    
    # Calcular total vendido por cliente (solo ventas positivas)
    ventas_positivas = df[df['cantidad_vendida'] > 0]
    if 'nombre_cliente' in ventas_positivas.columns:
        sales_by_client = ventas_positivas.groupby(['cliente', 'nombre_cliente'])['cantidad_vendida'].sum().reset_index()
    else:
        sales_by_client = ventas_positivas.groupby('cliente')['cantidad_vendida'].sum().reset_index()
    
    sales_by_client = sales_by_client.rename(columns={'cantidad_vendida': 'total_vendido'})
    
    # Merge para obtener devoluciones y ventas por cliente
    if 'nombre_cliente' in returns_by_client.columns:
        result = returns_by_client.merge(sales_by_client, on=['cliente', 'nombre_cliente'], how='left')
    else:
        result = returns_by_client.merge(sales_by_client, on='cliente', how='left')
    
    result['total_vendido'] = result['total_vendido'].fillna(0)
    
    # Calcular porcentaje de devoluciones sobre el total de movimientos
    result['porcentaje_devolucion'] = (result['cantidad_devoluciones'] / (result['total_vendido'])) * 100
    result['porcentaje_devolucion'] = result['porcentaje_devolucion'].fillna(0)
    
    # Ordenar por porcentaje de devoluciones (mayor a menor) y agregar ranking
    result = result.sort_values('porcentaje_devolucion', ascending=False).reset_index(drop=True)
    result.insert(0, 'Ranking', range(1, len(result) + 1))
    
    # Formatear porcentaje
    result['Porcentaje devoluciones'] = result['porcentaje_devolucion'].apply(lambda x: f"{x:.1f}%")
    
    # Reordenar columnas para mejor presentación
    if 'nombre_cliente' in result.columns:
        result = result[['Ranking', 'cliente', 'nombre_cliente', 'cantidad_devoluciones', 'total_vendido', 'Porcentaje devoluciones']]
    else:
        result = result[['Ranking', 'cliente', 'cantidad_devoluciones', 'total_vendido', 'Porcentaje devoluciones']]
    
    return result 