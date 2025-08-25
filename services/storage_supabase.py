# services/storage_supabase.py
import uuid, io
from typing import List, Dict, Any, Optional
import streamlit as st
from supabase import create_client, Client

def _client() -> Client:
    cfg = st.secrets["supabase"]
    return create_client(cfg["url"], cfg["anon_key"])

def upload_excel(file_bytes: bytes, original_name: str) -> str:
    """Sube el binario al bucket y devuelve storage_key único."""
    sb = _client()
    bucket = st.secrets["supabase"]["bucket"]
    key = f"{uuid.uuid4()}.xlsx"
    # content-type de Excel OOXML
    sb.storage.from_(bucket).upload(key, file_bytes, {"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"})
    return key

def download_excel(storage_key: str) -> bytes:
    sb = _client()
    bucket = st.secrets["supabase"]["bucket"]
    return sb.storage.from_(bucket).download(storage_key)

def signed_url(storage_key: str, expires_in: int = 3600) -> str:
    sb = _client()
    bucket = st.secrets["supabase"]["bucket"]
    res = sb.storage.from_(bucket).create_signed_url(storage_key, expires_in)
    return res.get("signedURL")

def insert_meta(file_type: str, original_name: str, storage_key: str):
    sb = _client()
    sb.table("files").insert({
        "file_type": file_type,
        "original_name": original_name,
        "storage_key": storage_key
    }).execute()

def list_files(file_type: Optional[str] = None) -> List[Dict[str, Any]]:
    sb = _client()
    q = sb.table("files").select("*").order("uploaded_at", desc=True)
    if file_type:
        q = q.eq("file_type", file_type)
    return q.execute().data
