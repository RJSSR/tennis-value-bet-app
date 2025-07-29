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

def encontrar_yelo(jogador, yelo_df):
    if jogador in yelo_df["Player"].values:
        return yelo_df[yelo_df["Player"] == jogador]["yElo"].values[0]
    candidatos = get_close_matches(jogador, yelo_df["Player"], n=1, cutoff=0.70)
    if candidatos:
        return yelo_df[yelo_df["Player"] == candidatos[0]]["yElo"].values[0]
    return None

# Mapeamento superfície em português para chave interna
superficies_map = {
    "Piso Duro": "Hard",
    "Relva": "Grass",
    "Terra Batida": "Clay"
}

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

# Criar coluna com nome limpo removendo o texto "Player"
elo_df["Player_Limpo"] = elo_df["Player"].astype(str).str.replace("Player", "", regex=False).str.strip()

# Dicionário para mapear nome limpo => nome original
mapa_jogadores = dict(zip(elo_df["Player_Limpo"], elo_df["Player"]))

# Lista de nomes limpos para exibir
jogadores_disponiveis = sorted(mapa_jogadores.keys())

# Primeiro o selectbox da superfície (em português)
superficie_port = st.selectbox("Superfície", options=list(superficies_map.keys()))

# Traduz para chave correta para cálculo
superficie = superficies_map[superficie_port]

col1, col2 = st.columns(2)

with col1:
    jogador_a_limpo = st.selectbox("Seleciona o Jogador A", jogadores_disponiveis, index=0)
    odd_a = st.number_input("Odd para o Jogador A", value=1.80, step=0.01)

with col2:
    jogador_b_limpo = st.selectbox("Seleciona o Jogador B", jogadores_disponiveis, index=1)
    odd_b = st.number_input("Odd para o Jogador B", value=2.00, step=0.01)

# Recuperar os nomes originais para a busca dos dados
jogador_a = mapa_jogadores[jogador_a_limpo]
jogador_b = mapa_jogadores[jogador_b_limpo]

if jogador_a and jogador_b and jogador_a != jogador_b:
    dados_a = elo_df[elo_df["Player"] == jogador_a].iloc[0]
    dados_b = elo_df[elo_df["Player"] == jogador_b].iloc[0]

    yelo_a = encontrar_yelo(jogador_a, yelo_df)
    yelo_b = encontrar_yelo(jogador_b, yelo_df)

    # Mostrar Elo final logo abaixo das odds, dentro das mesmas colunas
    with col1:
        try:
            geral_a = float(dados_a["Elo"])
            esp_a = float(dados_a[{"Hard":"hElo","Clay":"cElo","Grass":"gElo"}[superficie]])
            yelo_a_f = float(yelo_a)
            elo_final_a = (esp_a / geral_a) * yelo_a_f
            st.metric("Elo Final Jogador A", f"{elo_final_a:.2f}")
        except Exception:
            st.warning("Elo Final Jogador A não disponível")

    with col2:
        try:
            geral_b = float(dados_b["Elo"])
            esp_b = float(dados_b[{"Hard":"hElo","Clay":"cElo","Grass":"gElo"}[superficie]])
            yelo_b_f = float(yelo_b)
            elo_final_b = (esp_b / geral_b) * yelo_b_f
            st.metric("Elo Final Jogador B", f"{elo_final_b:.2f}")
        except Exception:
            st.warning("Elo Final Jogador B não disponível")

    # Mostrar detalhes completos dos jogadores com yElo incluído
    with st.expander("Mostrar detalhes completos dos jogadores selecionados"):
        dados_a_exibir = dados_a.to_dict()
        dados_a_exibir["yElo"] = yelo_a
        st.markdown(f"### {jogador_a_limpo}")
        st.json(dados_a_exibir)

        dados_b_exibir = dados_b.to_dict()
        dados_b_exibir["yElo"] = yelo_b
        st.markdown(f"### {jogador_b_limpo}")
        st.json(dados_b_exibir)

    if yelo_a is None or yelo_b is None:
        st.error("Não foi possível encontrar o yElo de um dos jogadores.")
    else:
        try:
            geral_a = float(dados_a["Elo"])
            geral_b = float(dados_b["Elo"])
            esp_a = float(dados_a[{"Hard":"hElo","Clay":"cElo","Grass":"gElo"}[superficie]])
            esp_b = float(dados_b[{"Hard":"hElo","Clay":"cElo","Grass":"gElo"}[superficie]])
            yelo_a_f = float(yelo_a)
            yelo_b_f = float(yelo_b)
        except (ValueError, TypeError, KeyError) as e:
            st.error(f"Erro ao obter valores numéricos para cálculo: {e}")
            st.stop()

        elo_final_a = (esp_a / geral_a) * yelo_a_f
        elo_final_b = (esp_b / geral_b) * yelo_b_f

        prob_a = elo_prob(elo_final_a, elo_final_b)
        prob_b = 1 - prob_a

        # Remover juice das odds antes do cálculo de valor esperado
        prob_a_raw = 1 / odd_a
        prob_b_raw = 1 / odd_b
        soma_prob = prob_a_raw + prob_b_raw
        prob_a_corr = prob_a_raw / soma_prob
        prob_b_corr = prob_b_raw / soma_prob
        odd_a_corr = 1 / prob_a_corr
        odd_b_corr = 1 / prob_b_corr

        valor_a = value_bet(prob_a, odd_a_corr)
        valor_b = value_bet(prob_b, odd_b_corr)

        st.markdown("---")
        col_a, col_b = st.columns(2)

        with col_a:
            st.metric("Probabilidade A vencer", f"{prob_a * 100:.2f}%")
            st.metric("Valor esperado A", f"{valor_a * 100:.2f}%")
            if odd_a >= 1.45 and 0.03 <= valor_a <= 0.20:
                st.success("Valor positivo ✅")
            else:
                st.error("Sem valor ❌")

        with col_b:
            st.metric("Probabilidade B vencer", f"{prob_b * 100:.2f}%")
            st.metric("Valor esperado B", f"{valor_b * 100:.2f}%")
            if odd_b >= 1.45 and 0.03 <= valor_b <= 0.20:
                st.success("Valor positivo ✅")
            else:
                st.error("Sem valor ❌")

        with st.expander("Como é feito o cálculo?"):
            st.write("""
            O Elo final de cada jogador é calculado com:
            ```
            Elo Final = (Elo Superfície / Elo Geral) × yElo
            ```
            Depois, calcula-se a probabilidade pelo modelo Elo e o valor esperado usando as odds inseridas (ajustadas sem juice).
            """)

else:
    st.info("Selecione jogadores diferentes em cada campo.")

st.markdown("---")
st.caption("Fonte dos dados: tennisabstract.com | Este app é experimental. Use com responsabilidade.")
