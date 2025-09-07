# functions/domain_cleaning.py
import pandas as pd
import unicodedata

def _norm_text(s: pd.Series) -> pd.Series:
    # quita acentos y baja a minúsculas
    s = s.astype(str)
    s = s.apply(lambda x: unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode("ascii"))
    return s.str.lower()

def apply_domain_cleaning(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # cantidad_vendida > 0
    if "cantidad_vendida" in out.columns:
        out["cantidad_vendida"] = pd.to_numeric(out["cantidad_vendida"], errors="coerce")
        out = out[out["cantidad_vendida"].fillna(0) > 0]

    # excluir 'seña'/'sena' y 'varios' por código o descripción
    mask_excl = pd.Series(False, index=out.index)
    for col in ["codigo_del_articulo", "descripcion_del_producto"]:
        if col in out.columns:
            norm = _norm_text(out[col])
            mask_excl = mask_excl | norm.str.contains("sena") | norm.str.contains("varios")

    out = out[~mask_excl].copy()
    return out
