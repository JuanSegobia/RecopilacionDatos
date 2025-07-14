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

genero_dict = {
    '0': 'accesorio',
    '1': 'femenino',
    '2': 'masculino',
    '3': 'niños'
}

def add_typology_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Añade columnas 'tipologia', 'genero', 'categoria_especial' y 'cuenta_ventas' 
    deducidas del código del artículo según las reglas de negocio.
    """
    df = df.copy()
    df['codigo_del_articulo'] = df['codigo_del_articulo'].astype(str).str.upper()
    
    # Inicializar columnas
    df['tipologia'] = 'desconocido'
    df['genero'] = 'desconocido'
    df['categoria_especial'] = 'ventas_normales'  # ventas_normales, cierre, ch, sorteo, perfuminas, otros_codigos
    df['cuenta_ventas'] = True  # Si cuenta para el total de unidades vendidas
    
    def classify_article(codigo):
        if pd.isna(codigo) or codigo == 'nan' or str(codigo).strip() == '':
            return 'desconocido', 'desconocido', 'ventas_normales', True
            
        codigo_str = str(codigo).strip().upper()
        
        # Casos especiales - códigos exactos
        if codigo_str == "CIERRE":
            return 'cierre', 'desconocido', 'cierre', False
        elif codigo_str == "SORTEO":
            return 'sorteo', 'desconocido', 'sorteo', False
        elif codigo_str in ["9310", "9309"]:
            return 'perfuminas', 'desconocido', 'perfuminas', False
        elif codigo_str == "710091":
            return 'accesorios', 'desconocido', 'ventas_normales', True
        
        # Si comienza con letra
        if codigo_str[0].isalpha():
            # Códigos que empiezan con "CH"
            if codigo_str.startswith("CH"):
                return 'ch', 'desconocido', 'ch', False
            
            # Códigos que empiezan con "B" (básicos)
            elif codigo_str.startswith("B") and len(codigo_str) >= 3:
                # B + género + tipología
                if len(codigo_str) >= 3:
                    genero_code = codigo_str[1] if len(codigo_str) > 1 else '0'
                    tipologia_code = codigo_str[2] if len(codigo_str) > 2 else '0'
                    
                    genero = genero_dict.get(genero_code, 'desconocido')
                    tipologia = typology_dict.get(tipologia_code, 'desconocido')
                    
                    return tipologia, genero, 'ventas_normales', True
                else:
                    return 'basicos', 'desconocido', 'ventas_normales', True
            
            # Otros códigos que empiezan con letra
            else:
                return 'otros_codigos', 'desconocido', 'otros_codigos', False
        
        # Si comienza con número
        elif codigo_str[0].isdigit():
            # Códigos de 7 caracteres: temporada(2) + género(1) + tipología(1) + ...
            if len(codigo_str) == 7:
                genero_code = codigo_str[2] if len(codigo_str) > 2 else '0'
                tipologia_code = codigo_str[3] if len(codigo_str) > 3 else '0'
                
                genero = genero_dict.get(genero_code, 'desconocido')
                tipologia = typology_dict.get(tipologia_code, 'desconocido')
                
                return tipologia, genero, 'ventas_normales', True
            
            # Otros códigos numéricos - usar lógica original (4to carácter para tipología)
            elif len(codigo_str) >= 4:
                tipologia_code = codigo_str[3]
                tipologia = typology_dict.get(tipologia_code, 'desconocido')
                return tipologia, 'desconocido', 'ventas_normales', True
            
            else:
                return 'desconocido', 'desconocido', 'ventas_normales', True
        
        return 'desconocido', 'desconocido', 'ventas_normales', True
    
    # Aplicar la clasificación
    clasificaciones = df['codigo_del_articulo'].apply(classify_article)
    df['tipologia'] = clasificaciones.apply(lambda x: x[0])
    df['genero'] = clasificaciones.apply(lambda x: x[1])
    df['categoria_especial'] = clasificaciones.apply(lambda x: x[2])
    df['cuenta_ventas'] = clasificaciones.apply(lambda x: x[3])
    
    return df

def top_selling_typologies(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    Devuelve las n tipologías más vendidas (solo cuenta ventas normales).
    """
    if 'tipologia' not in df.columns:
        df = add_typology_column(df)
    
    # Filtrar solo las ventas que cuentan
    df_ventas = df[df['cuenta_ventas'] == True]
    result = df_ventas.groupby('tipologia')['cantidad_vendida'].sum().reset_index()
    return result.sort_values('cantidad_vendida', ascending=False).head(n)

def get_special_categories_summary(df: pd.DataFrame) -> dict:
    """
    Devuelve un resumen de todas las categorías especiales.
    """
    if 'categoria_especial' not in df.columns:
        df = add_typology_column(df)
    
    summary = {}
    
    # Cierres
    cierres = df[df['categoria_especial'] == 'cierre']
    summary['cierres'] = {
        'cantidad': len(cierres),
        'unidades': cierres['cantidad_vendida'].sum(),
        'detalle': cierres.groupby('codigo_del_articulo')['cantidad_vendida'].sum().reset_index()
    }
    
    # CH
    ch_items = df[df['categoria_especial'] == 'ch']
    summary['ch'] = {
        'cantidad': len(ch_items),
        'unidades': ch_items['cantidad_vendida'].sum(),
        'detalle': ch_items.groupby(['codigo_del_articulo', 'descripcion_del_producto'])['cantidad_vendida'].sum().reset_index()
    }
    
    # Sorteos
    sorteos = df[df['categoria_especial'] == 'sorteo']
    summary['sorteos'] = {
        'cantidad': len(sorteos),
        'unidades': sorteos['cantidad_vendida'].sum(),
        'detalle': sorteos.groupby('codigo_del_articulo')['cantidad_vendida'].sum().reset_index()
    }
    
    # Perfuminas
    perfuminas = df[df['categoria_especial'] == 'perfuminas']
    summary['perfuminas'] = {
        'cantidad': len(perfuminas),
        'unidades': perfuminas['cantidad_vendida'].sum(),
        'detalle': perfuminas.groupby('codigo_del_articulo')['cantidad_vendida'].sum().reset_index()
    }
    
    # Otros códigos
    otros = df[df['categoria_especial'] == 'otros_codigos']
    summary['otros_codigos'] = {
        'cantidad': len(otros),
        'unidades': otros['cantidad_vendida'].sum(),
        'detalle': otros.groupby(['codigo_del_articulo', 'descripcion_del_producto'])['cantidad_vendida'].sum().reset_index()
    }
    
    return summary

def get_sales_by_gender(df: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve las ventas agrupadas por género (solo ventas normales).
    """
    if 'genero' not in df.columns:
        df = add_typology_column(df)
    
    # Filtrar solo las ventas que cuentan
    df_ventas = df[df['cuenta_ventas'] == True]
    result = df_ventas.groupby('genero')['cantidad_vendida'].sum().reset_index()
    return result.sort_values('cantidad_vendida', ascending=False) 