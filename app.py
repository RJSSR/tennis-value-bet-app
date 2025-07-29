import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from difflib import get_close_matches
import importlib.util

BASE_URL = "https://www.tennisexplorer.com"

# ----- Checar dependência html5lib -----
if importlib.util.find_spec("html5lib") is None:
    st.error(
        "Dependência obrigatória não encontrada: 'html5lib'.\n"
        "Execute `pip install html5lib` no terminal antes de usar o aplicativo."
    )
    st.stop()

# Função para fazer scraping dos jogos do Toronto (filtrando pela seção do torneio)
def obter_jogos_toronto():
    url = f"{BASE_URL}/matches/"
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "html.parser")

    jogos_toronto = []
    captura = False  # flag para identificar se estamos na seção Toronto

    # Percorre as tabelas com jogos
    for table in soup.find_all("table", class_="table-main"):
        tbody = table.find("tbody")
        if not tbody:
            continue

        for tr in tbody.find_all("tr"):
            # Checa se é linha de cabeçalho de torneio para ligar/desligar flag
            if "head" in tr.get("class", []) and "flags" in tr.get("class", []):
                tname_td = tr.find("td", class_="t-name")
                if tname_td and tname_td.find("a") and "Toronto" in tname_td.text:
                    captura = True
                else:
                    captura = False
                continue

            if captura:
                jogadores = tr.find_all("td", class_="player")
                if len(jogadores) >= 2:
                    jogador_a_tag = jogadores[0].find("a")
                    jogador_b_tag = jogadores[1].find("a")
                    if jogador_a_tag and jogador_b_tag:
                        nome_abrev_a = jogador_a_tag.text.strip()
                        link_a = BASE_URL + jogador_a_tag['href']
                        nome_abrev_b = jogador_b_tag.text.strip()
                        link_b = BASE_URL + jogador_b_tag['href']

                        jogos_toronto.append({
                            "nome_abrev_a": nome_abrev_a,
                            "link_a": link_a,
                            "nome_abrev_b": nome_abrev_b,
                            "link_b": link_b,
                        })
    return jogos_toronto

# Função para obter o nome completo da página individual do jogador
def obter_nome_completo(url_jogador):
    try:
        resposta = requests.get(url_jogador)
        soup = BeautifulSoup(resposta.content, "html.parser")
        h1 = soup.find('h1')
        if h1:
            nome_completo = re.sub(r"\s+", " ", h1.text.strip())
            return nome_completo
        return None
    except:
        return None

# Função para limpar número de ranking dos nomes, ex: "Cerundolo F. (14)" → "Cerundolo F."
def limpar_numero_ranking(nome):
    return re.sub(r"\s*\(\d+\)", "", nome).strip()

# Funções para obter as tabelas Elo e yElo do Tennis Abstract
def obter_elo_tabela():
    url = "https://tennisabstract.com/reports/atp_elo_ratings.html"
    try:
        resposta = requests.get(url, timeout=10)
        resposta.raise_for_status()
        soup = BeautifulSoup(resposta.content, "html.parser")
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
        resposta = requests.get(url, timeout=10)
        resposta.raise_for_status()
        soup = BeautifulSoup(resposta.content, "html.parser")
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

# Mapeamento para superfícies
superficies_map = {
    "Piso Duro": "Hard",
    "Relva": "Grass",
    "Terra Batida": "Clay"
}

# ----------------------------------

st.title("Análise de Valor em Apostas de Ténis — ATP Toronto")

if st.button("Atualizar dados agora"):
    st.cache_data.clear()
    st.info("Os dados serão recarregados.")

with st.spinner("Carregando bases de dados Elo e yElo..."):
    elo_df = cache_elo()
    yelo_df = cache_yelo()

if elo_df is None or yelo_df is None:
    st.stop()

st.success("Bases de dados carregadas com sucesso!")

# Captura os jogos com nomes completos (cache para performance)
@st.cache_data(show_spinner=False)
def obter_jogos_completo():
    jogos_curto = obter_jogos_toronto()
    jogos_completo = []
    for jogo in jogos_curto:
        nome_completo_a = obter_nome_completo(jogo["link_a"])
        nome_completo_b = obter_nome_completo(jogo["link_b"])
        if not nome_completo_a:
            nome_completo_a = jogo["nome_abrev_a"]
        if not nome_completo_b:
            nome_completo_b = jogo["nome_abrev_b"]
        nome_completo_a = limpar_numero_ranking(nome_completo_a)
        nome_completo_b = limpar_numero_ranking(nome_completo_b)
        jogos_completo.append({
            "label": f"{nome_completo_a} vs {nome_completo_b}",
            "jogador_a": nome_completo_a,
            "jogador_b": nome_completo_b,
            "odd_a": None,  # Odds reais não extraídas neste exemplo (podem ser extraídas se estiverem no html)
            "odd_b": None,
        })
    return jogos_completo

