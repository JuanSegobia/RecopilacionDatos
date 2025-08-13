# google_drive.py
import streamlit as st
import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials


# Scopes necesarios
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def get_drive_credentials():
    try:
        # 1) Preferir tabla TOML (recomendada)
        if "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            # Mover GDRIVE_FOLDER_ID fuera si está mezclado
            info.pop("GDRIVE_FOLDER_ID", None)
            return Credentials.from_service_account_info(info, scopes=SCOPES)

        # 2) Compatibilidad con string JSON previo
        if "GOOGLE_CREDENTIALS" in st.secrets:
            creds_str = st.secrets["GOOGLE_CREDENTIALS"]
            info = json.loads(creds_str)  # aquí requiere \n escapados en private_key
            return Credentials.from_service_account_info(info, scopes=SCOPES)

        # 3) Fallback por archivo
        path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if path and os.path.exists(path):
            return Credentials.from_service_account_file(path, scopes=SCOPES)

        raise RuntimeError("No se encontraron credenciales.")
    except Exception as e:
        st.error(f"❌ Error obteniendo credenciales: {e}")
        return None

def upload_to_drive(file_content, filename, credentials, folder_id=None):
    try:
        if not credentials:
            raise RuntimeError("Credenciales inválidas o ausentes.")

        # Folder desde secrets si no se pasa
        if folder_id is None:
            folder_id = st.secrets.get("GDRIVE_FOLDER_ID")

        service = build('drive', 'v3', credentials=credentials)

        file_metadata = {"name": filename}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        if filename.lower().endswith(".xlsx"):
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif filename.lower().endswith(".xls"):
            mimetype = "application/vnd.ms-excel"
        else:
            mimetype = "application/octet-stream"

        media = MediaIoBaseUpload(file_content, mimetype=mimetype)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, createdTime, webViewLink"
        ).execute()

        return file
    except Exception as e:
        st.error(f"❌ Error subiendo a Drive: {str(e)}")
        return None
