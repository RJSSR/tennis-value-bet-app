# Aplicativo Streamlit com download automático de Elo Ratings do Tennis Abstract

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# --------------------- Funções 
def obter_elo_tabela():
    url = "https://tennisabstract.com/reports/atp_elo_ratings.html"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    tabelas = pd.read_html(str(soup))

    # Procurar a tabela correta (a que tem a coluna 'Player')
    for df in tabelas:
        if 'Player' in df.columns:
            df.columns = [col.strip() for col in df.columns]
            df = df.dropna(subset=["Player"])
            return df
    raise ValueError("Não foi possível encontrar a tabela de Elo.")

@st.cache_data
def carregar_elo():
    return obter_elo_tabela()

def elo_prob(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

def value_bet(prob, odd):
    return (prob * odd) - 1

# --------------------- Interface Streamlit ---------------------
st.title("Análise de Valor em Apostas de Ténis (Elo - Tennis Abstract)")

with st.spinner("A carregar Elo Ratings..."):
    elo_df = carregar_elo()

st.success("Dados atualizados com sucesso!")

jogadores_disponiveis = sorted(elo_df["Player"].dropna().unique())

col1, col2 = st.columns(2)

with col1:
    jogador_a = st.selectbox("Seleciona o Jogador A", jogadores_disponiveis, index=0)
    odd_a = st.number_input("Odd para o Jogador A", value=1.80, step=0.01)

with col2:
    jogador_b = st.selectbox("Seleciona o Jogador B", jogadores_disponiveis, index=1)
    odd_b = st.number_input("Odd para o Jogador B", value=2.00, step=0.01)

superficie = st.selectbox("Superfície", ["Hard", "Clay", "Grass", "Indoor"])

if jogador_a and jogador_b:
    dados_a = elo_df[elo_df["Player"] == jogador_a].iloc[0]
    dados_b = elo_df[elo_df["Player"] == jogador_b].iloc[0]

    elo_chave = {
        "Hard": "hElo",
        "Clay": "cElo",
        "Grass": "gElo",
        "Indoor": "iElo"
    }[superficie]

    try:
        elo_a = dados_a[elo_chave]
        elo_b = dados_b[elo_chave]

        prob_a = elo_prob(elo_a, elo_b)
        prob_b = 1 - prob_a

        valor_a = value_bet(prob_a, odd_a)
        valor_b = value_bet(prob_b, odd_b)

        st.markdown("---")
        col_a, col_b = st.columns(2)

        with col_a:
            st.metric("Probabilidade A vencer", f"{prob_a * 100:.2f}%")
            st.metric("Valor esperado A", f"{valor_a * 100:.2f}%")
            if valor_a > 0:
                st.success("Valor positivo ✅")
            elif valor_a < 0:
                st.error("Sem valor ❌")
            else:
                st.info("Aposta neutra")

        with col_b:
            st.metric("Probabilidade B vencer", f"{prob_b * 100:.2f}%")
            st.metric("Valor esperado B", f"{valor_b * 100:.2f}%")
            if valor_b > 0:
                st.success("Valor positivo ✅")
            elif valor_b < 0:
                st.error("Sem valor ❌")
            else:
                st.info("Aposta neutra")

    except KeyError:
        st.error(f"Não foi possível encontrar o Elo '{elo_chave}' para um dos jogadores.")
