import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from difflib import get_close_matches
import importlib.util
import time

BASE_URL = "https://www.tennisexplorer.com"

# Dependência obrigatória para tabelas HTML
if importlib.util.find_spec("html5lib") is None:
    st.error(
        "Dependência obrigatória não encontrada: 'html5lib'.\n"
        "Execute `pip install html5lib` no terminal antes de usar o aplicativo."
    )
    st.stop()

# Obter a lista de torneios masculinos ATP ativos da página principal
def obter_torneios_atp_ativos():
    url = f"{BASE_URL}/matches/"
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "html.parser")
    torneios = []
    for a in soup.select("a[href*='/atp-men/']"):
        nome = a.text.strip()
        href = a['href']
        url_completo = BASE_URL + href if href.startswith('/') else href
        if url_completo not in [t['url'] for t in torneios]:
            torneios.append({"nome": nome, "url": url_completo})
    return torneios

# Buscar o nome completo do jogador a partir da página pessoal
@st.cache_data(show_spinner=False)
def obter_nome_completo(url_jogador):
    try:
        r = requests.get(url_jogador, timeout=15)
        soup = BeautifulSoup(r.content, "html.parser")
        h1 = soup.find("h1")
        if h1:
            nome = re.sub(r'\s+', ' ', h1.get_text(strip=True))
            return nome
    except:
        pass
    return None

def limpar_numero_ranking(nome):
    return re.sub(r"\s*\(\d+\)", "", nome).strip()

# Extrair jogos (com nomes completos) do torneio selecionado
@st.cache_data(show_spinner=False)
def obter_jogos_do_torneio_completos(url_torneio):
    jogos = []
    r = requests.get(url_torneio)
    soup = BeautifulSoup(r.content, "html.parser")
    tabelas = soup.select("table")
    if not tabelas:
        return jogos

    jogadores_links = []

    # Buscar todos os links de jogadores presentes na página do torneio
    for a in soup.select("a[href^='/player/']"):
        nome = a.text.strip()
        url_jogador = BASE_URL + a['href']
        jogadores_links.append((nome, url_jogador))

    mapa_links = dict(jogadores_links)  # nome reduzido -> url perfil

    for table in tabelas:
        tbody = table.find("tbody")
        if not tbody:
            continue
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 7:
                continue
            confronto = tds[2].text.strip()
            try:
                odd_a = float(tds[5].text.strip())
                odd_b = float(tds[6].text.strip())
            except:
                odd_a = None
                odd_b = None

            partes = confronto.split('-')
            if len(partes) != 2:
                continue
            nome_red_a = limpar_numero_ranking(partes[0].strip())
            nome_red_b = limpar_numero_ranking(partes[1].strip())

            # Pega o link individual do jogador (se houver)
            url_jog_a = mapa_links.get(nome_red_a)
            url_jog_b = mapa_links.get(nome_red_b)

            # Busca nome completo de cada jogador (com cache)
            nome_completo_a = obter_nome_completo(url_jog_a) if url_jog_a else nome_red_a
            nome_completo_b = obter_nome_completo(url_jog_b) if url_jog_b else nome_red_b

            jogos.append({
                "label": f"{nome_completo_a} vs {nome_completo_b}",
                "jogador_a": nome_completo_a,
                "jogador_b": nome_completo_b,
                "odd_a": odd_a,
                "odd_b": odd_b
            })
        if jogos:
            break
    return jogos

# Funções Elo/yElo (iguais ao fluxo anterior)
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
        raise ValueError("Tabela de Elo não encontrada.")
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
        raise ValueError("Tabela de yElo não encontrada.")
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
    candidatos = get_close_matches(jogador, yelo_df["Player"], n=1, cutoff=0.7)
    if candidatos:
        return yelo_df[yelo_df["Player"] == candidatos[0]]["yElo"].values[0]
    return None

superficies_map = {
    "Piso Duro": "Hard",
    "Relva": "Grass",
    "Terra Batida": "Clay"
}

