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
    name_lower = str(key).lower()
    try:
        if name_lower.endswith('.xlsx'):
            df = pd.read_excel(bio, engine='openpyxl')
        else:
            try:
                df = pd.read_excel(bio, engine='xlrd')
            except ImportError:
                # Intentar calamine como alternativa universal
                bio.seek(0)
                try:
                    df = pd.read_excel(bio, engine='calamine')
                except Exception:
                    st.error("No se pudo leer .xls: falta 'xlrd==1.2.0' y falló engine 'calamine'. Convertí a .xlsx.")
                    raise
    except Exception:
        # Fallback cruzado por si la extensión engaña
        bio.seek(0)
        try:
            df = pd.read_excel(bio, engine='openpyxl')
        except Exception:
            bio.seek(0)
            try:
                df = pd.read_excel(bio, engine='xlrd')
            except Exception:
                bio.seek(0)
                df = pd.read_excel(bio, engine='calamine')
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
        name_lower = uploaded_file.name.lower()
        try:
            if name_lower.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file, engine='openpyxl')
            else:
                # .xls u otros: intentar xlrd; si no está instalado, intentar calamine
                try:
                    df = pd.read_excel(uploaded_file, engine='xlrd')
                except ImportError:
                    uploaded_file.seek(0)
                    try:
                        df = pd.read_excel(uploaded_file, engine='calamine')
                    except Exception:
                        st.error("No se pudo leer .xls: falta 'xlrd==1.2.0' y falló engine 'calamine'. Convertí a .xlsx.")
                        raise
        except Exception:
            # fallback cruzado: intentar el otro engine por si la extensión engaña
            uploaded_file.seek(0)
            try:
                df = pd.read_excel(uploaded_file, engine='openpyxl')
            except Exception:
                uploaded_file.seek(0)
                try:
                    df = pd.read_excel(uploaded_file, engine='xlrd')
                except Exception:
                    uploaded_file.seek(0)
                    df = pd.read_excel(uploaded_file, engine='calamine')
        return self._parse_by_format(df, getattr(uploaded_file, 'name', None))

    def load_from_supabase_bytes(self, original_name: str, content: bytes) -> pd.DataFrame:
        df = _cache_df(original_name, content)
        return self._parse_by_format(df, original_name)
