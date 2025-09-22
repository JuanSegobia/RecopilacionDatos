# services/storage_supabase.py
import uuid, io
from typing import List, Dict, Any, Optional
import streamlit as st
from supabase import create_client, Client


def _client() -> Optional[Client]:
    try:
        cfg = st.secrets.get("supabase", {})
        url = cfg.get("url")
        key = cfg.get("anon_key")
        if not url or not key or not isinstance(url, str) or not url.startswith("http"):
            return None
        return create_client(url, key)
    except Exception:
        return None


def _bucket_name() -> Optional[str]:
    try:
        cfg = st.secrets.get("supabase", {})
        bucket = cfg.get("bucket")
        return bucket if isinstance(bucket, str) and bucket else None
    except Exception:
        return None


def upload_excel(file_bytes: bytes, original_name: str) -> Optional[str]:
    """Sube el binario al bucket y devuelve storage_key único, o None si falla."""
    sb = _client()
    bucket = _bucket_name()
    if sb is None or bucket is None:
        return None
    try:
        key = f"{uuid.uuid4()}.xlsx"
        sb.storage.from_(bucket).upload(
            key,
            file_bytes,
            {"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
        )
        return key
    except Exception:
        return None


def download_excel(storage_key: str) -> Optional[bytes]:
    sb = _client()
    bucket = _bucket_name()
    if sb is None or bucket is None:
        return None
    try:
        return sb.storage.from_(bucket).download(storage_key)
    except Exception:
        return None


def signed_url(storage_key: str, expires_in: int = 3600) -> Optional[str]:
    sb = _client()
    bucket = _bucket_name()
    if sb is None or bucket is None:
        return None
    try:
        res = sb.storage.from_(bucket).create_signed_url(storage_key, expires_in)
        return res.get("signedURL") if isinstance(res, dict) else None
    except Exception:
        return None


def insert_meta(file_type: str, original_name: str, storage_key: str) -> bool:
    sb = _client()
    if sb is None:
        return False
    try:
        sb.table("files").insert({
            "file_type": file_type,
            "original_name": original_name,
            "storage_key": storage_key
        }).execute()
        return True
    except Exception:
        return False


def list_files(file_type: Optional[str] = None) -> List[Dict[str, Any]]:
    sb = _client()
    if sb is None:
        return []
    try:
        q = sb.table("files").select("*").order("uploaded_at", desc=True)
        if file_type:
            q = q.eq("file_type", file_type)
        data = q.execute().data
        return data or []
    except Exception:
        return []
