# utils/loaders.py
import io
import os
import gc
import tempfile
import pandas as pd
import streamlit as st
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from .format import normalize_dataframe

# --- FUNÇÕES AUXILIARES DE CONEXÃO ---

def get_drive_service():
    """Autentica e retorna o serviço do Google Drive."""
    if "gcp_service_account" not in st.secrets or "drive_files" not in st.secrets:
        st.error("❌ Erro: Segredos de configuração (Secrets) não encontrados.")
        return None

    try:
        service_account_info = dict(st.secrets["gcp_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Erro na autenticação do Drive: {e}")
        return None

# --- CARREGAMENTO BASE DE VENDAS (EXCEL) ---

@st.cache_data(ttl=3600, show_spinner="Carregando do Data Lake (Vendas)...")
def fetch_from_drive():
    service = get_drive_service()
    if not service: return None, None

    file_id = st.secrets["drive_files"]["faturamento_xlsx"]
    
    try:
        # Excel geralmente é menor, mantemos em memória (BytesIO) por ser mais rápido para openpyxl
        request = service.files().get_media(fileId=file_id)
        file_io = io.BytesIO()
        downloader = MediaIoBaseDownload(file_io, request)
        
        done = False
        while not done: status, done = downloader.next_chunk()
        file_io.seek(0)
        
        # Leitura
        df_raw = pd.read_excel(file_io, engine="openpyxl")
        df = normalize_dataframe(df_raw)
        
        # Limpeza imediata de memória
        file_io.close()
        del file_io
        gc.collect()

        if df.empty: return None, "Dados Vazios"

        # Data de atualização
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
        print(f"Erro Drive Vendas: {e}")
        return None, None

def load_main_base():
    if "uploaded_dataframe" in st.session_state and st.session_state.uploaded_dataframe is not None:
        return st.session_state.uploaded_dataframe, st.session_state.get("uploaded_timestamp", "Upload Manual")
    return fetch_from_drive()


# --- CARREGAMENTO BASE CROWLEY (PARQUET) ---

@st.cache_data(ttl=3600, show_spinner="Acessando base Crowley...")
def load_crowley_base():
    """
    Usa arquivo temporário em disco para evitar estouro de memória RAM
    durante o download de arquivos grandes (Parquet).
    """
    service = get_drive_service()
    if not service: return None, "Erro Conexão"

    file_id = st.secrets["drive_files"]["crowley_parquet"]

    # Cria arquivo temporário no disco (delete=False para podermos fechar, ler e depois apagar manualmente)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".parquet") as tmp_file:
        temp_filename = tmp_file.name
        
        try:
            # 1. Download Streamado para o Disco (Economiza RAM)
            request = service.files().get_media(fileId=file_id)
            downloader = MediaIoBaseDownload(tmp_file, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            # Garante que os dados foram escritos no disco
            tmp_file.flush()
            tmp_file.close() 

            # 2. Leitura Otimizada do Parquet
            # Selecionamos apenas colunas essenciais se necessário para economizar mais memória
            # Mas o uso do disco já deve resolver o crash principal.
            df = pd.read_parquet(temp_filename)

            # 3. Processamento de Data
            ultima_atualizacao = "N/A"
            if "Data" in df.columns:
                # Converte apenas se necessário e tenta otimizar memória
                df["Data_Dt"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
                max_date = df["Data_Dt"].max()
                if pd.notna(max_date):
                    ultima_atualizacao = max_date.strftime("%d/%m/%Y")

            if ultima_atualizacao == "N/A":
                file_metadata = service.files().get(fileId=file_id, fields="modifiedTime").execute()
                mod_time_str = file_metadata.get("modifiedTime")
                if mod_time_str:
                    mod_dt = datetime.strptime(mod_time_str[:19], "%Y-%m-%dT%H:%M:%S")
                    ultima_atualizacao = mod_dt.strftime("%d/%m/%Y")

            return df, ultima_atualizacao

        except Exception as e:
            st.error(f"Erro ao processar Crowley: {e}")
            return None, "Erro Leitura"
        
        finally:
            # 4. Limpeza Crítica: Apaga o arquivo temporário e libera RAM
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
            gc.collect()
