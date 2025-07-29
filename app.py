import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from difflib import get_close_matches
import importlib.util

# ----- Verificar dependência html5lib -----
if importlib.util.find_spec("html5lib") is None:
    st.error(
        "Dependência obrigatória não encontrada: 'html5lib'.\n"
        "Execute `pip install html5lib` no terminal antes de usar o aplicativo."
    )
    st.stop()

# --------------------- Funções 
def obter_elo_tabela():
    url = "https://tennisabstract.com/reports/atp_elo_ratings.html"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        tabelas = pd.read_html(str(soup), flavor="bs4")
        for df in tabelas:
            # Corrigir colunas para string com strip
            df.columns = [str(col).strip() for col in df.columns]
            if 'Player' in df.columns:
                df = df.dropna(subset=["Player"])
                return df
        raise ValueError("Não foi possível encontrar a tabela de Elo.")
    except Exception as e:
        st.error(f"Erro ao obter Elo Ratings: {e}")
        return None

def obter_yelo_tabela():
    url = "https://tennisabstract.com/reports/atp_season_yelo_ratings.html"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        tabelas = pd.read_html(str(soup), flavor="bs4")
        for df in tabelas:
            # Corrigir colunas para string com strip e em minusculas
            df.columns = [str(col).strip().lower() for col in df.columns]
            if 'player' in df.columns and 'yelo' in df.columns:
                df = df.dropna(subset=["player"])
                df = df.rename(columns={"player": "Player", "yelo": "yElo"})
                return df[["Player", "yElo"]]
        raise ValueError("Não foi possível encontrar a tabela de yElo.")
    except Exception as e:
        st.error(f"Erro ao obter yElo Ratings: {e}")
        return None

@st.cache_data(show_spinner=False)
def cache_elo():
    return obter_elo_tabela()

@st.cache_data(show_spinner=False)
def cache_yelo():
    return obter_yelo_tabela()

def elo_prob(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

def value_bet(prob, odd):
    return (prob * odd) - 1

def buscar_jogadores(subtexto, jogadores):
    encontrados = [j for j in jogadores if subtexto.lower() in j.lower()]
    return encontrados

def encontrar_yelo(jogador, yelo_df):
    if jogador in yelo_df["Player"].values:
        return yelo_df[yelo_df["Player"] == jogador]["yElo"].values[0]
    candidatos = get_close_matches(jogador, yelo_df["Player"], n=1, cutoff=0.70)
    if candidatos:
        return yelo_df[yelo_df["Player"] == candidatos[0]]["yElo"].values[0]
    return None

# --------------------- Interface Streamlit ---------------------
st.title("Análise de Valor em Apostas de Ténis (Elo - Tennis Abstract)")

# Botão para atualizar manualmente dados
if st.button("Atualizar dados agora"):
    st.cache_data.clear()
    st.info("Os dados serão recarregados.")

with st.spinner("A carregar Elo Ratings..."):
    elo_df = cache_elo()
    yelo_df = cache_yelo()

if elo_df is None or yelo_df is None:
    st.stop()

st.success("Dados carregados com sucesso!")

jogadores_disponiveis = sorted(elo_df["Player"].dropna().unique())

# Busca de jogadores por substring
with st.expander("Procurar nome do jogador por substring"):
    busca_nome = st.text_input("Pesquisar por parte do nome")
    if busca_nome:
        encontrados = buscar_jogadores(busca_nome, jogadores_disponiveis)
        if encontrados:
            st.write("Jogadores encontrados:", encontrados)
        else:
            st.write("Nenhum jogador encontrado.")

col1, col2 = st.columns(2)

with col1:
    jogador_a = st.selectbox("Seleciona o Jogador A", jogadores_disponiveis, index=0)
    odd_a = st.number_input("Odd para o Jogador A", value=1.80, step=0.01)

with col2:
    jogador_b = st.selectbox("Seleciona o Jogador B", jogadores_disponiveis, index=1)
    odd_b = st.number_input("Odd para o Jogador B", value=2.00, step=0.01)

superficie = st.selectbox("Superfície", ["Hard", "Clay", "Grass"])

if jogador_a and jogador_b and jogador_a != jogador_b:
    dados_a = elo_df[elo_df["Player"] == jogador_a].iloc[0]
    dados_b = elo_df[elo_df["Player"] == jogador_b].iloc[0]

    yelo_a = encontrar_yelo(jogador_a, yelo_df)
    yelo_b = encontrar_yelo(jogador_b, yelo_df)

    # Exibe elos dos jogadores com transparência
    with st.expander("Mostrar detalhes completos dos jogadores selecionados"):
        st.markdown(f"**{jogador_a}**")
        st.json(dados_a.to_dict())
        st.markdown(f"**{jogador_b}**")
        st.json(dados_b.to_dict())
    st.markdown(f"**yElo de {jogador_a}:** {yelo_a}")
    st.markdown(f"**yElo de {jogador_b}:** {yelo_b}")

    if yelo_a is None or yelo_b is None:
        st.error("Não foi possível encontrar o yElo de um dos jogadores.")
    else:
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

            with st.expander("Como é feito o cálculo?"):
                st.write("""
                O Elo final de cada jogador é calculado com:
                ```
                Elo Final = (Elo Superfície / Elo Geral) × yElo
                ```
                Depois, calcula-se a probabilidade pelo modelo Elo e o valor esperado usando as odds inseridas.
                """)

        except KeyError:
            st.error(f"Não foi possível encontrar o Elo '{elo_chave}' para um dos jogadores.")
else:
    st.info("Selecione jogadores diferentes em cada campo.")

st.markdown("---")
st.caption("Fonte dos dados: tennisabstract.com | Este app é experimental. Use com responsabilidade.")


