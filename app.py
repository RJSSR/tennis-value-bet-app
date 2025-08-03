import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from difflib import get_close_matches
import unicodedata
import importlib.util

# ===== Checagem dependência html5lib =====
if importlib.util.find_spec("html5lib") is None:
    st.error("Dependência obrigatória 'html5lib' ausente. Instale com:\npip install html5lib")
    st.stop()

# ===== Configuração visual e CSS =====
st.set_page_config(page_title="Tennis Value Bets ATP & WTA", page_icon="🎾", layout="wide")
st.markdown("""
    <style>
      .main-title {color:#176ab4; font-size:2.5em; font-weight:700; margin-bottom:0.2em;}
      .stMetric {background-color:#e4f1fb !important; border-radius:8px;}
      .faixa-stake {font-weight:bold; padding:2px 10px; border-radius:8px;}
      .stake-low {background:#fff5cc; color:#ad8506;}
      .stake-mid {background:#fff5cc; color:#ad8506;}
      .stake-high {background:#fff5cc; color:#ad8506;}
      .custom-sep {border-bottom:1px solid #daecfa; margin:20px 0 20px 0;}
    </style>
""", unsafe_allow_html=True)
st.markdown('<div class="main-title">🎾 Análise de Valor em Apostas de Ténis — ATP & WTA</div>', unsafe_allow_html=True)

# ===== Mapas superfícies PT -> EN =====
superficies_map = {"Piso Duro": "Hard", "Terra": "Clay", "Relva": "Grass"}

BASE_URL = "https://www.tennisexplorer.com"

