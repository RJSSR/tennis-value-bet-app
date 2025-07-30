import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from difflib import get_close_matches
import unicodedata
import importlib.util

BASE_URL = "https://www.tennisexplorer.com"

TORNEIOS_PERMITIDOS = [
    "Acapulco", "Adelaide", "Adelaide 2", "Almaty", "Antwerp", "Astana", "Atlanta", "ATP Cup",
    "Auckland", "Australian Open", "Banja Luka", "Barcelona", "Basel", "Bastad", "Beijing",
    "Belgrade", "Belgrade 2", "Brisbane", "Bucharest", "Buenos Aires", "Chengdu", "Cincinnati",
    "Cordoba", "Dallas", "Delray Beach", "Doha", "Dubai", "Eastbourne", "Estoril", "Florence",
    "French Open", "Geneva", "Gijon", "Gstaad", "Halle", "Hamburg", "Hangzhou",
    "Hertogenbosch", "Hong Kong ATP", "Houston", "Indian Wells", "Kitzbühel", "Los Cabos",
    "Lyon", "Madrid", "Mallorca", "Marrakech", "Marseille", "Masters Cup ATP", "Melbourne Summer Set 1",
    "Metz", "Miami", "Monte Carlo", "Montpellier", "Montreal", "Moscow", "Munich", "Napoli",
    "Newport", "Next Gen ATP Finals", "Paris", "Parma", "Pune", "Queen's Club", "Rio de Janeiro",
    "Rome", "Rotterdam", "Saint Petersburg", "San Diego", "Santiago", "Seoul", "Shanghai",
    "Sofia", "Stockholm", "Stuttgart", "Sydney", "Tel Aviv", "Tokyo (Japan Open)", "Toronto",
    "Umag", "United Cup", "US Open", "Vienna", "Washington", "Wimbledon", "Winston Salem", "Zhuhai"
]

if importlib.util.find_spec("html5lib") is None:
    st.error(
        "Dependência obrigatória não encontrada: 'html5lib'.\n"
        "Execute `pip install html5lib` no terminal antes de usar o aplicativo."
    )
    st.stop()

def limpar_numero_ranking(nome):
    return re.sub(r"\s*\(\d+\)", "", nome).strip()

def ajustar_nome(nome_raw):
    nome_sem_profile = nome_raw.replace(" - profile", "").strip()
    partes = nome_sem_profile.split(" - ")
    if len(partes) == 2:
        return f"{partes[1].strip()} {partes[0].strip()}"
    return nome_sem_profile

def reorganizar_nome(nome):
    partes = nome.strip().split()
    if len(partes) == 2:
        return f"{partes[1]} {partes[0]}"
    elif len(partes) == 3:
        return f"{partes[2]} {partes[0]} {partes[1]}"
    else:
        return nome

def normalizar_nome(nome):
    s = ''.join(
        c for c in unicodedata.normalize('NFD', nome)
        if unicodedata.category(c) != 'Mn'
    )
    return s.strip().casefold()

def obter_torneios_atp_ativos():
    url = f"{BASE_URL}/matches/"
    r = requests.get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")
    torneios = []
    nomes_permitidos = [tp.lower() for tp in TORNEIOS_PERMITIDOS]
    for a in soup.select("a[href*='/atp-men/']"):
        nome = a.text.strip()
        href = a['href']
        url_completo = BASE_URL + href if href.startswith('/') else href
        if nome.lower() in nomes_permitidos:
            if url_completo not in [t['url'] for t in torneios]:
                torneios.append({"nome": nome, "url": url_completo})
    return torneios