# --- App
st.title("Análise de Valor em Apostas de Ténis — Torneios ATP (nomes completos automáticos)")

if st.button("Atualizar dados agora"):
    st.cache_data.clear()
    st.info("Os dados serão recarregados.")

with st.spinner("Carregando bases Elo e yElo..."):
    elo_df = cache_elo()
    yelo_df = cache_yelo()

if elo_df is None or yelo_df is None:
    st.stop()
st.success("Bases carregadas!")

with st.spinner("Detectando torneios ATP masculinos ativos..."):
    torneios = obter_torneios_atp_ativos()
if not torneios:
    st.warning("Nenhum torneio ATP ativo encontrado neste momento.")
    st.stop()

nome_torneio_escolhido = st.selectbox("Selecione o torneio ATP", [t["nome"] for t in torneios])
url_torneio = next(t["url"] for t in torneios if t["nome"] == nome_torneio_escolhido)

with st.spinner(f"Buscando jogos para {nome_torneio_escolhido} com nomes completos..."):
    jogos = obter_jogos_do_torneio_completos(url_torneio)

if not jogos:
    st.warning(f"Nenhum jogo encontrado para o torneio {nome_torneio_escolhido}.")
    st.stop()

label_selec = st.selectbox("Selecione o jogo", [j["label"] for j in jogos])
selecionado = next(j for j in jogos if j["label"] == label_selec)

# Odds já vêm preenchidas se disponíveis, mas permitem edição
odd_a_input = st.number_input(f"Odd para {selecionado['jogador_a']}", value=selecionado['odd_a'] if selecionado['odd_a'] else 1.80, step=0.01)
odd_b_input = st.number_input(f"Odd para {selecionado['jogador_b']}", value=selecionado['odd_b'] if selecionado['odd_b'] else 2.00, step=0.01)

superficie_port = st.selectbox("Superfície", list(superficies_map.keys()), index=0)
superficie = superficies_map[superficie_port]

# Busca de dados Elo/yElo com nome completo
dados_a = elo_df[elo_df["Player"] == selecionado["jogador_a"]]
dados_b = elo_df[elo_df["Player"] == selecionado["jogador_b"]]

if dados_a.empty:
    st.error(f"Nenhum dado Elo encontrado para jogador: {selecionado['jogador_a']}")
    st.stop()
if dados_b.empty:
    st.error(f"Nenhum dado Elo encontrado para jogador: {selecionado['jogador_b']}")
    st.stop()

dados_a = dados_a.iloc[0]
dados_b = dados_b.iloc[0]
yelo_a = encontrar_yelo(selecionado["jogador_a"], yelo_df)
yelo_b = encontrar_yelo(selecionado["jogador_b"], yelo_df)

col1, col2 = st.columns(2)
with col1:
    try:
        geral_a = float(dados_a["Elo"])
        esp_a = float(dados_a[{"Hard":"hElo", "Clay":"cElo", "Grass":"gElo"}[superficie]])
        yelo_a_f = float(yelo_a)
        elo_final_a = (esp_a / geral_a) * yelo_a_f
        st.metric(f"Elo Final {selecionado['jogador_a']}", f"{elo_final_a:.2f}")
    except Exception:
        st.warning(f"Elo Final do jogador {selecionado['jogador_a']} indisponível")
with col2:
    try:
        geral_b = float(dados_b["Elo"])
        esp_b = float(dados_b[{"Hard":"hElo", "Clay":"cElo", "Grass":"gElo"}[superficie]])
        yelo_b_f = float(yelo_b)
        elo_final_b = (esp_b / geral_b) * yelo_b_f
        st.metric(f"Elo Final {selecionado['jogador_b']}", f"{elo_final_b:.2f}")
    except Exception:
        st.warning(f"Elo Final do jogador {selecionado['jogador_b']} indisponível")

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

# Remover juice das odds do bookie antes do cálculo do valor esperado
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
    E o valor esperado é calculado usando odds ajustadas (sem juice).
    """)

st.markdown("---")
st.caption("Fontes: tennisabstract.com e tennisexplorer.com | App experimental")
