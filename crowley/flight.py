# crowley/flight.py
import streamlit as st
import pandas as pd
import numpy as np
import io
import math
import json
from datetime import datetime
import calendar

def render(df_crowley, cookies, data_atualizacao):
    # --- CONFIGURAÇÃO VISUAL ---
    pd.set_option("styler.render.max_elements", 5_000_000)
    
    st.markdown("""
        <style>
        /* Tabela Compacta */
        [data-testid="stDataFrame"] th {
            text-align: center !important;
            vertical-align: middle !important;
            font-size: 0.75rem !important;
            padding: 4px !important;
            white-space: nowrap !important;
        }
        [data-testid="stDataFrame"] td {
            text-align: center !important;
            vertical-align: middle !important;
            font-size: 0.75rem !important;
            padding: 4px !important;
        }
        /* Coluna Anunciante (1ª coluna) alinhada à esquerda */
        [data-testid="stDataFrame"] td:nth-child(1) {
            text-align: left !important;
            font-weight: bold;
            min-width: 200px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- Header ---
    if st.button("Voltar", key="btn_voltar_flight"):
        st.query_params["view"] = "menu"
        st.session_state.pop("flight_search_trigger", None)
        st.session_state.pop("flight_page_idx", None)
        st.rerun()

    st.markdown('<div class="page-title-centered">Relatório Flight (Mapa de Inserções)</div>', unsafe_allow_html=True)

    # Validação
    if df_crowley is None or df_crowley.empty:
        st.error("Base de dados não carregada.")
        st.stop()

    if "Data_Dt" not in df_crowley.columns:
        if "Data" in df_crowley.columns:
            df_crowley["Data_Dt"] = pd.to_datetime(df_crowley["Data"], dayfirst=True, errors="coerce")
        else:
            st.error("Coluna de Data não encontrada na base.")
            st.stop()

    # Colunas Auxiliares
    df_crowley["Ano"] = df_crowley["Data_Dt"].dt.year
    df_crowley["Mes"] = df_crowley["Data_Dt"].dt.month
    df_crowley["Dia"] = df_crowley["Data_Dt"].dt.day

    # --- COOKIES (PERSISTÊNCIA DE FILTROS) ---
    saved_filters = {}
    cookie_val = cookies.get("crowley_filters_flight")
    if cookie_val:
        try:
            saved_filters = json.loads(cookie_val)
        except:
            pass

    # Função auxiliar para pegar valor salvo ou default
    def get_cookie_val(key, default=None):
        return saved_filters.get(key, default)

    # --- CONTROLE DE PAGINAÇÃO ---
    if "flight_page_idx" not in st.session_state:
        st.session_state.flight_page_idx = 0

    def reset_pagination():
        st.session_state.flight_page_idx = 0

    # --- FILTROS ---
    st.markdown("##### Configuração do Mapa")
    
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        
        # 1. Ano
        lista_anos = sorted(df_crowley["Ano"].dropna().unique(), reverse=True)
        default_ano = get_cookie_val("ano")
        idx_ano = lista_anos.index(default_ano) if default_ano in lista_anos else 0
        
        with c1:
            sel_ano = st.selectbox("1. Ano (*)", options=lista_anos, index=idx_ano, key="flight_ano", on_change=reset_pagination)
            
        df_ano = df_crowley[df_crowley["Ano"] == sel_ano]
        
        # 2. Mês
        lista_meses_num = sorted(df_ano["Mes"].dropna().unique())
        mes_map = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
            7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }
        lista_meses_fmt = [(m, mes_map.get(m, str(m))) for m in lista_meses_num]
        
        # Tenta recuperar mês salvo
        saved_mes = get_cookie_val("mes")
        idx_mes = 0
        if saved_mes:
            for i, (m_num, _) in enumerate(lista_meses_fmt):
                if m_num == saved_mes:
                    idx_mes = i
                    break
        
        with c2:
            sel_mes_tuple = st.selectbox(
                "2. Mês (*)", 
                options=lista_meses_fmt, 
                index=idx_mes,
                format_func=lambda x: x[1], 
                key="flight_mes",
                on_change=reset_pagination
            )
            sel_mes = sel_mes_tuple[0] if sel_mes_tuple else None

        # 3. Dia
        if sel_ano and sel_mes:
            _, last_day = calendar.monthrange(int(sel_ano), int(sel_mes))
            lista_dias = list(range(1, last_day + 1))
        else:
            lista_dias = []
            
        saved_dias = get_cookie_val("dias", [])
        valid_dias = [d for d in saved_dias if d in lista_dias]
        
        with c3:
            sel_dias = st.multiselect("3. Dias (Opcional)", options=lista_dias, default=valid_dias, placeholder="Todo o mês", key="flight_dias", on_change=reset_pagination)

        if sel_ano and sel_mes:
            df_temp = df_ano[df_ano["Mes"] == sel_mes]
        else:
            df_temp = pd.DataFrame()

        c4, c5, c6 = st.columns(3)
        
        # 4. Praça
        lista_pracas = sorted(df_temp["Praca"].dropna().unique()) if not df_temp.empty else []
        saved_praca = get_cookie_val("praca")
        idx_praca = lista_pracas.index(saved_praca) if saved_praca in lista_pracas else 0
        
        with c4:
            sel_praca = st.selectbox("4. Praça (*)", options=lista_pracas, index=idx_praca, key="flight_praca", on_change=reset_pagination)
            
        # 5. Veículo
        df_praca = df_temp[df_temp["Praca"] == sel_praca] if not df_temp.empty else pd.DataFrame()
        lista_veiculos = sorted(df_praca["Emissora"].dropna().unique())
        saved_veiculo = get_cookie_val("veiculo")
        idx_veiculo = lista_veiculos.index(saved_veiculo) if saved_veiculo in lista_veiculos else 0
        
        with c5:
            sel_veiculo = st.selectbox("5. Veículo (*)", options=lista_veiculos, index=idx_veiculo, key="flight_veiculo", on_change=reset_pagination)
            
        # 6. Anunciante
        df_veic = df_praca[df_praca["Emissora"] == sel_veiculo] if not df_praca.empty else pd.DataFrame()
        lista_anunciantes = sorted(df_veic["Anunciante"].dropna().unique())
        saved_anunciantes = get_cookie_val("anunciantes", [])
        valid_anunciantes = [a for a in saved_anunciantes if a in lista_anunciantes]
        
        with c6:
            sel_anunciantes = st.multiselect("6. Anunciantes (Opcional)", options=lista_anunciantes, default=valid_anunciantes, placeholder="Todos", key="flight_anunciantes", on_change=reset_pagination)

        st.markdown("<br>", unsafe_allow_html=True)
        btn_gerar = st.button("Gerar Mapa Flight", type="primary", use_container_width=True)

    if btn_gerar:
        st.session_state["flight_search_trigger"] = True
        reset_pagination()
        
        # Salva cookies
        new_cookie = {
            "ano": int(sel_ano) if sel_ano else None,
            "mes": int(sel_mes) if sel_mes else None,
            "dias": sel_dias,
            "praca": sel_praca,
            "veiculo": sel_veiculo,
            "anunciantes": sel_anunciantes
        }
        cookies["crowley_filters_flight"] = json.dumps(new_cookie)
        cookies.save()

    # --- PROCESSAMENTO ---
    if st.session_state.get("flight_search_trigger") and sel_ano and sel_mes and sel_praca and sel_veiculo:
        
        mask = (
            (df_crowley["Ano"] == sel_ano) &
            (df_crowley["Mes"] == sel_mes) &
            (df_crowley["Praca"] == sel_praca) &
            (df_crowley["Emissora"] == sel_veiculo)
        )
        if sel_anunciantes:
            mask = mask & (df_crowley["Anunciante"].isin(sel_anunciantes))
        if sel_dias:
            mask = mask & (df_crowley["Dia"].isin(sel_dias))
            
        df_final = df_crowley[mask].copy()
        
        if df_final.empty:
            st.warning("Nenhuma inserção encontrada.")
            return

        val_col = "Volume de Insercoes" if "Volume de Insercoes" in df_final.columns else "Contagem"
        if val_col == "Contagem": df_final["Contagem"] = 1

        # Pivot Table
        # Fix: observed=True para silenciar warning do pandas
        pivot = pd.pivot_table(
            df_final, 
            index="Anunciante", 
            columns="Dia", 
            values=val_col, 
            aggfunc="sum", 
            fill_value=0,
            observed=True
        )
        
        # Garante colunas de dias
        if sel_dias:
            days_range = sorted(sel_dias)
        else:
            _, last_day = calendar.monthrange(int(sel_ano), int(sel_mes))
            days_range = list(range(1, last_day + 1))
            
        pivot = pivot.reindex(columns=days_range, fill_value=0)
        
        # Calcula Total por Linha e Remove Zerados
        pivot["TOTAL"] = pivot.sum(axis=1)
        pivot = pivot[pivot["TOTAL"] > 0]
        
        if pivot.empty:
            st.warning("Nenhum anunciante com inserções neste período.")
            return

        # Ordenação
        pivot = pivot.sort_values("TOTAL", ascending=False)
        
        # --- CÁLCULO DA LINHA TOTALIZADORA (TOTAL DIÁRIO) ---
        # Soma as colunas (dias) e a coluna TOTAL
        daily_totals = pivot.sum(numeric_only=True)
        # Cria um DataFrame de uma linha para o total
        total_row_df = pd.DataFrame(daily_totals).T
        total_row_df.index = ["TOTAL DIÁRIO"]
        
        # Formata cabeçalho dos dias para string (01, 02...)
        pivot.columns = [f"{c:02d}" if isinstance(c, int) else c for c in pivot.columns]
        total_row_df.columns = pivot.columns # Garante alinhamento exato

        # --- LÓGICA DE PAGINAÇÃO ---
        ROWS_PER_PAGE = 20
        total_rows = len(pivot)
        total_pages = math.ceil(total_rows / ROWS_PER_PAGE)
        
        if st.session_state.flight_page_idx >= total_pages:
            st.session_state.flight_page_idx = 0
            
        current_page = st.session_state.flight_page_idx
        start_idx = current_page * ROWS_PER_PAGE
        end_idx = start_idx + ROWS_PER_PAGE
        
        # Fatia os dados
        df_display = pivot.iloc[start_idx:end_idx]
        
        # ANEXA O TOTALIZADOR À PÁGINA ATUAL
        # Assim o usuário vê o total do dia independentemente da página que está
        df_display_with_total = pd.concat([df_display, total_row_df])

        nome_mes_display = mes_map.get(sel_mes, str(sel_mes))
        st.subheader(f"Mapa: {sel_veiculo} - {nome_mes_display}/{sel_ano}")

        cols_days = [c for c in pivot.columns if c != "TOTAL"]
        max_val_global = pivot[cols_days].max().max() if not pivot[cols_days].empty else 1

        col_config = {
            "TOTAL": st.column_config.TextColumn("Total", width="small")
        }
        for c in cols_days:
            col_config[c] = st.column_config.TextColumn(c, width="small")

        # --- RENDERIZAÇÃO DA TABELA ---
        # Fix: map em vez de applymap para silenciar warning
        styler = df_display_with_total.style\
            .background_gradient(cmap="YlOrRd", subset=cols_days, vmin=0, vmax=max_val_global)\
            .format("{:.0f}")\
            .map(lambda x: "color: transparent" if x == 0 else "color: black; font-weight: bold", subset=cols_days)\
            .map(lambda x: "background-color: #e6f3ff; font-weight: bold; border-left: 2px solid #ccc", subset=["TOTAL"])\
            .apply(lambda x: ["background-color: #d1e7dd; font-weight: bold" if x.name == "TOTAL DIÁRIO" else "" for i in x], axis=1)
        
        styler = styler.set_properties(**{'text-align': 'center'})

        st.dataframe(
            styler,
            height=(len(df_display_with_total) * 35) + 38,
            width="stretch", # Fix: width="stretch" em vez de use_container_width
            column_config=col_config
        )
        
        # --- UI DE PAGINAÇÃO ---
        if total_pages > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            c_prev, c_msg, c_next = st.columns([1, 2, 1])
            
            with c_prev:
                if st.button("⬅️ Anterior", disabled=(current_page == 0), use_container_width=True):
                    st.session_state.flight_page_idx -= 1
                    st.rerun()
            
            with c_msg:
                st.markdown(
                    f"<div style='text-align: center; padding-top: 5px; font-weight: bold; color: #003366'>"
                    f"Página {current_page + 1} de {total_pages} • Mostrando {start_idx + 1} a {min(end_idx, total_rows)} de {total_rows} anunciantes"
                    f"</div>", 
                    unsafe_allow_html=True
                )
            
            with c_next:
                if st.button("Próximo ➡️", disabled=(current_page == total_pages - 1), use_container_width=True):
                    st.session_state.flight_page_idx += 1
                    st.rerun()
        else:
            st.caption(f"Mostrando {total_rows} registros.")

        st.markdown("---")
        
        # --- DETALHAMENTO PADRONIZADO ---
        with st.expander("Fonte de Dados Completa (Detalhamento)", expanded=False):
            # Prepara DF detalhado
            rename_map = {
                "Praca": "Praça", "Anuncio": "Anúncio", "Duracao": "Duração",
                "Emissora": "Veículo", "Volume de Insercoes": "Inserções", 
                "Tipo": "Tipo", "DayPart": "DayPart"
            }
            cols_originais = ["Data_Dt", "Anunciante", "Anuncio", "Duracao", "Praca", "Emissora", "Tipo", "DayPart", "Volume de Insercoes"]
            cols_existentes = [c for c in cols_originais if c in df_final.columns]
            
            df_detalhe = df_final[cols_existentes].rename(columns=rename_map)
            
            # Formatação de Data para String (DD/MM/AAAA)
            if "Data_Dt" in df_detalhe.columns:
                df_detalhe["Data"] = df_detalhe["Data_Dt"].dt.strftime("%d/%m/%Y")
                df_detalhe = df_detalhe.drop(columns=["Data_Dt"])
                # Reordena para Data ser a primeira
                cols = ["Data"] + [c for c in df_detalhe.columns if c != "Data"]
                df_detalhe = df_detalhe[cols]

            df_detalhe = df_detalhe.sort_values(by=["Anunciante", "Data"])
            st.dataframe(df_detalhe, width="stretch", hide_index=True)

        # --- EXPORTAÇÃO ---
        with st.spinner("Gerando Excel Completo..."):
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                workbook = writer.book
                fmt_center = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
                
                # Filtros
                f_data = {
                    "Filtro": ["Ano", "Mês", "Praça", "Veículo", "Anunciantes", "Dias"],
                    "Valor": [
                        sel_ano, nome_mes_display, sel_praca, sel_veiculo,
                        ", ".join(sel_anunciantes) if sel_anunciantes else "Todos",
                        "Selecionados" if sel_dias else "Todos"
                    ]
                }
                pd.DataFrame(f_data).to_excel(writer, sheet_name='Filtros', index=False)
                writer.sheets['Filtros'].set_column('A:B', 30)
                
                # Mapa Flight Completo (com linha Total Geral no final)
                pivot_export = pd.concat([pivot, total_row_df])
                pivot_export.to_excel(writer, sheet_name='Flight Map')
                ws = writer.sheets['Flight Map']
                ws.set_column('A:A', 40)
                ws.set_column('B:AF', 5, fmt_center)
                ws.set_column('AG:AG', 10, fmt_center)

                # Detalhamento
                if not df_detalhe.empty:
                    df_detalhe.to_excel(writer, sheet_name='Detalhamento', index=False)
                    ws_det = writer.sheets['Detalhamento']
                    ws_det.set_column('A:Z', 15, fmt_center)
                    ws_det.set_column('B:C', 35) # Anunciante largo
        
        c_vazio1, c_vazio2, c_btn, c_vazio3, c_vazio4 = st.columns([1, 1, 1, 1, 1])
        with c_btn:
            st.download_button(
                label="Exportar Excel",
                data=buffer,
                file_name=f"Flight_{sel_veiculo}_{sel_mes:02d}_{sel_ano}.xlsx",
                mime="application/vnd.ms-excel",
                type="secondary",
                use_container_width=True
            )
            
        st.markdown(f"<div style='text-align:center;color:#666;font-size:0.8rem;margin-top:5px;'>Última atualização da base de dados: {data_atualizacao}</div>", unsafe_allow_html=True)