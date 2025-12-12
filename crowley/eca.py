# crowley/eca.py
import streamlit as st
import pandas as pd
import json
import io
import numpy as np  # Importante para usar np.nan
from datetime import datetime, timedelta, date

def render(df_crowley, cookies, data_atualizacao):
    # Aumenta limite de renderização
    pd.set_option("styler.render.max_elements", 5_000_000)

    # --- CSS GLOBAL ---
    st.markdown("""
        <style>
        [data-testid="stDataFrame"] th {
            text-align: center !important;
            vertical-align: middle !important;
        }
        [data-testid="stDataFrame"] td {
            text-align: center !important;
            vertical-align: middle !important;
        }
        [data-testid="stDataFrame"] th[data-testid="stColumnHeader"]:first-child,
        [data-testid="stDataFrame"] td:first-child {
            text-align: left !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- Header e Voltar ---
    if st.button("Voltar", key="btn_voltar_eca"):
        st.query_params["view"] = "menu"
        st.session_state.pop("eca_search_trigger", None)
        st.rerun()

    st.markdown('<div class="page-title-centered">Relatório ECA</div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666;">Exclusivos • Compartilhados • Ausentes</p>', unsafe_allow_html=True)
    
    if df_crowley is None or df_crowley.empty:
        st.error("Base de dados não carregada.")
        st.stop()

    if "Data_Dt" not in df_crowley.columns:
        if "Data" in df_crowley.columns:
            df_crowley["Data_Dt"] = pd.to_datetime(df_crowley["Data"], dayfirst=True, errors="coerce")
        else:
            st.error("Coluna de Data não encontrada na base.")
            st.stop()

    # --- CONFIGURAÇÃO ---
    min_date_allowed = date(2024, 1, 1)
    try: max_date_allowed = datetime.strptime(data_atualizacao, "%d/%m/%Y").date()
    except: max_date_allowed = datetime.now().date()
        
    tooltip_dates = f"Dados disponíveis para pesquisa:\nDe 01/01/2024 até {data_atualizacao}"
    st.session_state["eca_show_share"] = True

    # --- COOKIES ---
    saved_filters = {}
    cookie_val = cookies.get("crowley_filters_eca")
    if cookie_val:
        try: saved_filters = json.loads(cookie_val)
        except: pass

    def get_date_from_cookie(key, default_date):
        val = saved_filters.get(key)
        if val:
            try:
                d = datetime.strptime(val, "%Y-%m-%d").date()
                if d < min_date_allowed: return min_date_allowed
                if d > max_date_allowed: return max_date_allowed
                return d
            except: return default_date
        return default_date

    # Defaults
    default_ini = max(min_date_allowed, max_date_allowed - timedelta(days=30))
    val_dt_ini = get_date_from_cookie("dt_ini", default_ini)
    val_dt_fim = get_date_from_cookie("dt_fim", max_date_allowed)
    
    saved_praca = saved_filters.get("praca", None)
    saved_veiculo = saved_filters.get("veiculo", None)
    saved_concorrentes = saved_filters.get("concorrentes", [])

    # --- FILTROS ---
    st.markdown("##### Configuração da Análise")
    
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 1.5])
        with c1: dt_ini = st.date_input("Início", value=val_dt_ini, min_value=min_date_allowed, max_value=max_date_allowed, format="DD/MM/YYYY", help=tooltip_dates)
        with c2: dt_fim = st.date_input("Fim", value=val_dt_fim, min_value=min_date_allowed, max_value=max_date_allowed, format="DD/MM/YYYY")
        
        lista_pracas = sorted(df_crowley["Praca"].dropna().unique())
        
        def on_praca_change():
            st.session_state["eca_veiculo_key"] = None
            st.session_state["eca_concorrentes_key"] = []
            st.session_state["eca_search_trigger"] = False

        if "eca_praca_key" not in st.session_state:
            idx_praca = lista_pracas.index(saved_praca) if saved_praca in lista_pracas else 0
            st.session_state["eca_praca_key"] = lista_pracas[idx_praca]

        with c3: sel_praca = st.selectbox("Praça", options=lista_pracas, key="eca_praca_key", on_change=on_praca_change)

        st.divider()

        df_praca = df_crowley[df_crowley["Praca"] == sel_praca]
        lista_veiculos_local = sorted(df_praca["Emissora"].dropna().unique())
        
        c4, c5 = st.columns([1, 2])
        if "eca_veiculo_key" not in st.session_state:
            idx_v = lista_veiculos_local.index(saved_veiculo) if saved_veiculo in lista_veiculos_local else 0
            st.session_state["eca_veiculo_key"] = lista_veiculos_local[idx_v] if lista_veiculos_local else None

        with c4: sel_veiculo = st.selectbox("Veículo Alvo (Protagonista)", options=lista_veiculos_local, key="eca_veiculo_key")

        lista_concorrentes = [v for v in lista_veiculos_local if v != sel_veiculo]
        valid_concorrentes = [c for c in saved_concorrentes if c in lista_concorrentes]
        if "eca_concorrentes_key" not in st.session_state:
            st.session_state["eca_concorrentes_key"] = valid_concorrentes

        with c5: sel_concorrentes = st.multiselect("Comparar com (Concorrência)", options=lista_concorrentes, key="eca_concorrentes_key", placeholder="Se vazio, compara com TODOS da praça")

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.button("Gerar Relatório ECA", type="primary", use_container_width=True)

    if submitted:
        st.session_state["eca_search_trigger"] = True
        new_filters = {"dt_ini": str(dt_ini), "dt_fim": str(dt_fim), "praca": sel_praca, "veiculo": sel_veiculo, "concorrentes": sel_concorrentes}
        cookies["crowley_filters_eca"] = json.dumps(new_filters)
        cookies.save()

    if st.session_state.get("eca_search_trigger"):
        ts_ini = pd.Timestamp(dt_ini)
        ts_fim = pd.Timestamp(dt_fim) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        
        df_base = df_praca[(df_praca["Data_Dt"] >= ts_ini) & (df_praca["Data_Dt"] <= ts_fim)].copy()
        df_target = df_base[df_base["Emissora"] == sel_veiculo]
        
        if sel_concorrentes: df_comp = df_base[df_base["Emissora"].isin(sel_concorrentes)]
        else: df_comp = df_base[df_base["Emissora"] != sel_veiculo]

        exclusivos = set(df_target["Anunciante"].unique()) - set(df_comp["Anunciante"].unique())
        compartilhados = set(df_target["Anunciante"].unique()) & set(df_comp["Anunciante"].unique())
        ausentes = set(df_comp["Anunciante"].unique()) - set(df_target["Anunciante"].unique())

        # --- HELPER DE TABELA (CORRIGIDO COM NP.NAN) ---
        def criar_tabela_resumo(df_src, lista_anunciantes, is_exclusive=False):
            if not lista_anunciantes: return pd.DataFrame()
            
            df_final = df_src[df_src["Anunciante"].isin(lista_anunciantes)].copy()
            col_val = "Volume de Insercoes" if "Volume de Insercoes" in df_final.columns else "Contagem"
            if col_val == "Contagem": df_final["Contagem"] = 1
            
            pivot_qty = pd.pivot_table(
                df_final, index="Anunciante", columns="Emissora", values=col_val, 
                aggfunc="sum", fill_value=0, observed=True
            )
            
            total_por_anunciante = pivot_qty.sum(axis=1)
            pivot_qty = pivot_qty.loc[total_por_anunciante.sort_values(ascending=False).index]
            
            if is_exclusive:
                total_row = pivot_qty.sum(numeric_only=True)
                pivot_qty.loc["TOTAL GERAL"] = total_row
                return pivot_qty
            
            total_por_emissora = pivot_qty.sum(axis=0)
            pivot_share = pivot_qty.div(total_por_emissora.replace(0, 1), axis=1) * 100
            
            cols = []
            for col in pivot_qty.columns:
                cols.append((col, "Share %"))
                cols.append((col, "Inserções"))
            cols.append(("TOTAL", "Inserções"))
            
            df_multi = pd.DataFrame(index=pivot_qty.index, columns=pd.MultiIndex.from_tuples(cols))
            
            for col in pivot_qty.columns:
                df_multi[(col, "Inserções")] = pivot_qty[col]
                df_multi[(col, "Share %")] = pivot_share[col]
            
            df_multi[("TOTAL", "Inserções")] = total_por_anunciante
            
            totals_qty = pivot_qty.sum(numeric_only=True)
            total_geral_row = []
            
            for col_tuple in df_multi.columns:
                emissora, tipo = col_tuple
                if tipo == "Inserções":
                    if emissora == "TOTAL": val = total_por_anunciante.sum()
                    else: val = totals_qty[emissora]
                    total_geral_row.append(val)
                else:
                    # --- A MÁGICA: Usar np.nan ---
                    # Isso mantém a coluna como float e o PyArrow não reclama.
                    total_geral_row.append(np.nan)
            
            df_multi.loc["TOTAL GERAL"] = total_geral_row
            return df_multi

        # --- HELPERS DE ESTILO ---
        def safe_fmt_int(x):
            try:
                if pd.isnull(x) or x == "": return ""
                return f"{int(x)}"
            except: return str(x)

        def safe_fmt_pct(x):
            try:
                if pd.isnull(x) or x == "": return "" # NaN vira string vazia AQUI
                return f"{float(x):.1f}%"
            except: return str(x)

        def style_df(df, is_exclusive=False):
            if df.empty: return df
            
            header_styles = [
                {'selector': 'th', 'props': [('text-align', 'center'), ('vertical-align', 'middle')]},
                {'selector': 'th.row_heading', 'props': [('text-align', 'left')]},
                {'selector': 'td', 'props': [('text-align', 'center')]}
            ]
            
            if is_exclusive:
                s = df.style.format(safe_fmt_int)
            else:
                format_dict = {}
                for col in df.columns:
                    if col[1] == "Share %": format_dict[col] = safe_fmt_pct
                    else: format_dict[col] = safe_fmt_int
                
                # na_rep="" faz o NaN aparecer vazio no visual do Streamlit
                s = df.style.format(format_dict, na_rep="")

            s = s.set_properties(**{'text-align': 'center'})
            s = s.set_table_styles(header_styles)
            s = s.apply(lambda x: ["background-color: #f0f2f6; font-weight: bold" if (hasattr(x, 'name') and x.name == "TOTAL GERAL") else "" for i in x], axis=1)
            return s

        t1, t2, t3 = st.tabs([f"Exclusivos ({len(exclusivos)})", f"Compartilhados ({len(compartilhados)})", f"Ausentes ({len(ausentes)})"])

        with t1:
            df1 = criar_tabela_resumo(df_target, exclusivos, is_exclusive=True)
            if not df1.empty: 
                st.dataframe(style_df(df1, is_exclusive=True), width="stretch", height=500)
            else: st.info("Nenhum registro.")

        with t2:
            df_full_shared = pd.concat([df_target[df_target["Anunciante"].isin(compartilhados)], df_comp[df_comp["Anunciante"].isin(compartilhados)]])
            df2 = criar_tabela_resumo(df_full_shared, compartilhados, is_exclusive=False)
            if not df2.empty: st.dataframe(style_df(df2, is_exclusive=False), width="stretch", height=500)
            else: st.info("Nenhum registro.")

        with t3:
            df3 = criar_tabela_resumo(df_comp, ausentes, is_exclusive=False)
            if not df3.empty: st.dataframe(style_df(df3, is_exclusive=False), width="stretch", height=500)
            else: st.info("Nenhum registro.")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- DETALHAMENTO ---
        with st.expander("Fonte de Dados Completa (Detalhamento)", expanded=False):
            df_global_view = pd.concat([df_target, df_comp])
            
            rename_map = {
                "Praca": "Praça", "Anuncio": "Anúncio", "Duracao": "Duração",
                "Emissora": "Veículo", "Volume de Insercoes": "Inserções", 
                "Tipo": "Tipo", "DayPart": "DayPart"
            }
            
            df_detalhe = df_global_view.copy()
            if "Data_Dt" in df_detalhe.columns:
                df_detalhe["Data"] = df_detalhe["Data_Dt"].dt.strftime("%d/%m/%Y")
            
            cols_originais = ["Data", "Anunciante", "Anuncio", "Duracao", "Praca", "Emissora", "Tipo", "DayPart", "Volume de Insercoes"]
            cols_existentes = [c for c in cols_originais if c in df_detalhe.columns]
            
            df_exib = df_detalhe[cols_existentes].rename(columns=rename_map)
            df_exib.sort_values(by=["Anunciante", "Data"], inplace=True)
            
            st.dataframe(df_exib, width="stretch", hide_index=True)

        st.markdown("---")
        
        # --- EXPORTAÇÃO ---
        with st.spinner("Gerando Excel..."):
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                workbook = writer.book
                
                fmt_center = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
                fmt_left = workbook.add_format({'align': 'left', 'valign': 'vcenter'})
                
                f_data = {"Parâmetro": ["Início", "Fim", "Praça", "Veículo", "Concorrentes", "Share"], 
                          "Valor": [dt_ini.strftime("%d/%m/%Y"), dt_fim.strftime("%d/%m/%Y"), sel_praca, sel_veiculo, ", ".join(sel_concorrentes) if sel_concorrentes else "Todos", "Ativado"]}
                pd.DataFrame(f_data).to_excel(writer, sheet_name='Filtros', index=False)
                writer.sheets['Filtros'].set_column('A:B', 40)

                def save_tab(df, name, include_index=True):
                    if not df.empty:
                        # O Pandas já exporta np.nan como célula vazia por padrão
                        # Não precisamos fazer replace nenhum!
                        df.to_excel(writer, sheet_name=name, index=include_index)
                        worksheet = writer.sheets[name]
                        worksheet.set_column('A:A', 40, fmt_left)
                        worksheet.set_column('B:Z', 15, fmt_center)
                
                save_tab(df1, 'Exclusivos')
                save_tab(df2, 'Compartilhados')
                save_tab(df3, 'Ausentes')
                
                if not df_exib.empty:
                    df_exib.to_excel(writer, sheet_name='Detalhamento', index=False)
                    worksheet = writer.sheets['Detalhamento']
                    
                    for idx, col_name in enumerate(df_exib.columns):
                        if col_name in ["Anunciante", "Anúncio"]:
                            worksheet.set_column(idx, idx, 35, fmt_left)
                        else:
                            worksheet.set_column(idx, idx, 15, fmt_center)

        c_vazio1, c_vazio2, c_btn, c_vazio3, c_vazio4 = st.columns([1, 1, 1, 1, 1])
        with c_btn:
            st.download_button("Exportar Excel", data=buf, file_name=f"ECA_{sel_veiculo}_{datetime.now().strftime('%d%m')}.xlsx", mime="application/vnd.ms-excel", type="secondary", use_container_width=True)
        
        st.markdown(f"<div style='text-align:center;color:#666;font-size:0.8rem;margin-top:5px;'>Última atualização da base de dados: {data_atualizacao}</div>", unsafe_allow_html=True)