jogos_hoje = obter_jogos_completo()

if not jogos_hoje:
    st.warning("Nenhum jogo do torneio Toronto encontrado hoje.")
    st.stop()

labels = [j["label"] for j in jogos_hoje]
selecionado_label = st.selectbox("Selecione o confronto do dia (Toronto)", labels)
selecionado = next(j for j in jogos_hoje if j["label"] == selecionado_label)

jogador_a = selecionado["jogador_a"]
jogador_b = selecionado["jogador_b"]

# Odds inseridas manualmente pelo usuário pois não extraímos do Tennis Explorer neste exemplo
odd_a_input = st.number_input(f"Odd para {jogador_a}", value=1.80, step=0.01)
odd_b_input = st.number_input(f"Odd para {jogador_b}", value=2.00, step=0.01)

superficie_port = st.selectbox("Superfície", list(superficies_map.keys()), index=0)
superficie = superficies_map[superficie_port]

dados_a = elo_df[elo_df["Player"] == jogador_a]
dados_b = elo_df[elo_df["Player"] == jogador_b]

if dados_a.empty:
    st.error(f"Nenhum dado Elo encontrado para jogador: {jogador_a}")
    st.stop()
if dados_b.empty:
    st.error(f"Nenhum dado Elo encontrado para jogador: {jogador_b}")
    st.stop()

dados_a = dados_a.iloc[0]
dados_b = dados_b.iloc[0]

yelo_a = encontrar_yelo(jogador_a, yelo_df)
yelo_b = encontrar_yelo(jogador_b, yelo_df)

col1, col2 = st.columns(2)

with col1:
    try:
        geral_a = float(dados_a["Elo"])
        esp_a = float(dados_a[{"Hard":"hElo", "Clay":"cElo", "Grass":"gElo"}[superficie]])
        yelo_a_f = float(yelo_a)
        elo_final_a = (esp_a / geral_a) * yelo_a_f
        st.metric(f"Elo Final {jogador_a}", f"{elo_final_a:.2f}")
    except Exception:
        st.warning(f"Elo Final do jogador {jogador_a} indisponível")

with col2:
    try:
        geral_b = float(dados_b["Elo"])
        esp_b = float(dados_b[{"Hard":"hElo", "Clay":"cElo", "Grass":"gElo"}[superficie]])
        yelo_b_f = float(yelo_b)
        elo_final_b = (esp_b / geral_b) * yelo_b_f
        st.metric(f"Elo Final {jogador_b}", f"{elo_final_b:.2f}")
    except Exception:
        st.warning(f"Elo Final do jogador {jogador_b} indisponível")

if yelo_a is None or yelo_b is None:
    st.error("Não foi possível encontrar o yElo de um dos jogadores.")
    st.stop()

try:
    geral_a = float(dados_a["Elo"])
    geral_b = float(dados_b["Elo"])
    esp_a = float(dados_a[{"Hard":"hElo", "Clay":"cElo", "Grass":"gElo"}[superficie]])
    esp_b = float(dados_b[{"Hard":"hElo", "Clay":"cElo", "Grass":"gElo"}[superficie]])
    yelo_a_f = float(yelo_a)
    yelo_b_f = float(yelo_b)
except (ValueError, TypeError, KeyError) as e:
    st.error(f"Erro ao obter valores numéricos para cálculo: {e}")
    st.stop()

elo_final_a = (esp_a / geral_a) * yelo_a_f
elo_final_b = (esp_b / geral_b) * yelo_b_f

prob_a = elo_prob(elo_final_a, elo_final_b)
prob_b = 1 - prob_a

# Remove juice das odds do bookie antes de calcular valor esperado
prob_a_raw = 1 / odd_a_input
prob_b_raw = 1 / odd_b_input
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
    if odd_a_input >= 1.45 and 0.03 <= valor_a <= 0.20:
        st.success("Valor positivo ✅")
    else:
        st.error("Sem valor ❌")

with col_b:
    st.metric("Probabilidade B vencer", f"{prob_b * 100:.2f}%")
    st.metric("Valor esperado B", f"{valor_b * 100:.2f}%")
    if odd_b_input >= 1.45 and 0.03 <= valor_b <= 0.20:
        st.success("Valor positivo ✅")
    else:
        st.error("Sem valor ❌")

with st.expander("Como funciona o cálculo?"):
    st.write("""
    O Elo final de cada jogador é calculado com:
    ```
    Elo Final = (Elo Superfície / Elo Geral) × yElo
    ```
    Depois, calcula-se a probabilidade pelo modelo Elo e o valor esperado usando odds ajustadas para retirar o juice.
    """)

st.markdown("---")
st.caption("Fontes dos dados: tennisabstract.com e tennisexplorer.com | App experimental")

