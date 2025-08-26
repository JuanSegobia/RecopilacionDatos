# services/storage_supabase.py
# ------------------------------------------------------------
# Solo utilidades de STORAGE (Supabase Storage / buckets)
# No maneja tablas ni metadatos (eso está en functions/uploads_service.py)
# ------------------------------------------------------------

from typing import Optional
from supabase import create_client, Client
import streamlit as st

EXCEL_OOXML = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

def _client() -> Client:
    cfg = st.secrets["supabase"]
    return create_client(cfg["url"], cfg["anon_key"])

def upload_to_path(
    file_bytes: bytes,
    storage_key: str,
    content_type: str = EXCEL_OOXML,
    overwrite: bool = False
) -> None:
    """
    Sube un archivo a 'storage_key' dentro del bucket configurado.
    - Si overwrite=True, hace upsert (sobrescribe si ya existe).
    - Si overwrite=False, lanzará 409 si el recurso existe.
    """
    sb = _client()
    bucket = st.secrets["supabase"]["bucket"]

    options = {"contentType": content_type}
    if overwrite:
        options["upsert"] = "true"  # sobrescribe si existe

    try:
        sb.storage.from_(bucket).upload(storage_key, file_bytes, options)
    except Exception as e:
        # Fallback defensivo si el cliente no respetara 'upsert'
        if overwrite and any(x in str(e).lower() for x in ["409", "duplicate", "already exists"]):
            sb.storage.from_(bucket).update(storage_key, file_bytes, options)
        else:
            raise

def download_excel(storage_key: str) -> bytes:
    """Descarga el objeto y devuelve los bytes."""
    sb = _client()
    bucket = st.secrets["supabase"]["bucket"]
    return sb.storage.from_(bucket).download(storage_key)

def signed_url(storage_key: str, expires_in: int = 3600) -> Optional[str]:
    """Devuelve una URL firmada temporal para compartir/descargar."""
    sb = _client()
    bucket = st.secrets["supabase"]["bucket"]
    res = sb.storage.from_(bucket).create_signed_url(storage_key, expires_in)
    return res.get("signedURL")

def delete_object(storage_key: str) -> None:
    """Borra un objeto del bucket (útil si implementás 'revert' o limpieza)."""
    sb = _client()
    bucket = st.secrets["supabase"]["bucket"]
    sb.storage.from_(bucket).remove(storage_key)
