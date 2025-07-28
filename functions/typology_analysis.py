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
    if df.empty:
        # Crear estructura vacía si no hay datos
        empty_summary = {
            'cierres': {'cantidad': 0, 'unidades': 0, 'detalle': pd.DataFrame()},
            'ch': {'cantidad': 0, 'unidades': 0, 'detalle': pd.DataFrame()},
            'sorteos': {'cantidad': 0, 'unidades': 0, 'detalle': pd.DataFrame()},
            'perfuminas': {'cantidad': 0, 'unidades': 0, 'detalle': pd.DataFrame()},
            'otros_codigos': {'cantidad': 0, 'unidades': 0, 'detalle': pd.DataFrame()}
        }
        return empty_summary
    
    if 'categoria_especial' not in df.columns:
        df = add_typology_column(df)
    
    summary = {}
    
    # Cierres
    cierres = df[df['categoria_especial'] == 'cierre']
    if not cierres.empty:
        detalle_cierres = cierres.groupby('codigo_del_articulo')['cantidad_vendida'].sum().reset_index()
    else:
        detalle_cierres = pd.DataFrame(columns=['codigo_del_articulo', 'cantidad_vendida'])
    
    summary['cierres'] = {
        'cantidad': len(cierres),
        'unidades': cierres['cantidad_vendida'].sum() if not cierres.empty else 0,
        'detalle': detalle_cierres
    }
    
    # CH
    ch_items = df[df['categoria_especial'] == 'ch']
    if not ch_items.empty:
        detalle_ch = ch_items.groupby(['codigo_del_articulo', 'descripcion_del_producto'])['cantidad_vendida'].sum().reset_index()
    else:
        detalle_ch = pd.DataFrame(columns=['codigo_del_articulo', 'descripcion_del_producto', 'cantidad_vendida'])
    
    summary['ch'] = {
        'cantidad': len(ch_items),
        'unidades': ch_items['cantidad_vendida'].sum() if not ch_items.empty else 0,
        'detalle': detalle_ch
    }
    
    # Sorteos
    sorteos = df[df['categoria_especial'] == 'sorteo']
    if not sorteos.empty:
        detalle_sorteos = sorteos.groupby('codigo_del_articulo')['cantidad_vendida'].sum().reset_index()
    else:
        detalle_sorteos = pd.DataFrame(columns=['codigo_del_articulo', 'cantidad_vendida'])
    
    summary['sorteos'] = {
        'cantidad': len(sorteos),
        'unidades': sorteos['cantidad_vendida'].sum() if not sorteos.empty else 0,
        'detalle': detalle_sorteos
    }
    
    # Perfuminas
    perfuminas = df[df['categoria_especial'] == 'perfuminas']
    if not perfuminas.empty:
        detalle_perfuminas = perfuminas.groupby('codigo_del_articulo')['cantidad_vendida'].sum().reset_index()
    else:
        detalle_perfuminas = pd.DataFrame(columns=['codigo_del_articulo', 'cantidad_vendida'])
    
    summary['perfuminas'] = {
        'cantidad': len(perfuminas),
        'unidades': perfuminas['cantidad_vendida'].sum() if not perfuminas.empty else 0,
        'detalle': detalle_perfuminas
    }
    
    # Otros códigos
    otros = df[df['categoria_especial'] == 'otros_codigos']
    if not otros.empty:
        detalle_otros = otros.groupby(['codigo_del_articulo', 'descripcion_del_producto'])['cantidad_vendida'].sum().reset_index()
    else:
        detalle_otros = pd.DataFrame(columns=['codigo_del_articulo', 'descripcion_del_producto', 'cantidad_vendida'])
    
    summary['otros_codigos'] = {
        'cantidad': len(otros),
        'unidades': otros['cantidad_vendida'].sum() if not otros.empty else 0,
        'detalle': detalle_otros
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