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
    Incluye el nombre del cliente y localidad si están disponibles. Solo cuenta ventas normales.
    Incluye ranking y porcentaje formateado.
    """
    # Filtrar solo las ventas que cuentan (excluir categorías especiales)
    if 'cuenta_ventas' in df.columns:
        df_ventas = df[df['cuenta_ventas'] == True]
    else:
        df_ventas = df  # Si no existe la columna, usar todos los datos
    
    total_unidades = df_ventas['cantidad_vendida'].sum()  # Total neto (incluye devoluciones como valores negativos)
    
    # Preparar agregaciones dinámicamente según las columnas disponibles
    agg_dict = {'cantidad_vendida': 'sum'}
    columns_to_include = ['Ranking', 'cliente', 'cantidad_vendida', 'Porcentaje']
    
    if 'nombre_cliente' in df_ventas.columns:
        agg_dict['nombre_cliente'] = 'first'
        columns_to_include.insert(-2, 'nombre_cliente')  # Insertar antes de las últimas dos columnas
    
    if 'localidad' in df_ventas.columns:
        agg_dict['localidad'] = 'first'
        columns_to_include.insert(-2, 'localidad')  # Insertar antes de las últimas dos columnas
    
    # Agrupar por cliente
    resumen = df_ventas.groupby('cliente').agg(agg_dict).reset_index()
    
    resumen['porcentaje'] = 100 * resumen['cantidad_vendida'] / total_unidades if total_unidades > 0 else 0
    
    # Ordenar por cantidad vendida y agregar ranking
    resumen = resumen.sort_values('cantidad_vendida', ascending=False).reset_index(drop=True)
    resumen.insert(0, 'Ranking', range(1, len(resumen) + 1))
    
    # Formatear porcentaje
    resumen['Porcentaje'] = resumen['porcentaje'].apply(lambda x: f"{x:.1f}%")
    
    # Reordenar columnas para mejor presentación
    resumen = resumen[columns_to_include]
    
    return resumen

def client_returns_count(df: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve la cantidad de devoluciones por cliente con porcentaje, nombre del cliente, localidad y ranking.
    Incluye el porcentaje de devoluciones sobre el total de movimientos del cliente.
    """
    # Calcular devoluciones (cantidad negativa)
    devoluciones = df[df['cantidad_vendida'] < 0].copy()
    devoluciones['cantidad_vendida'] = devoluciones['cantidad_vendida'].abs()  # Convertir a positivo para el conteo
    
    if devoluciones.empty:
        columns = ['Ranking', 'cliente', 'cantidad_devoluciones', 'total_vendido', 'Porcentaje devoluciones']
        if 'nombre_cliente' in df.columns:
            columns.insert(2, 'nombre_cliente')
        if 'localidad' in df.columns:
            columns.insert(-3, 'localidad')
        return pd.DataFrame(columns=columns)
    
    # Agrupar devoluciones por cliente
    group_cols_returns = ['cliente']
    agg_dict_returns = {'cantidad_vendida': 'sum'}
    
    if 'nombre_cliente' in devoluciones.columns:
        group_cols_returns.append('nombre_cliente')
        agg_dict_returns['nombre_cliente'] = 'first'
    
    if 'localidad' in devoluciones.columns:
        group_cols_returns.append('localidad')  
        agg_dict_returns['localidad'] = 'first'
    
    returns_by_client = devoluciones.groupby('cliente').agg(agg_dict_returns).reset_index()
    returns_by_client = returns_by_client.rename(columns={'cantidad_vendida': 'cantidad_devoluciones'})
    
    # Calcular total vendido por cliente (solo ventas positivas)
    ventas_positivas = df[df['cantidad_vendida'] > 0]
    group_cols_sales = ['cliente']
    agg_dict_sales = {'cantidad_vendida': 'sum'}
    
    if 'nombre_cliente' in ventas_positivas.columns:
        group_cols_sales.append('nombre_cliente')
        agg_dict_sales['nombre_cliente'] = 'first'
    
    if 'localidad' in ventas_positivas.columns:
        group_cols_sales.append('localidad')
        agg_dict_sales['localidad'] = 'first'
    
    sales_by_client = ventas_positivas.groupby('cliente').agg(agg_dict_sales).reset_index()
    sales_by_client = sales_by_client.rename(columns={'cantidad_vendida': 'total_vendido'})
    
    # Merge para obtener devoluciones y ventas por cliente
    result = returns_by_client.merge(sales_by_client, on='cliente', how='left', suffixes=('', '_y'))
    
    # Limpiar columnas duplicadas del merge
    for col in result.columns:
        if col.endswith('_y'):
            if col.replace('_y', '') in result.columns:
                result = result.drop(columns=[col])
            else:
                result = result.rename(columns={col: col.replace('_y', '')})
    
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
    columns_to_include = ['Ranking', 'cliente']
    if 'nombre_cliente' in result.columns:
        columns_to_include.append('nombre_cliente')
    if 'localidad' in result.columns:
        columns_to_include.append('localidad')
    columns_to_include.extend(['cantidad_devoluciones', 'total_vendido', 'Porcentaje devoluciones'])
    
    result = result[columns_to_include]
    
    return result 