
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
            return df
    raise ValueError("Não foi possível encontrar a tabela de Elo.")

@st.cache_data
def carregar_elo():
    return obter_elo_tabela()

def encontrar_jogador(df, nome):
    nome = nome.lower().strip()
    resultados = df[df["Player"].str.lower().str.contains(nome)]
    if resultados.empty:
        return None
    return resultados.iloc[0]

def elo_prob(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

def value_bet(prob, odd):
    return (prob * odd) - 1

# --------------------- Interface Streamlit ---------------------
st.title("Análise de Valor em Apostas de Ténis (Elo - Tennis Abstract)")

with st.spinner("A carregar Elo Ratings..."):
    elo_df = carregar_elo()

st.success("Dados atualizados com sucesso!")

col1, col2 = st.columns(2)

with col1:
    jogador_a = st.text_input("Jogador A", placeholder="ex: Carlos Alcaraz")
    odd_a = st.number_input("Odd para o Jogador A", value=1.80, step=0.01)

with col2:
    jogador_b = st.text_input("Jogador B", placeholder="ex: Jannik Sinner")

superficie = st.selectbox("Superfície", ["Hard", "Clay", "Grass", "Indoor"])

if jogador_a and jogador_b:
    dados_a = encontrar_jogador(elo_df, jogador_a)
    dados_b = encontrar_jogador(elo_df, jogador_b)

    if dados_a is None or dados_b is None:
        st.error("Jogador não encontrado. Verifica os nomes.")
    else:
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
            valor = value_bet(prob_a, odd_a)

            st.markdown("---")
            st.metric("Probabilidade estimada de A vencer", f"{prob_a * 100:.2f}%")
            st.metric("Valor esperado da aposta", f"{valor * 100:.2f}%")

            if valor > 0:
                st.success("Aposta com valor! ✅")
            elif valor < 0:
                st.error("Sem valor na aposta ❌")
            else:
                st.info("Aposta neutra.")
        except KeyError:
            st.error(f"Não foi possível encontrar o Elo '{elo_chave}' para um dos jogadores.")
