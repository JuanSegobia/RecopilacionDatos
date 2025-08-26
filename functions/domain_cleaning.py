# functions/domain_cleaning.py
import pandas as pd

def apply_domain_cleaning(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reglas mínimas:
      - mantener columnas artículo, descripción, cantidad (no precios)
      - eliminar filas con cantidad <= 0
      - excluir artículos que contengan 'seña' o 'varios' (case-insensitive)
    """
    if "cantidad_vendida" in df.columns:
        df = df[df["cantidad_vendida"].fillna(0) > 0]

    # Excluir por 'artículo' o 'descripcion' si existiera
    mask_excl = pd.Series(False, index=df.index)
    for col in ["codigo_del_articulo", "descripcion_del_producto"]:
        if col in df.columns:
            mask_excl = mask_excl | df[col].astype(str).str.contains(r"(seña|varios)", case=False, na=False)

    df = df[~mask_excl].copy()
    return df
