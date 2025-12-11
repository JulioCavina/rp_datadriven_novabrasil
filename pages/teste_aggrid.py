# pages/teste_aggrid.py
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

def render():
    st.set_page_config(layout="wide", page_title="Deep Dive Opção 3")
    st.title("🧪 Laboratório: Focando na Opção 3 (Scroll vs Total)")
    st.markdown("O objetivo é: Altura Fixa (scroll vertical interno) + Scroll Horizontal + Totalizador visível sem corte.")

    # --- DADOS ---
    cols = ["Cliente", "Alpha_Ins", "Alpha_Share", "Band_Ins", "Band_Share", 
            "Clube_Ins", "Clube_Share", "JP_Ins", "JP_Share", 
            "Mega_Ins", "Mega_Share", "Diario_Ins", "Diario_Share",
            "Nativa_Ins", "Nativa_Share", "CBN_Ins", "CBN_Share"]
    
    data = []
    for i in range(50): 
        row = [f"Cliente {i:03d}"] + [np.random.randint(10, 500) for _ in range(16)]
        data.append(row)
    
    df = pd.DataFrame(data, columns=cols)
    
    totals = {c: 99999 for c in cols if c != "Cliente"}
    totals["Cliente"] = "TOTAL GERAL"

    js_num = JsCode("function(p){ return p.value ? p.value.toLocaleString('pt-BR') : ''; }")

    def get_gb(dataframe):
        gb = GridOptionsBuilder.from_dataframe(dataframe)
        # MinWidth 120 força o scroll horizontal aparecer
        gb.configure_default_column(resizable=True, filter=True, sortable=True, minWidth=120) 
        gb.configure_column("Cliente", pinned="left", minWidth=200, cellStyle={'fontWeight': 'bold'})
        for c in dataframe.columns:
            if c != "Cliente": gb.configure_column(c, type=["numericColumn"], valueFormatter=js_num)
        return gb

    # ==============================================================================
    # VARIAÇÕES DA OPÇÃO 3
    # ==============================================================================

    st.header("3.1. Aumentar Altura da Linha Pinned")
    st.caption("Aumentamos a altura da linha de total para 50px. Se a barra cobrir 15px, ainda sobram 35px para o texto.")
    gb = get_gb(df)
    gb.configure_grid_options(domLayout='normal', pinnedBottomRowData=[totals], pinnedBottomRowHeight=50)
    AgGrid(df, gridOptions=gb.build(), height=400, width='100%', fit_columns_on_grid_load=False, allow_unsafe_jscode=True, key='v3_1')

    st.header("3.2. ScrollbarWidth Explicito")
    st.caption("Dizemos ao Grid que a barra tem 20px de altura, para ele tentar reservar espaço.")
    gb = get_gb(df)
    gb.configure_grid_options(domLayout='normal', pinnedBottomRowData=[totals], scrollbarWidth=20)
    AgGrid(df, gridOptions=gb.build(), height=400, width='100%', fit_columns_on_grid_load=False, allow_unsafe_jscode=True, key='v3_2')

    st.header("3.3. O Truque da Linha Fantasma (Buffer)")
    st.caption("Adicionamos DUAS linhas no rodapé. A última é vazia (para a barra de rolagem comer) e a penúltima é o Total.")
    totals_buffer = {c: "" for c in cols} # Linha vazia
    gb = get_gb(df)
    # Ordem: Total, depois Buffer (o buffer fica no fundo absoluto)
    gb.configure_grid_options(domLayout='normal', pinnedBottomRowData=[totals, totals_buffer], pinnedBottomRowHeight=30)
    AgGrid(df, gridOptions=gb.build(), height=400, width='100%', fit_columns_on_grid_load=False, allow_unsafe_jscode=True, key='v3_3')

    st.header("3.4. Tema Alpine (Layout Engine Diferente)")
    st.caption("O tema 'alpine' gerencia bordas e paddings de forma diferente do 'streamlit'. Pode não cortar.")
    gb = get_gb(df)
    gb.configure_grid_options(domLayout='normal', pinnedBottomRowData=[totals])
    AgGrid(df, gridOptions=gb.build(), height=400, width='100%', fit_columns_on_grid_load=False, theme="alpine", allow_unsafe_jscode=True, key='v3_4')

    st.header("3.5. Tema Balham (Compacto)")
    st.caption("Tema 'balham' é mais denso. Verifica se o cálculo de altura bate.")
    gb = get_gb(df)
    gb.configure_grid_options(domLayout='normal', pinnedBottomRowData=[totals])
    AgGrid(df, gridOptions=gb.build(), height=400, width='100%', fit_columns_on_grid_load=False, theme="balham", allow_unsafe_jscode=True, key='v3_5')

    st.header("3.6. CSS: Padding no Viewport")
    st.caption("Forçamos um padding-bottom de 20px no corpo da tabela via CSS para empurrar o conteúdo.")
    st.markdown("""<style>
    #grid-v3_6 .ag-body-viewport { padding-bottom: 20px !important; }
    </style>""", unsafe_allow_html=True)
    gb = get_gb(df)
    gb.configure_grid_options(domLayout='normal', pinnedBottomRowData=[totals])
    AgGrid(df, gridOptions=gb.build(), height=400, width='100%', fit_columns_on_grid_load=False, allow_unsafe_jscode=True, key='v3_6')

    st.header("3.7. CSS: Scrollbar Fina + Z-Index")
    st.caption("Customizamos a barra de rolagem para ser mais fina e garantimos que a linha pinned tenha prioridade de Z-Index.")
    st.markdown("""<style>
    /* Barra fina */
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-thumb { background: #888; }
    /* Linha total acima */
    #grid-v3_7 .ag-row-pinned { z-index: 9999 !important; border-top: 2px solid red !important; }
    </style>""", unsafe_allow_html=True)
    gb = get_gb(df)
    gb.configure_grid_options(domLayout='normal', pinnedBottomRowData=[totals])
    AgGrid(df, gridOptions=gb.build(), height=400, width='100%', fit_columns_on_grid_load=False, allow_unsafe_jscode=True, key='v3_7')

    st.header("3.8. Always Show Horizontal Scroll")
    st.caption("Força a barra a estar lá desde o início, o que às vezes ajuda o Grid a calcular a altura correta da linha pinned.")
    gb = get_gb(df)
    gb.configure_grid_options(domLayout='normal', pinnedBottomRowData=[totals], alwaysShowHorizontalScroll=True)
    AgGrid(df, gridOptions=gb.build(), height=400, width='100%', fit_columns_on_grid_load=False, allow_unsafe_jscode=True, key='v3_8')

    st.header("3.9. Header + Row Height Explicitos")
    st.caption("Definimos todas as alturas manualmente para não deixar o AgGrid adivinhar.")
    gb = get_gb(df)
    gb.configure_grid_options(
        domLayout='normal', 
        pinnedBottomRowData=[totals], 
        headerHeight=40, 
        rowHeight=30, 
        pinnedBottomRowHeight=40 # Mais alto que a row normal
    )
    AgGrid(df, gridOptions=gb.build(), height=400, width='100%', fit_columns_on_grid_load=False, allow_unsafe_jscode=True, key='v3_9')

    st.header("3.10. Container Wrapper + Fit Width False")
    st.caption("Uma variação da Opção 4: AgGrid 'normal' (limitado), mas dentro de um container Streamlit.")
    with st.container(border=True, height=450):
        gb = get_gb(df)
        gb.configure_grid_options(domLayout='normal', pinnedBottomRowData=[totals])
        AgGrid(df, gridOptions=gb.build(), height=400, width='100%', fit_columns_on_grid_load=False, allow_unsafe_jscode=True, key='v3_10')

if __name__ == "__main__":
    render()