@st.cache_data(show_spinner=False)
def obter_nome_completo(url_jogador):
    if not url_jogador:
        return None
    try:
        r = requests.get(url_jogador, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        h1 = soup.find("h1")
        if h1:
            nome = re.sub(r'\s+', ' ', h1.get_text(strip=True))
            return nome
    except:
        pass
    return None

@st.cache_data(show_spinner=False)
def obter_jogos_do_torneio_completos(url_torneio):
    jogos = []
    r = requests.get(url_torneio)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")
    tabelas = soup.select("table")
    if not tabelas:
        return jogos
    jogadores_links = []
    for a in soup.select("a[href^='/player/']"):
        nome = a.text.strip()
        url_jogador = BASE_URL + a['href']
        jogadores_links.append((nome, url_jogador))
    mapa_links = dict(jogadores_links)
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
            url_jog_a = mapa_links.get(nome_red_a)
            url_jog_b = mapa_links.get(nome_red_b)
            nome_completo_a = obter_nome_completo(url_jog_a) if url_jog_a else nome_red_a
            nome_completo_b = obter_nome_completo(url_jog_b) if url_jog_b else nome_red_b
            nome_final_a = reorganizar_nome(ajustar_nome(nome_completo_a))
            nome_final_b = reorganizar_nome(ajustar_nome(nome_completo_b))
            jogos.append({
                "label": f"{nome_final_a} vs {nome_final_b}",
                "jogador_a": nome_final_a,
                "jogador_b": nome_final_b,
                "odd_a": odd_a,
                "odd_b": odd_b
            })
        if jogos:
            break
    return jogos

def obter_elo_tabela():
    url = "https://tennisabstract.com/reports/atp_elo_ratings.html"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        tabelas = pd.read_html(str(soup), flavor="bs4")
        for df in tabelas:
            df.columns = [str(col).strip() for col in df.columns]
            if "Player" in df.columns:
                df = df.dropna(subset=["Player"])
                return df
        raise ValueError("Tabela de Elo não encontrada.")
    except Exception as e:
        st.error(f"Erro ao obter Elo Ratings: {e}")
        return None

def obter_yelo_tabela():
    url = "https://tennisabstract.com/reports/atp_season_yelo_ratings.html"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        tabelas = pd.read_html(str(soup), flavor="bs4")
        for df in tabelas:
            df.columns = [str(col).strip().lower() for col in df.columns]
            if "player" in df.columns and "yelo" in df.columns:
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

def encontrar_yelo(nome, yelo_df):
    nome_cmp = normalizar_nome(nome)
    yelolist = [normalizar_nome(p) for p in yelo_df["Player"].dropna()]
    for idx, norm in enumerate(yelolist):
        if nome_cmp == norm:
            return yelo_df["yElo"].iloc[idx]
    match = get_close_matches(nome_cmp, yelolist, n=1, cutoff=0.80)
    if match:
        idx = yelolist.index(match[0])
        return yelo_df["yElo"].iloc[idx]
    return None

def match_nome(nome, df_col):
    nome_base = normalizar_nome(nome)
    possiveis_norm = df_col.dropna().map(normalizar_nome)
    mask = possiveis_norm == nome_base
    if mask.any():
        idx = mask[mask].index[0]
        return idx
    lista_nomes = possiveis_norm.tolist()
    match = get_close_matches(nome_base, lista_nomes, n=1, cutoff=0.80)
    if match:
        idx = lista_nomes.index(match[0])
        return df_col.index[idx]
    return None

superficies_map = {
    "Piso Duro": "Hard",
    "Relva": "Grass",
    "Terra Batida": "Clay"
}

st.title("Análise de Valor em Apostas de Ténis — Torneios ATP")

if st.button("Atualizar dados agora"):
    st.cache_data.clear()
    st.info("Os dados serão recarregados")

with st.spinner("Carregando bases Elo e yElo..."):
    elo_df = cache_elo()
    yelo_df = cache_yelo()

if elo_df is None or yelo_df is None:
    st.stop()

with st.spinner("Detectando torneios ATP ativos permitidos..."):
    torneios = obter_torneios_atp_ativos()

if not torneios:
    st.warning("Nenhum torneio ATP ativo encontrado no momento.")
    st.stop()

nome_torneio = st.selectbox("A escolher o torneio ATP", [t["nome"] for t in torneios])
url_torneio = next(t["url"] for t in torneios if t["nome"] == nome_torneio)

superficie_port = st.selectbox("A escolher o piso do torneio", list(superficies_map.keys()), index=0)
superficie = superficies_map[superficie_port]

with st.spinner(f"Obtendo jogos para {nome_torneio}..."):
    jogos = obter_jogos_do_torneio_completos(url_torneio)

if not jogos:
    st.warning(f"Nenhum jogo encontrado para o torneio {nome_torneio}.")
    st.stop()

selecionado_label = st.selectbox("Selecione o jogo", [j["label"] for j in jogos])
selecionado = next(j for j in jogos if j["label"] == selecionado_label)

odd_a = st.number_input(f"Odd para {selecionado['jogador_a']}",
                        value=selecionado['odd_a'] if selecionado['odd_a'] else 1.80, step=0.01)
odd_b = st.number_input(f"Odd para {selecionado['jogador_b']}",
                        value=selecionado['odd_b'] if selecionado['odd_b'] else 2.00, step=0.01)

idx_a = match_nome(selecionado["jogador_a"], elo_df["Player"])
idx_b = match_nome(selecionado["jogador_b"], elo_df["Player"])

if idx_a is None:
    st.error(f"Nenhum dado Elo encontrado para jogador: {selecionado['jogador_a']}")
    st.write(f"Nomes disponíveis na base: {elo_df['Player'].unique().tolist()}")
    st.stop()
if idx_b is None:
    st.error(f"Nenhum dado Elo encontrado para jogador: {selecionado['jogador_b']}")
    st.write(f"Nomes disponíveis na base: {elo_df['Player'].unique().tolist()}")
    st.stop()

dados_a = elo_df.loc[idx_a]
dados_b = elo_df.loc[idx_b]

yelo_a = encontrar_yelo(selecionado["jogador_a"], yelo_df)
yelo_b = encontrar_yelo(selecionado["jogador_b"], yelo_df)

col1, col2 = st.columns(2)
with col1:
    try:
        geral_a = float(dados_a["Elo"])
        esp_a = float(dados_a[{"Hard": "hElo", "Clay": "cElo", "Grass": "gElo"}[superficie]])
        yelo_a_f = float(yelo_a)
        elo_final_a = (esp_a / geral_a) * yelo_a_f
        st.metric(f"Elo Final {selecionado['jogador_a']}", f"{elo_final_a:.2f}")
    except Exception:
        st.warning(f"Elo Final do jogador {selecionado['jogador_a']} indisponível")
with col2:
    try:
        geral_b = float(dados_b["Elo"])
        esp_b = float(dados_b[{"Hard": "hElo", "Clay": "cElo", "Grass": "gElo"}[superficie]])
        yelo_b_f = float(yelo_b)
        elo_final_b = (esp_b / geral_b) * yelo_b_f
        st.metric(f"Elo Final {selecionado['jogador_b']}", f"{elo_final_b:.2f}")
    except Exception:
        st.warning(f"Elo Final do jogador {selecionado['jogador_b']} indisponível")

with st.expander("Detalhes completos Elo/yElo dos jogadores e explicação dos cálculos"):
    st.write(f"**{selecionado['jogador_a']}:**")
    st.json(dados_a.to_dict())
    st.write(f"**yElo:** {yelo_a}")
    st.write("---")
    st.write(f"**{selecionado['jogador_b']}:**")
    st.json(dados_b.to_dict())
    st.write(f"**yElo:** {yelo_b}")
    st.write("---")
    st.markdown(r"""
    ## Como funciona o cálculo?

    O sistema Elo estima a força relativa dos jogadores em confrontos diretos. A probabilidade do Jogador A vencer o Jogador B é:

    $$
    P(A) = \frac{1}{1 + 10^{\frac{Elo_B - Elo_A}{400}}}
    $$

    O Elo final de cada jogador é ajustado considerando a superfície e o yElo (atualização de desempenho recente):

    $$
    Elo_{final} = \left(\frac{Elo_{superfície}}{Elo_{geral}}\right) \times yElo
    $$

    O valor esperado da aposta é calculado removendo a margem da casa (juice) das odds, assim:

    $$
    \text{Valor esperado} = (\text{Probabilidade} \times \text{Odd ajustada}) - 1
    $$

    Um valor esperado positivo indica vantagem estatística para a aposta.
    """, unsafe_allow_html=True)

try:
    geral_a = float(dados_a["Elo"])
    geral_b = float(dados_b["Elo"])
    esp_a = float(dados_a[{"Hard": "hElo", "Clay": "cElo", "Grass": "gElo"}[superficie]])
    esp_b = float(dados_b[{"Hard": "hElo", "Clay": "cElo", "Grass": "gElo"}[superficie]])
    yelo_a_f = float(yelo_a)
    yelo_b_f = float(yelo_b)
except (ValueError, TypeError, KeyError) as e:
    st.error(f"Erro ao obter valores numéricos para cálculo: {e}")
    st.stop()

elo_final_a = (esp_a / geral_a) * yelo_a_f
elo_final_b = (esp_b / geral_b) * yelo_b_f

prob_a = elo_prob(elo_final_a, elo_final_b)
prob_b = 1 - prob_a

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
    if 3.00 >= odd_a >= 1.45 and 0.03 <= valor_a <= 0.25:
        st.success("Valor positivo ✅")
    else:
        st.error("Sem valor ❌")

with col_b:
    st.metric("Probabilidade B vencer", f"{prob_b * 100:.2f}%")
    st.metric("Valor esperado B", f"{valor_b * 100:.2f}%")
    if 3.00 >= odd_b >= 1.45 and 0.03 <= valor_b <= 0.25:
        st.success("Valor positivo ✅")
    else:
        st.error("Sem valor ❌")

# Bloco da análise automática dentro do expander
with st.expander("Análise automática: Jogos com valor esperado positivo"):
    if st.button("Analisar todos os jogos do torneio selecionado"):
        resultados = []
        for jogo in jogos:
            jogador_a = jogo["jogador_a"]
            jogador_b = jogo["jogador_b"]
            odd_a = jogo["odd_a"] if jogo["odd_a"] else 1.8
            odd_b = jogo["odd_b"] if jogo["odd_b"] else 2.0
            idx_a = match_nome(jogador_a, elo_df["Player"])
            idx_b = match_nome(jogador_b, elo_df["Player"])
            if idx_a is None or idx_b is None:
                continue
            dados_a = elo_df.loc[idx_a]
            dados_b = elo_df.loc[idx_b]
            yelo_a = encontrar_yelo(jogador_a, yelo_df)
            yelo_b = encontrar_yelo(jogador_b, yelo_df)
            if yelo_a is None or yelo_b is None:
                continue
            geral_a = float(dados_a["Elo"])
            esp_a = float(dados_a[{"Hard":"hElo","Clay":"cElo","Grass":"gElo"}[superficie]])
            yelo_a_f = float(yelo_a)
            elo_final_a = (esp_a / geral_a) * yelo_a_f
            geral_b = float(dados_b["Elo"])
            esp_b = float(dados_b[{"Hard":"hElo","Clay":"cElo","Grass":"gElo"}[superficie]])
            yelo_b_f = float(yelo_b)
            elo_final_b = (esp_b / geral_b) * yelo_b_f
            prob_a = elo_prob(elo_final_a, elo_final_b)
            prob_b = 1 - prob_a
            prob_a_raw = 1 / odd_a
            prob_b_raw = 1 / odd_b
            soma_prob = prob_a_raw + prob_b_raw
            prob_a_corr = prob_a_raw / soma_prob
            prob_b_corr = prob_b_raw / soma_prob
            odd_a_corr = 1 / prob_a_corr
            odd_b_corr = 1 / prob_b_corr
            valor_a = value_bet(prob_a, odd_a_corr)
            valor_b = value_bet(prob_b, odd_b_corr)
            resultados.append({
                "Confronto": f"{jogador_a} vs {jogador_b}",
                "Odd A": odd_a,
                "Odd B": odd_b,
                "Prob A": f"{prob_a*100:.2f}%",
                "Prob B": f"{prob_b*100:.2f}%",
                "Valor Esp. A": f"{valor_a*100:.2f}%",
                "Valor Esp. B": f"{valor_b*100:.2f}%",
                "Valor A OK": valor_a >= 0.03 and valor_a <= 0.25 and odd_a >= 1.45 and odd_a <= 3.00,
                "Valor B OK": valor_b >= 0.03 and valor_b <= 0.25 and odd_b >= 1.45 and odd_b <= 3.00,
            })
        df_valor = pd.DataFrame([r for r in resultados if r["Valor A OK"] or r["Valor B OK"]])
        if df_valor.empty:
            st.info("Nenhum jogo com valor esperado positivo encontrado.")
        else:
            st.success("Jogos com valor esperado positivo para pelo menos um dos lados:")
            st.dataframe(df_valor.drop(columns=["Valor A OK", "Valor B OK"]))
