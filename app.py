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

    for df in tabelas:
        if 'Player' in df.columns:
            df.columns = [col.strip() for col in df.columns]
            df = df.dropna(subset=["Player"])
            return df
    raise ValueError("Não foi possível encontrar a tabela de Elo.")

def obter_yelo_tabela():
    url = "https://tennisabstract.com/reports/atp_season_yelo_ratings.html"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    tabelas = pd.read_html(str(soup))

    for df in tabelas:
        if 'Player' in df.columns and 'yElo' in df.columns:
            df.columns = [col.strip() for col in df.columns]
            df = df.dropna(subset=["Player"])
            return df[['Player', 'yElo']]
    raise ValueError("Não foi possível encontrar a tabela de yElo.")

@st.cache_data
def carregar_elo():
    return obter_elo_tabela()

@st.cache_data
def carregar_yelo():
    return obter_yelo_tabela()

def elo_prob(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

def value_bet(prob, odd):
    return (prob * odd) - 1

# --------------------- Interface Streamlit ---------------------
st.title("Análise de Valor em Apostas de Ténis (Elo - Tennis Abstract)")

with st.spinner("A carregar Elo Ratings..."):
    elo_df = carregar_elo()
    yelo_df = carregar_yelo()

st.success("Dados atualizados com sucesso!")

jogadores_disponiveis = sorted(elo_df["Player"].dropna().unique())

col1, col2 = st.columns(2)

with col1:
    jogador_a = st.selectbox("Seleciona o Jogador A", jogadores_disponiveis, index=0)
    odd_a = st.number_input("Odd para o Jogador A", value=1.80, step=0.01)

with col2:
    jogador_b = st.selectbox("Seleciona o Jogador B", jogadores_disponiveis, index=1)
    odd_b = st.number_input("Odd para o Jogador B", value=2.00, step=0.01)

superficie = st.selectbox("Superfície", ["Hard", "Clay", "Grass"])

if jogador_a and jogador_b:
    dados_a = elo_df[elo_df["Player"] == jogador_a].iloc[0]
    dados_b = elo_df[elo_df["Player"] == jogador_b].iloc[0]

    yelo_val_a = yelo_df[yelo_df["Player"] == jogador_a]["yElo"]
    yelo_val_b = yelo_df[yelo_df["Player"] == jogador_b]["yElo"]

    if yelo_val_a.empty or yelo_val_b.empty:
        st.error("Não foi possível encontrar o yElo de um dos jogadores.")
    else:
        yelo_a = yelo_val_a.values[0]
        yelo_b = yelo_val_b.values[0]

        elo_chave = {
            "Hard": "hElo",
            "Clay": "cElo",
            "Grass": "gElo"
        }[superficie]

        try:
            geral_a = dados_a["Elo"]
            geral_b = dados_b["Elo"]
            esp_a = dados_a[elo_chave]
            esp_b = dados_b[elo_chave]

            elo_final_a = (esp_a / geral_a) * yelo_a
            elo_final_b = (esp_b / geral_b) * yelo_b

            prob_a = elo_prob(elo_final_a, elo_final_b)
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
