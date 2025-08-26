# functions/uploads_service.py
import re
import io
import hashlib
import unicodedata
from datetime import date
from typing import Optional, Dict, Any, List

import streamlit as st
from supabase import create_client, Client

LOCAL_CODES = {"centenario", "5", "49", "55"}

RE_GLOBAL = re.compile(r"^temporada_(\d{4})-(\d{2})\.(xlsx|xls)$", re.IGNORECASE)
RE_LOCAL  = re.compile(r"^local-(centenario|5|49|55)_(\d{4})-(\d{2})\.(xlsx|xls)$", re.IGNORECASE)

def _sb() -> Client:
    cfg = st.secrets["supabase"]
    return create_client(cfg["url"], cfg["anon_key"])

def _slugify_filename(name: str) -> str:
    # Quedarnos con ASCII básico, guiones bajos, puntos
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    ascii_str = ascii_str.replace(" ", "_")
    # Evitar barras u otros separadores
    return re.sub(r"[^A-Za-z0-9._-]", "", ascii_str)

def parse_filename(original_name: str) -> Dict[str, Any]:
    """
    Valida el nombre por convención y extrae:
      scope: 'global'|'local'
      file_type: 'temporada'|'locales'
      local_code: None|{centenario,5,49,55}
      period_month: date (día 1)
      period_str: 'YYYY-MM'
    Lanza ValueError con mensaje amigable si no matchea.
    """
    m = RE_GLOBAL.match(original_name)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        return {
            "scope": "global",
            "file_type": "temporada",
            "local_code": None,
            "period_month": date(year, month, 1),
            "period_str": f"{year:04d}-{month:02d}"
        }

    m = RE_LOCAL.match(original_name)
    if m:
        local_code = m.group(1).lower()
        year, month = int(m.group(2)), int(m.group(3))
        return {
            "scope": "local",
            "file_type": "locales",
            "local_code": local_code,
            "period_month": date(year, month, 1),
            "period_str": f"{year:04d}-{month:02d}"
        }

    raise ValueError(
        "Nombre de archivo inválido. Usá una de estas convenciones:\n"
        "  • Global (temporada): temporada_YYYY-MM.xlsx  (ej.: temporada_2025-06.xlsx)\n"
        "  • Por local (locales): local-<centenario|5|49|55>_YYYY-MM.xlsx  (ej.: local-49_2025-06.xlsx)"
    )

def compute_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()

def build_storage_path(scope: str, local_code: Optional[str], period_month: date, original_name: str) -> str:
    year = period_month.year
    ym = f"{period_month.year:04d}-{period_month.month:02d}"
    safe_name = _slugify_filename(original_name)
    if scope == "global":
        return f"sales/global/{year}/{ym}/{safe_name}"
    else:
        return f"sales/local/{local_code}/{year}/{ym}/{safe_name}"

def check_duplicate(file_type: str, period_month: date, local_code: Optional[str]) -> Optional[Dict[str, Any]]:
    sb = _sb()
    q = sb.table("uploads").select("*").eq("file_type", file_type).eq("period_month", period_month.isoformat())
    if local_code is None:
        q = q.is_("local_code", None)
    else:
        q = q.eq("local_code", local_code)
    data = q.execute().data
    return data[0] if data else None

def insert_upload_metadata(file_type: str, scope: str, local_code: Optional[str], period_month: date,
                           format_name: str, original_name: str, storage_key: str,
                           sha256: Optional[str], status: Optional[str] = "processed",
                           source: Optional[str] = "upload", supersedes_upload_id: Optional[str] = None) -> Dict[str, Any]:
    sb = _sb()
    payload = {
        "file_type": file_type,
        "scope": scope,
        "local_code": local_code,
        "period_month": period_month.isoformat(),
        "format_name": format_name,
        "original_name": original_name,
        "storage_key": storage_key,
        "sha256": sha256,
        "status": status,
        "source": source,
        "supersedes_upload_id": supersedes_upload_id
    }
    return sb.table("uploads").insert(payload).execute().data[0]

def update_upload_metadata(upload_id: str, **fields) -> Dict[str, Any]:
    sb = _sb()
    return sb.table("uploads").update(fields).eq("id", upload_id).execute().data[0]

def list_uploads(scope: Optional[str] = None, local_code: Optional[str] = None,
                 year: Optional[int] = None, month: Optional[int] = None,
                 file_type: Optional[str] = None) -> List[Dict[str, Any]]:
    sb = _sb()
    q = sb.table("uploads").select("*").order("uploaded_at", desc=True)
    if scope: q = q.eq("scope", scope)
    if local_code is not None: q = q.eq("local_code", local_code)
    if file_type: q = q.eq("file_type", file_type)
    if year and month:
        period = date(year, month, 1).isoformat()
        q = q.eq("period_month", period)
    return q.execute().data

def get_upload_by_context(file_type: str, period_month: date, local_code: Optional[str]) -> Optional[Dict[str, Any]]:
    return check_duplicate(file_type, period_month, local_code)
