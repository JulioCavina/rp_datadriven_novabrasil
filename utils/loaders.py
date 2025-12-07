# utils/loaders.py
import io
import pandas as pd
import streamlit as st
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from .format import normalize_dataframe

# Função genérica de download do Drive (reutilizável)
def _download_file_from_drive(file_id_key):
    """
    Baixa arquivo do Drive retornando BytesIO.
    file_id_key: chave dentro de st.secrets["drive_files"]
    """
    if "gcp_service_account" not in st.secrets or "drive_files" not in st.secrets:
        st.error("❌ Erro: Segredos de configuração (Secrets) não encontrados.")
        return None
        
    try:
        service_account_info = dict(st.secrets["gcp_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        service = build('drive', 'v3', credentials=creds)
        file_id = st.secrets["drive_files"][file_id_key]
        
        request = service.files().get_media(fileId=file_id)
        file_io = io.BytesIO()
        downloader = MediaIoBaseDownload(file_io, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        file_io.seek(0)
        return file_io, service, file_id
    except Exception as e:
        print(f"Erro download Drive ({file_id_key}): {e}")
        return None, None, None

@st.cache_data(ttl=3600, show_spinner="Carregando do Data Lake...")
def fetch_from_drive():
    # ... (código existente da função fetch_from_drive mantido igual) ...
    # Apenas copiei a lógica interna para o helper _download_file_from_drive se quiser refatorar depois,
    # mas para não quebrar o que já funciona, manterei fetch_from_drive como estava ou usando o helper.
    # Vou manter o fetch_from_drive original intacto para segurança e criar o novo load_crowley separado.
    
    # REPETINDO O CÓDIGO ORIGINAL DA FETCH_FROM_DRIVE PARA GARANTIR ESTABILIDADE
    if "gcp_service_account" not in st.secrets or "drive_files" not in st.secrets:
        st.error("❌ Erro: Segredos não encontrados.")
        return None, None

    try:
        service_account_info = dict(st.secrets["gcp_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        service = build('drive', 'v3', credentials=creds)
        file_id = st.secrets["drive_files"]["faturamento_xlsx"]
        request = service.files().get_media(fileId=file_id)
        file_io = io.BytesIO()
        downloader = MediaIoBaseDownload(file_io, request)
        done = False
        while not done: status, done = downloader.next_chunk()
        file_io.seek(0)
        
        df_raw = pd.read_excel(file_io, engine="openpyxl")
        df = normalize_dataframe(df_raw)
        
        if df.empty: return None, "Dados Vazios"

        ultima_atualizacao = "N/A"
        if "data_ref" in df.columns and pd.api.types.is_datetime64_any_dtype(df["data_ref"]):
            max_date = df["data_ref"].max()
            if pd.notna(max_date): ultima_atualizacao = max_date.strftime("%m/%Y")
        
        if ultima_atualizacao == "N/A":
            file_metadata = service.files().get(fileId=file_id, fields="modifiedTime").execute()
            mod_time_str = file_metadata.get("modifiedTime")
            if mod_time_str:
                mod_dt = datetime.strptime(mod_time_str[:19], "%Y-%m-%dT%H:%M:%S")
                ultima_atualizacao = mod_dt.strftime("%d/%m/%Y %H:%M")
            else:
                ultima_atualizacao = datetime.now().strftime("%d/%m/%Y %H:%M")
            
        return df, ultima_atualizacao
    except Exception as e:
        print(f"Erro Drive: {e}")
        return None, None

def load_main_base():
    if "uploaded_dataframe" in st.session_state and st.session_state.uploaded_dataframe is not None:
        return st.session_state.uploaded_dataframe, st.session_state.get("uploaded_timestamp", "Upload Manual")
    return fetch_from_drive()

# --- NOVA FUNÇÃO CROWLEY ---
@st.cache_data(ttl=3600, show_spinner="Acessando base Crowley...")
def load_crowley_base():
    """
    Carrega o arquivo PARQUET do Crowley e retorna DF + Data de Atualização.
    """
    file_io, service, file_id = _download_file_from_drive("crowley_parquet")
    
    if not file_io:
        return None, "Erro Conexão"
        
    try:
        # Lê Parquet
        df = pd.read_parquet(file_io)
        
        # Determina Data
        # Formato esperado: '26/11/2025 12:00:00 AM'
        ultima_atualizacao = "N/A"
        
        if "Data" in df.columns:
            # Converte para datetime
            # O formato misto com AM/PM pode exigir tratamento específico
            df["Data_Dt"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
            
            max_date = df["Data_Dt"].max()
            if pd.notna(max_date):
                ultima_atualizacao = max_date.strftime("%d/%m/%Y")
        
        # Fallback para metadados do arquivo se a coluna falhar
        if ultima_atualizacao == "N/A" and service:
            file_metadata = service.files().get(fileId=file_id, fields="modifiedTime").execute()
            mod_time_str = file_metadata.get("modifiedTime")
            if mod_time_str:
                mod_dt = datetime.strptime(mod_time_str[:19], "%Y-%m-%dT%H:%M:%S")
                ultima_atualizacao = mod_dt.strftime("%d/%m/%Y")

        return df, ultima_atualizacao
        
    except Exception as e:
        st.error(f"Erro ao ler Parquet Crowley: {e}")
        return None, "Erro Leitura"