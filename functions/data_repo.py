import io
import pandas as pd
import streamlit as st
from utils.format_detect import detect_format, detect_format_smart
from functions.parsers.temporada import parse_temporada
from functions.parsers.locales import parse_locales
from functions.parsers.articulos_mes import parse_articulos_mes
from functions.schemas import canonicalize

@st.cache_data(show_spinner=False)
def _cache_df(key: str, content: bytes) -> pd.DataFrame:
    bio = io.BytesIO(content)
    # Intentar leer Excel
    try:
        df = pd.read_excel(bio, engine='openpyxl')
    except Exception:
        bio.seek(0)
        df = pd.read_excel(bio, engine='xlrd')
    return df

class DataRepository:
    def __init__(self):
        pass

    def _parse_by_format(self, df: pd.DataFrame, filename: str | None = None) -> pd.DataFrame:
        fmt = detect_format_smart(df, filename)
        if fmt == 'temporada':
            return parse_temporada(df)
        if fmt == 'articulos_mes':
            return parse_articulos_mes(df)
        if fmt == 'locales' or fmt.startswith('locales:'):
            return parse_locales(df)
        # fallback: canonical base
        df, missing = canonicalize(df)
        if missing:
            raise ValueError(f"Formato desconocido. Columnas faltantes: {missing}")
        df['cuenta_ventas'] = True
        return df

    def load_from_upload(self, uploaded_file) -> pd.DataFrame:
        # leer con pandas directo (streamlit UploadedFile)
        df = pd.read_excel(uploaded_file, engine='openpyxl') if uploaded_file.name.lower().endswith('.xlsx') else pd.read_excel(uploaded_file, engine='xlrd')
        return self._parse_by_format(df, getattr(uploaded_file, 'name', None))

    def load_from_supabase_bytes(self, original_name: str, content: bytes) -> pd.DataFrame:
        df = _cache_df(original_name, content)
        return self._parse_by_format(df, original_name)
