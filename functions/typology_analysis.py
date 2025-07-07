import pandas as pd

typology_dict = {
    '0': 'accesorios',
    '1': 'pantalon babucha calza',
    '2': 'capri, pescador',
    '3': 'short pollera vestido',
    '4': 'remera, polera',
    '5': 'musculosa, remera s/m',
    '6': 'buzo, chaleco s/cierre',
    '7': 'campera, chaleco c/cierre',
    '8': 'camisas',
    '9': 'mallas'
}

def add_typology_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Añade una columna 'tipologia' deducida del código del artículo.
    """
    df['tipologia'] = df['codigo_del_articulo'].astype(str).str[3].map(typology_dict)
    return df

def top_selling_typologies(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    Devuelve las n tipologías más vendidas.
    """
    if 'tipologia' not in df.columns:
        df = add_typology_column(df)
    result = df.groupby('tipologia')['cantidad_vendida'].sum().reset_index()
    return result.sort_values('cantidad_vendida', ascending=False).head(n) 