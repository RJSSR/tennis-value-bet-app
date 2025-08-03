import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from difflib import get_close_matches
import unicodedata
import importlib.util

# ======== CSS MODERNO E LIMPO ========
st.markdown("""
    <style>
    body, .main {
        background: linear-gradient(120deg, #e3ecfc 0%, #f8fdff 100%);
    }
    div[data-testid="stSidebar"] {
        background: #11336b;
        color: white;
        min-width: 225px;
    }
    .stButton>button {
        background-color:#3164DD; color:white; font-weight:bold; border-radius:8px;
        border:none; padding:7px 0px;
    }
    .stDataFrame, .stTable {
        background: #f9fbfd !important;
        border-radius: 10px;
    }
    .stMetric {
        background: #f5f7fb; border-radius: 15px; padding:17px; min-height: 90px;
        box-shadow: 0 2px 8px rgba(80,110,200,.07);
    }
    header, h1, h2, h3 {
        color: #11336b;
        font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif !important;
    }
    .stAlert-success {background-color: #dbffe2;border-left: 7px solid #18af22;}
    .stAlert-error {background-color: #ffeaea;border-left:7px solid #f55;}
    .stAlert-info, .stAlert-warning {border-radius: 8px;}
    .stExpanderHeader {font-weight:bold;font-size:19px;}
    .card {
        background: white;
        border-radius: 18px;
        padding: 32px 26px 20px 26px;
        box-shadow: 0 2px 18px rgba(120,136,180,0.10);
        margin-bottom:20px;
    }
    .value-highlight {background: #e4ffe5; border-radius: 10px;}
    .stDataFrame tbody tr:hover {background-color: #f1f5fc !important;}
    .stDataFrame tbody tr td[rowspan] {background: #e4f2ff !important;}
    </style>
""", unsafe_allow_html=True)

# ======== SIDEBAR com brightness ========
with st.sidebar:
    st.markdown(
        '<div style="text-align:center;"><img src="https://www.tennisexplorer.com/img/te_logo.svg" width="110"></div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div style="font-size:18px;margin-top:20px;text-align:center;color:#dbe3f8;">' +
        'by <b>teambetting</b> experimental</div>',
        unsafe_allow_html=True
    )

# ======== CARD PRINCIPAL CENTRAL ========
st.markdown('<div class="card">', unsafe_allow_html=True)

st.markdown("<h1 style='font-size:2.3em;'>🎾 ATP Bets Value & Stake Analyzer</h1>", unsafe_allow_html=True)
st.write(
    "Obtenha recomendações matemáticas sobre onde pode haver valor em apostas de ténis ATP, com base em Elo, yElo e probabilidades ajustadas. Todos os dados ao vivo e fonte aberta!"
)

with st.container():
    st.markdown("#### 👀 O que o app faz?")
    st.write("- Analisa odds, **Elo/yElo**, surface-specialty, calcula probabilidade, edge (valor) e sugere stake.")
    st.write("- Só sinaliza aposta se **odds** e **valor esperado** encaixarem em parâmetros seguros.")
    st.markdown("---")
st.markdown('</div>', unsafe_allow_html=True)

BASE_URL = "https://www.tennisexplorer.com"
# ... (mantém as funções, helpers e lógica do app original)

# ======== ETAPA: DADOS ========
if st.button("🔄 Atualizar todos os dados", use_container_width=True):
    st.cache_data.clear()
    st.success("Dados atualizados!", icon="✅")

with st.spinner("Carregando bases..."):
    elo_df = cache_elo()
    yelo_df = cache_yelo()

if elo_df is None or yelo_df is None or elo_df.empty or yelo_df.empty:
    st.error("Erro ao carregar bases Elo/yElo.")
    st.stop()

# ======== ETAPAS EM “CARDS” ========
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("🌎 1. Escolha o Torneio ATP")
with st.spinner("Procurando torneios em andamento..."):
    torneios = obter_torneios_atp_ativos()
if not torneios:
    st.warning("Nenhum torneio ATP ativo encontrado.")
    st.stop()
nome_torneio = st.selectbox("Torneio:", [t['nome'] for t in torneios])
url_torneio = next(t['url'] for t in torneios if t['nome'] == nome_torneio)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("🛣️ 2. Superfície")
superficie_nome = st.selectbox("Superfície", list(superficies_map.keys()))
superficie = superficies_map[superficie_nome]
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("🎯 3. Escolha o Jogo")
with st.spinner(f"Carregando jogos do {nome_torneio}..."):
    jogos = obter_jogos_do_torneio(url_torneio)
if not jogos:
    st.warning("Nenhum jogo encontrado neste torneio.")
    st.stop()
selecionado_label = st.selectbox("Jogo:", [j['label'] for j in jogos])
selecionado = next(j for j in jogos if j['label'] == selecionado_label)
odd_a = st.number_input(f"Odd para {selecionado['jogador_a']}", value=selecionado['odd_a'] or 1.80, step=0.01, format="%.2f")
odd_b = st.number_input(f"Odd para {selecionado['jogador_b']}", value=selecionado['odd_b'] or 2.00, step=0.01, format="%.2f")
st.markdown('</div>', unsafe_allow_html=True)

# ... (processamento dos dados como antes)

st.markdown('<div class="card">', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.metric("🔵 Elo Final " + selecionado['jogador_a'], f"{elo_final_a:.2f}")
with col2:
    st.metric("🟠 Elo Final " + selecionado['jogador_b'], f"{elo_final_b:.2f}")
st.markdown('</div>', unsafe_allow_html=True)

# ====== RESULTADOS ======
st.markdown('<div class="card">', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.metric("Prob. vitória (A)", f"{prob_a*100:.2f}%")
    st.metric("Value esperado (A)", f"{valor_a*100:.2f}%")
    st.markdown(f"Stake: <span class='value-highlight'>€{stake_a:.2f}</span>", unsafe_allow_html=True)
    if 3.00 >= odd_a_f >= 1.45 and 0.03 <= valor_a <= 0.25:
        st.success("Valor positivo ✅")
    else:
        st.error("Sem valor", icon="❌")
with col2:
    st.metric("Prob. vitória (B)", f"{prob_b*100:.2f}%")
    st.metric("Value esperado (B)", f"{valor_b*100:.2f}%")
    st.markdown(f"Stake: <span class='value-highlight'>€{stake_b:.2f}</span>", unsafe_allow_html=True)
    if 3.00 >= odd_b_f >= 1.45 and 0.03 <= valor_b <= 0.25:
        st.success("Valor positivo ✅")
    else:
        st.error("Sem valor", icon="❌")
st.markdown('</div>', unsafe_allow_html=True)

# ====== EXPLICAÇÕES ==========

with st.expander("📊 ENTENDA O CÁLCULO – Detalhes Elo/yElo"):
    st.write(f"##### {selecionado['jogador_a']}")
    st.json(dados_a.to_dict())
    # ...
    st.markdown(r"""*(explicação do cálculo como antes)*""", unsafe_allow_html=True)

with st.expander("🚦 Análise automática: Value Bets"):
    if st.button("Analisar todos os jogos!", use_container_width=True):
        # ... cálculo e filtro da tabela df_valor_positivo ...
        st.markdown(
            "<div style='color:green;font-weight:700;'>Linha verde = aposta valiosa | Clique para ordenar!</div>",
            unsafe_allow_html=True
        )
        st.dataframe(styled, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center;opacity:.67;'>Fontes: tennisexplorer.com e tennisabstract.com | Design by teambetting+AI</div>",
    unsafe_allow_html=True
)

# -- Mantém toda a lógica e funções, apenas mudei o aspeto visual! --