# ===== Listas de torneios permitidos ===== (ATP e WTA conforme seu pedido)
TORNEIOS_ATP_PERMITIDOS = [
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

TORNEIOS_WTA_PERMITIDOS = [
    "Abu Dhabi WTA", "Adelaide", "Adelaide 2", "Andorra WTA", "Angers WTA", "Antalya 2 WTA", "Antalya 3 WTA",
    "Antalya WTA", "Auckland", "Austin", "Australian Open", "Bad Homburg WTA", "Bari WTA", "Barranquilla",
    "Bastad WTA", "Beijing", "Belgrade", "Belgrade WTA", "Berlin", "Birmingham", "Bogotá WTA", "Bol WTA", "Brisbane",
    "Bucharest 2 WTA", "Budapest 2 WTA", "Budapest WTA", "Buenos Aires WTA", "Cali", "Cancún WTA", "Charleston",
    "Charleston 2", "Charleston 3", "Charleston 4", "Chennai WTA", "Chicago 2 WTA", "Chicago 3 WTA", "Chicago WTA",
    "Cincinnati WTA", "Cleveland WTA", "Cluj-Napoca 2 WTA", "Cluj-Napoca WTA", "Colina WTA", "Columbus WTA",
    "Concord WTA", "Contrexeville WTA", "Courmayeur WTA", "Doha", "Dubai", "Eastbourne", "Florence WTA",
    "Florianopolis WTA", "French Open", "Gaiba WTA", "Gdynia", "Grado", "Granby WTA", "Guadalajara 2 WTA",
    "Guadalajara WTA", "Guangzhou", "Hamburg WTA", "Hertogenbosch", "Hobart", "Hong Kong 2 WTA", "Hong Kong WTA",
    "Hua Hin 2 WTA", "Hua Hin WTA", "Iasi WTA", "Ilkley WTA", "Indian Wells", "Istanbul WTA", "Jiujiang",
    "Karlsruhe", "Kozerki", "La Bisbal", "Lausanne", "Limoges", "Linz", "Livesport Prague Open", "Ljubljana WTA",
    "Lleida", "Luxembourg WTA", "Lyon WTA", "Madrid WTA", "Makarska", "Marbella WTA", "Mérida", "Miami",
    "Midland WTA", "Monastir", "Monterrey", "Montevideo WTA", "Montreal WTA", "Montreux WTA", "Moscow", "Mumbai WTA",
    "Newport Beach WTA", "Ningbo WTA", "Nottingham", "Nur-Sultan WTA", "Osaka WTA", "Ostrava WTA", "Palermo",
    "Paris WTA", "Parma", "Porto WTA", "Portoroz WTA", "Puerto Vallarta", "Queen's Club", "Rabat", "Reus WTA",
    "Rome 2 WTA", "Rome WTA", "Rouen WTA", "Saint Petersburg WTA", "Saint-Malo WTA", "San Diego", "San Jose WTA",
    "San Luis Potosi WTA", "Santa Cruz WTA", "Seoul WTA", "Singapore WTA", "Stanford WTA", "Strasbourg", "Stuttgart",
    "Sydney", "Tallinn", "Tampico WTA", "Tenerife WTA", "Tokyo", "Toronto WTA", "US Open", "Valencia WTA",
    "Vancouver WTA", "Warsaw 2 WTA", "Warsaw WTA", "Washington", "Wimbledon", "Wuhan", "Zhengzhou 2 WTA"
]

# ===== Funções utilitárias =====

def limpar_numero_ranking(nome):
    return re.sub(r"\s*\(\d+\)", "", nome or "").strip()

def ajustar_nome(nome_raw):
    nome_raw = nome_raw or ""
    nome_sem_profile = nome_raw.replace(" - profile", "").strip()
    partes = nome_sem_profile.split(" - ")
    if len(partes) == 2:
        return f"{partes[1].strip()} {partes[0].strip()}"
    return nome_sem_profile

def reorganizar_nome(nome):
    partes = (nome or "").strip().split()
    if len(partes) == 2:
        return f"{partes[1]} {partes[0]}"
    elif len(partes) == 3:
        return f"{partes[2]} {partes[0]} {partes[1]}"
    else:
        return nome or ""

def normalizar_nome(nome):
    nome = nome or ""
    s = ''.join(c for c in unicodedata.normalize('NFD', nome) if unicodedata.category(c) != 'Mn')
    return s.strip().casefold()

@st.cache_data(show_spinner=False)
def obter_torneios(tipo="ATP"):
    url = f"{BASE_URL}/matches/"
    r = requests.get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")
    torneios = []
    nomes_permitidos = [t.casefold() for t in (TORNEIOS_ATP_PERMITIDOS if tipo == "ATP" else TORNEIOS_WTA_PERMITIDOS)]
    seletor = "a[href*='/atp-men/']" if tipo == "ATP" else "a[href*='/wta-women/']"
    for a in soup.select(seletor):
        nome = a.text.strip()
        href = a.get('href', '')
        if not href:
            continue
        url_full = BASE_URL + href if href.startswith("/") else href
        if nome.casefold() in nomes_permitidos:
            if url_full not in {t['url'] for t in torneios}:
                torneios.append({"nome": nome, "url": url_full})
    return torneios

@st.cache_data(show_spinner=False)
def obter_nome_completo(url_jogador):
    if not url_jogador:
        return None
    try:
        r = requests.get(url_jogador, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        h1 = soup.find('h1')
        if h1:
            return re.sub(r"\s+", " ", h1.get_text(strip=True))
    except:
        return None
    return None

@st.cache_data(show_spinner=False)
def obter_jogos_do_torneio(url_torneio):
    jogos = []
    r = requests.get(url_torneio)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")
    tables = soup.select("table")
    if not tables:
        return jogos
    jogador_map = {}
    for a in soup.select("a[href^='/player/']"):
        n = a.text.strip()
        u = BASE_URL + a['href'] if a['href'].startswith("/") else a['href']
        jogador_map[n] = u
    for table in tables:
        tbody = table.find('tbody')
        if not tbody:
            continue
        for tr in tbody.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) < 7:
                continue
            confronto = tds[2].text.strip()
            try:
                odd_a = float(tds[5].text.strip())
                odd_b = float(tds[6].text.strip())
            except:
                odd_a = None
                odd_b = None
            parts = confronto.split("-")
            if len(parts) != 2:
                continue
            p1, p2 = map(lambda s: limpar_numero_ranking(s.strip()), parts)
            url1 = jogador_map.get(p1)
            url2 = jogador_map.get(p2)
            nome1 = obter_nome_completo(url1) or p1
            nome2 = obter_nome_completo(url2) or p2
            nome1 = reorganizar_nome(ajustar_nome(nome1))
            nome2 = reorganizar_nome(ajustar_nome(nome2))
            jogos.append({
                "label": f"{nome1} vs {nome2}",
                "jogador_a": nome1,
                "jogador_b": nome2,
                "odd_a": odd_a,
                "odd_b": odd_b,
            })
        if jogos:
            break
    return jogos

def obter_elo_table(tipo="ATP"):
    url = "https://tennisabstract.com/reports/atp_elo_ratings.html" if tipo == "ATP" else "https://tennisabstract.com/reports/wta_elo_ratings.html"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')
        dfs = pd.read_html(str(soup), flavor="bs4")
        for df in dfs:
            cols = [str(c).strip() for c in df.columns]
            if 'Player' in cols:
                df.columns = cols
                df = df.dropna(subset=["Player"])
                return df
    except Exception as e:
        st.error(f"Erro ao obter Elo table {tipo}: {e}")
        return None

def obter_yelo_table(tipo="ATP"):
    url = "https://tennisabstract.com/reports/atp_season_yelo_ratings.html" if tipo == "ATP" else "https://tennisabstract.com/reports/wta_season_yelo_ratings.html"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')
        dfs = pd.read_html(str(soup), flavor="bs4")
        for df in dfs:
            cols = [str(c).strip().lower() for c in df.columns]
            if 'player' in cols and 'yelo' in cols:
                df.columns = cols
                df = df.dropna(subset=['player'])
                df = df.rename(columns={'player': 'Player', 'yelo': 'yElo'})
                return df[['Player', 'yElo']]
    except Exception as e:
        st.error(f"Erro ao obter Yelo table {tipo}: {e}")
        return None

@st.cache_data(show_spinner=False)
def cache_elo(tipo="ATP"):
    return obter_elo_table(tipo)

@st.cache_data(show_spinner=False)
def cache_yelo(tipo="ATP"):
    return obter_yelo_table(tipo)

def elo_prob(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

def value_bet(prob, odd):
    return prob * odd - 1

def stake_por_faixa(valor):
    if valor < 0.045 or valor > 0.275:
        return 0.0
    elif 0.045 <= valor < 0.11:
        return 5.0
    elif 0.11 <= valor < 0.18:
        return 7.5
    elif 0.18 <= valor <= 0.275:
        return 10.0
    else:
        return 0.0

def encontrar_yelo(nome, yelo_df):
    nrm_nome = normalizar_nome(nome)
    ys = yelo_df['Player'].dropna().tolist()
    nrm_ys = [normalizar_nome(x) for x in ys]
    for idx, val in enumerate(nrm_ys):
        if val == nrm_nome:
            return yelo_df.iloc[idx]['yElo']
    matches = get_close_matches(nrm_nome, nrm_ys, n=1, cutoff=0.8)
    if matches:
        idx = nrm_ys.index(matches[0])
        return yelo_df.iloc[idx]['yElo']
    return None

def match_nome(nome, df_col):
    nome_norm = normalizar_nome(nome)
    df_norm = df_col.dropna().apply(normalizar_nome)
    exact_match = df_norm[df_norm == nome_norm]
    if not exact_match.empty:
        return exact_match.index[0]
    else:
        matches = get_close_matches(nome_norm, df_norm.tolist(), n=1, cutoff=0.8)
        if matches:
            return df_norm[df_norm == matches[0]].index[0]
    return None

def elo_por_superficie(df_jogador, superficie_en):
    col_map = {"Hard": "hElo", "Clay": "cElo", "Grass": "gElo"}
    try:
        return float(df_jogador[col_map[superficie_en]])
    except:
        return float(df_jogador.get("Elo", 1500))

# ===== Parâmetros globais =====

TOLERANCIA = 1e-6
VALOR_MIN = 0.045
VALOR_MAX = 0.275
ODD_MIN = 1.425
ODD_MAX = 3.15

# ===== Histórico de apostas na sessão =====

if "historico_apostas" not in st.session_state:
    st.session_state["historico_apostas"] = []

def calcular_retorno(aposta):
    resultado = aposta.get("resultado", "")
    valor_apostado = aposta.get("valor_apostado", 0.0)
    odd = aposta.get("odd", 0.0)
    if resultado == "ganhou":
        return valor_apostado * odd
    elif resultado == "cashout":
        # Exemplo: cashout retorna 50% do valor apostado
        return valor_apostado * 0.5
    else:
        return 0.0

# ===== Sidebar =====

with st.sidebar:
    st.header("⚙️ Definições gerais")
    tipo_competicao = st.selectbox("Escolher competição", ["ATP", "WTA"])
    superficie_pt = st.selectbox("Superfície", list(superficies_map.keys()), index=0)
    btn_atualizar = st.button("🔄 Atualizar Dados", type="primary")

if btn_atualizar:
    st.cache_data.clear()
    st.experimental_rerun()

superficie_en = superficies_map[superficie_pt]

# ===== Dados principais =====

torneios = obter_torneios(tipo=tipo_competicao)
if not torneios:
    st.error(f"Não foi possível obter torneios ativos para {tipo_competicao}.")
    st.stop()
torneio_nomes = [t['nome'] for t in torneios]

torneio_selec = st.selectbox(f"Selecionar Torneio {tipo_competicao}", torneio_nomes)
url_torneio_selec = next(t['url'] for t in torneios if t['nome'] == torneio_selec)

with st.spinner(f"Carregando bases Elo e yElo para {tipo_competicao}..."):
    elo_df = cache_elo(tipo=tipo_competicao)
    yelo_df = cache_yelo(tipo=tipo_competicao)
if elo_df is None or yelo_df is None or elo_df.empty or yelo_df.empty:
    st.error(f"Erro ao carregar bases Elo/yElo para {tipo_competicao}.")
    st.stop()

with st.spinner(f"Carregando jogos do torneio {torneio_selec}..."):
    jogos = obter_jogos_do_torneio(url_torneio_selec)
if not jogos:
    st.warning("Nenhum jogo encontrado neste torneio.")
    st.stop()

# ===== TABS =====

tab_manual, tab_auto, tab_hist = st.tabs([f"{tipo_competicao} - Análise Manual",
                                         f"{tipo_competicao} - Análise Automática",
                                         "Histórico"])

# ===== TAB MANUAL =====
with tab_manual:
    st.header(f"Análise Manual de Jogos {tipo_competicao}")

    jogo_selecionado_label = st.selectbox("Selecionar jogo:", [j['label'] for j in jogos])
    selecionado = next(j for j in jogos if j['label'] == jogo_selecionado_label)

    odd_a_input = st.number_input(f"Odd para {selecionado['jogador_a']}", value=selecionado['odd_a'] or 1.80, step=0.01)
    odd_b_input = st.number_input(f"Odd para {selecionado['jogador_b']}", value=selecionado['odd_b'] or 2.00, step=0.01)

    # Escolha qual jogador aposta A ou B (útil para registrar correta aposta)
    jogador_apostar = st.radio("Selecione o jogador para apostar", (selecionado['jogador_a'], selecionado['jogador_b']))

    idx_a = match_nome(selecionado['jogador_a'], elo_df['Player'])
    idx_b = match_nome(selecionado['jogador_b'], elo_df['Player'])
    if idx_a is None:
        st.error(f"Não encontrei Elo para: {selecionado['jogador_a']}")
        st.stop()
    if idx_b is None:
        st.error(f"Não encontrei Elo para: {selecionado['jogador_b']}")
        st.stop()
    dados_a = elo_df.loc[idx_a]
    dados_b = elo_df.loc[idx_b]

    yelo_a = encontrar_yelo(selecionado['jogador_a'], yelo_df)
    yelo_b = encontrar_yelo(selecionado['jogador_b'], yelo_df)
    if yelo_a is None or yelo_b is None:
        st.error("Não consegui encontrar yElo para um dos jogadores.")
        st.stop()

    try:
        geral_a = float(dados_a['Elo'])
        esp_a = elo_por_superficie(dados_a, superficie_en)
        yelo_a_f = float(yelo_a)
        elo_final_a = (esp_a / geral_a) * yelo_a_f

        geral_b = float(dados_b['Elo'])
        esp_b = elo_por_superficie(dados_b, superficie_en)
        yelo_b_f = float(yelo_b)
        elo_final_b = (esp_b / geral_b) * yelo_b_f
    except:
        st.warning("Erro ao calcular Elo final.")
        st.stop()

    prob_a = elo_prob(elo_final_a, elo_final_b)
    prob_b = 1 - prob_a

    odd_a = float(odd_a_input)
    odd_b = float(odd_b_input)

    raw_p_a = 1 / odd_a
    raw_p_b = 1 / odd_b
    soma_raw = raw_p_a + raw_p_b
    corr_p_a = raw_p_a / soma_raw
    corr_p_b = raw_p_b / soma_raw
    corr_odd_a = 1 / corr_p_a
    corr_odd_b = 1 / corr_p_b

    valor_a = value_bet(prob_a, corr_odd_a)
    valor_b = value_bet(prob_b, corr_odd_b)

    valor_a_arred = round(valor_a, 6)
    valor_b_arred = round(valor_b, 6)

    stake_a = stake_por_faixa(valor_a_arred)
    stake_b = stake_por_faixa(valor_b_arred)

    stake_usar = stake_a if jogador_apostar == selecionado['jogador_a'] else stake_b
    odd_usar = odd_a if jogador_apostar == selecionado['jogador_a'] else odd_b
    valor_usar = valor_a if jogador_apostar == selecionado['jogador_a'] else valor_b

    st.divider()
    colA, colB = st.columns(2)
    with colA:
        st.metric("Prob. vitória (A)", f"{prob_a*100:.1f}%")
        st.metric("Valor esperado (A)", f"{valor_a*100:.1f}%")
        if ODD_MAX >= odd_a >= ODD_MIN and (VALOR_MIN - TOLERANCIA) <= valor_a_arred <= (VALOR_MAX + TOLERANCIA):
            classe_stake = "stake-low" if stake_a == 5 else ("stake-mid" if stake_a == 7.5 else "stake-high" if stake_a == 10 else "")
            st.markdown(f"<span class='faixa-stake {classe_stake}'>Stake recomendada: €{stake_a:.2f}</span>", unsafe_allow_html=True)
            st.success("Valor positivo ✅")
        else:
            st.error("Sem valor")
    with colB:
        st.metric("Prob. vitória (B)", f"{prob_b*100:.1f}%")
        st.metric("Valor esperado (B)", f"{valor_b*100:.1f}%")
        if ODD_MAX >= odd_b >= ODD_MIN and (VALOR_MIN - TOLERANCIA) <= valor_b_arred <= (VALOR_MAX + TOLERANCIA):
            classe_stake = "stake-low" if stake_b == 5 else ("stake-mid" if stake_b == 7.5 else "stake-high" if stake_b == 10 else "")
            st.markdown(f"<span class='faixa-stake {classe_stake}'>Stake recomendada: €{stake_b:.2f}</span>", unsafe_allow_html=True)
            st.success("Valor positivo ✅")
        else:
            st.error("Sem valor")

    # Botão para registrar aposta direto da análise manual
    if st.button("Registrar esta aposta"):
        aposta = {
            "data": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "evento": selecionado['label'],
            "aposta": jogador_apostar,
            "odd": odd_usar,
            "valor_apostado": stake_usar,
            "stake": stake_usar,
            "resultado": ""
        }
        st.session_state["historico_apostas"].append(aposta)
        st.success(f"Aposta em {jogador_apostar} registrada com odd {odd_usar} e stake €{stake_usar:.2f}")

    st.markdown('<div class="custom-sep"></div>', unsafe_allow_html=True)

# ===== TAB AUTOMÁTICO =====
with tab_auto:
    st.header(f"Análise Automática de Jogos {tipo_competicao} — Valor Positivo")
    resultados = []
    for jogo in jogos:
        jogador_a = jogo["jogador_a"]
        jogador_b = jogo["jogador_b"]
        oA = jogo["odd_a"] or 1.80
        oB = jogo["odd_b"] or 2.00

        idxA = match_nome(jogador_a, elo_df["Player"])
        idxB = match_nome(jogador_b, elo_df["Player"])
        if idxA is None or idxB is None:
            continue
        dA = elo_df.loc[idxA]
        dB = elo_df.loc[idxB]
        yA = encontrar_yelo(jogador_a, yelo_df)
        yB = encontrar_yelo(jogador_b, yelo_df)
        if yA is None or yB is None:
            continue

        try:
            eGA = float(dA["Elo"])
            eSA = elo_por_superficie(dA, superficie_en)
            yFA = float(yA)
            eGB = float(dB["Elo"])
            eSB = elo_por_superficie(dB, superficie_en)
            yFB = float(yB)
        except:
            continue

        eloFA = (eSA / eGA) * yFA
        eloFB = (eSB / eGB) * yFB

        pA = elo_prob(eloFA, elo
