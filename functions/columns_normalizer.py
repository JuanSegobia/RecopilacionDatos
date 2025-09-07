# functions/columns_normalizer.py
import re, unicodedata
import pandas as pd

def _norm_key(s: str) -> str:
    # lower + sin tildes + espacios/puntuación -> underscores
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [_norm_key(str(c)) for c in df.columns]
    return df
