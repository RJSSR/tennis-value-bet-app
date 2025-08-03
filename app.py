import streamlit as st
import pandas as pd

# -- Configuração de página e CSS custom --
st.set_page_config(page_title="Tennis Value Bets", page_icon="🎾", layout="wide")

st.markdown("""
    <style>
      .main-title {color:#176ab4; font-size:2.5em; font-weight:700; margin-bottom:0.2em;}
      .stMetric {background-color:#e4f1fb !important; border-radius:8px;}
      .faixa-stake {font-weight:bold; padding:2px 10px; border-radius:8px;}
      .stake-low {background:#e3fde3; color:#2e7d32;}
      .stake-mid {background:#fff5cc; color:#ad8506;}
      .stake-high {background:#ffeaea; color:#b13d3d;}
      .custom-sep {border-bottom:1px solid #daecfa; margin:20px 0 20px 0;}
    </style>
""", unsafe_allow_html=True)
st.markdown('<div class="main-title">🎾 Análise de Valor em Apostas de Ténis — Torneios ATP</div>', unsafe_allow_html=True)

# -- Seções com Tabs --
tab1, tab2 = st.tabs(["🔎 Análise Manual", "🤖 Análise Automática"])

# -- Simulação de Inputs/Torneios para demonstração --
torneios = [{'nome':'Madrid Masters', 'url':'#'}, {'nome':'Roma Masters', 'url':'#'}]
superficies_map = {"Hard":"Duro", "Clay":"Terra", "Grass":"Relva"}

with st.sidebar:
    st.header("⚙️ Definições")
    st.caption("Personalize filtros e visualização aqui.")
    st.divider()
    st.selectbox("Selecionar Torneio", [t['nome'] for t in torneios])
    st.selectbox("Superfície", list(superficies_map.values()))
    st.button("🔄 Atualizar Dados", type="primary")

# -- Análise Manual --
with tab1:
    st.header("Selecione o jogo manualmente")
    jogos_exemplo = [
        {'label': 'Carlos Alcaraz vs Novak Djokovic', 'odd_a': 1.85, 'odd_b': 2.05},
        {'label': 'Daniil Medvedev vs Jannik Sinner', 'odd_a': 2.00, 'odd_b': 1.90}
    ]
    jogo_selecionado = st.selectbox("Jogo:", [j['label'] for j in jogos_exemplo])
    odd_a = st.number_input("Odd para jogador A", value=1.85, step=0.01)
    odd_b = st.number_input("Odd para jogador B", value=2.05, step=0.01)

    st.divider()
    colA, colB = st.columns(2)
    with colA:
        st.metric("Prob. vitória (A)", "56.3%")
        st.metric("Valor esperado (A)", "8.5%")
        stake_a = 5  # Exemplo fixo do exemplo: poderia ser calculado na app real
        st.markdown("<span class='faixa-stake stake-low'>Stake recomendada: €5.00</span>", unsafe_allow_html=True)
        st.success("Valor positivo ✅")
    with colB:
        st.metric("Prob. vitória (B)", "43.7%")
        st.metric("Valor esperado (B)", "4.2%")
        stake_b = 5
        st.markdown("<span class='faixa-stake stake-low'>Stake recomendada: €5.00</span>", unsafe_allow_html=True)
        st.success("Valor positivo ✅")

    with st.expander("🔬 Explicação dos cálculos e detalhes avançados"):
        st.markdown("""
        * Fórmulas de Elo, value bet e lógica de staking exibidas aqui para transparência.
        * Odds corrigidas, cálculo de probabilidades, etc.
        """)

# -- Divisor visual custom --
st.markdown('<div class="custom-sep"></div>', unsafe_allow_html=True)

# -- Análise Automática / Tabela custom --
with tab2:
    st.header("Jogos com valor positivo")
    df_auto = pd.DataFrame({
        "Jogo": ["Alcaraz vs Djokovic", "Medvedev vs Sinner"],
        "Odd A": ["1.85", "2.00"],
        "Odd B": ["2.05", "1.90"],
        "Valor A %": ["8.5%", "15.2%"],
        "Valor B %": ["4.2%", "10.8%"],
        "Stake A (€)": ["5.00", "7.50"],
        "Stake B (€)": ["5.00", "5.00"]
    })
    st.dataframe(
        df_auto.style
        .applymap(lambda v: "background-color:#e3fde3;" if v == "5.00" else
                             "background-color:#fff5cc;" if v == "7.50" else
                             "background-color:#ffeaea;" if v == "10.00" else "", subset=["Stake A (€)", "Stake B (€)"])
        .format(precision=2),
        use_container_width=True
    )

    st.caption("Legenda stake: 5€ [baixa], 7.5€ [média], 10€ [alta]")

# -- Créditos discretos no rodapé --
st.divider()
st.caption("Fontes: tennisexplorer.com e tennisabstract.com | App experimental — design demo")
