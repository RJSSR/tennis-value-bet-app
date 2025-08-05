import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from difflib import get_close_matches
import unicodedata
import os
from io import StringIO
import matplotlib.pyplot as plt
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode

# ===== Parâmetros globais =====
TOLERANCIA = 1e-6
VALOR_MIN = 0.045
VALOR_MAX = 0.275
ODD_MIN = 1.425
ODD_MAX = 3.15

BASE_URL = "https://www.tennisexplorer.com"
HISTORICO_CSV = "historico_apostas.csv"

superficies_map = {"Piso Duro": "Hard", "Terra": "Clay", "Relva": "Grass"}

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
    s = "".join(c for c in unicodedata.normalize("NFD", nome) if unicodedata.category(c) != "Mn")
    return s.strip().casefold()

@st.cache_data(show_spinner=False)
def obter_torneios(tipo="ATP"):
    try:
        url = f"{BASE_URL}/matches/"
        r = requests.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        torneios = []
        permitidos = TORNEIOS_ATP_PERMITIDOS if tipo == "ATP" else TORNEIOS_WTA_PERMITIDOS
        nomes_permitidos = [t.casefold() for t in permitidos]

        # Busca flexível por href com '/atp' ou '/wta'
        for a in soup.find_all("a", href=True):
            nome = a.text.strip()
            href = a["href"]

            if tipo == "ATP" and ("/atp" in href or "/atp-men" in href):
                if nome.casefold() in nomes_permitidos:
                    url_full = BASE_URL + href if href.startswith("/") else href
                    if url_full not in {t["url"] for t in torneios}:
                        torneios.append({"nome": nome, "url": url_full})
            elif tipo == "WTA" and ("/wta" in href or "/wta-women" in href):
                if nome.casefold() in nomes_permitidos:
                    url_full = BASE_URL + href if href.startswith("/") else href
                    if url_full not in {t["url"] for t in torneios}:
                        torneios.append({"nome": nome, "url": url_full})
        return torneios
    except Exception as e:
        st.error(f"Erro ao obter torneios {tipo}: {e}")
        return []

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
        u = BASE_URL + a["href"] if a["href"].startswith("/") else a["href"]
        jogador_map[n] = u
    for table in tables:
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
            jogos.append(
                {
                    "label": f"{nome1} vs {nome2}",
                    "jogador_a": nome1,
                    "jogador_b": nome2,
                    "odd_a": odd_a,
                    "odd_b": odd_b,
                }
            )
        if jogos:
            break
    return jogos

def obter_elo_table(tipo="ATP"):
    url = (
        "https://tennisabstract.com/reports/atp_elo_ratings.html"
        if tipo == "ATP"
        else "https://tennisabstract.com/reports/wta_elo_ratings.html"
    )
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        dfs = pd.read_html(StringIO(str(soup)), flavor="bs4")
        for df in dfs:
            cols = [str(c).strip() for c in df.columns]
            if "Player" in cols:
                df.columns = cols
                df = df.dropna(subset=["Player"])
                return df
    except Exception as e:
        st.error(f"Erro ao obter Elo table {tipo}: {e}")
        return None

def obter_yelo_table(tipo="ATP"):
    url = (
        "https://tennisabstract.com/reports/atp_season_yelo_ratings.html"
        if tipo == "ATP"
        else "https://tennisabstract.com/reports/wta_season_yelo_ratings.html"
    )
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        dfs = pd.read_html(StringIO(str(soup)), flavor="bs4")
        for df in dfs:
            cols = [str(c).strip().lower() for c in df.columns]
            if "player" in cols and "yelo" in cols:
                df.columns = cols
                df = df.dropna(subset=["player"])
                df = df.rename(columns={"player": "Player", "yelo": "yElo"})
                return df[["Player", "yElo"]]
    except Exception as e:
        st.error(f"Erro ao obter yElo table {tipo}: {e}")
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
    if valor < VALOR_MIN or valor > VALOR_MAX:
        return 0.0
    elif valor < 0.11:
        return 5.0
    elif valor < 0.18:
        return 7.5
    else:
        return 10.0

def encontrar_yelo(nome, yelo_df):
    nrm_nome = normalizar_nome(nome)
    ys = yelo_df["Player"].dropna().tolist()
    nrm_ys = [normalizar_nome(x) for x in ys]
    for idx, val in enumerate(nrm_ys):
        if val == nrm_nome:
            return yelo_df.iloc[idx]["yElo"]
    matches = get_close_matches(nrm_nome, nrm_ys, n=1, cutoff=0.8)
    if matches:
        idx = nrm_ys.index(matches[0])
        return yelo_df.iloc[idx]["yElo"]
    return None

def match_nome(nome, df_col):
    nome_norm = normalizar_nome(nome)
    df_norm = df_col.dropna().apply(normalizar_nome)
    exact_match = df_norm[df_norm == nome_norm]
    if not exact_match.empty:
        return exact_match.index[0]
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

def carregar_historico():
    if os.path.exists(HISTORICO_CSV):
        try:
            df = pd.read_csv(HISTORICO_CSV)
            if "data" in df.columns:
                df["data"] = df["data"].astype(str)
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

def salvar_historico(df):
    df.to_csv(HISTORICO_CSV, index=False)

def calcular_retorno(aposta):
    resultado = aposta.get("resultado", "")
    valor = float(aposta.get("stake", 0.0))  # usamos stake para consistência
    odd = float(aposta.get("odd", 0.0))
    if resultado == "ganhou":
        return valor * odd
    elif resultado == "cashout":
        return valor * 0.5
    else:
        return 0.0

# --- Main app flow ---

if "historico_apostas_df" not in st.session_state:
    st.session_state["historico_apostas_df"] = carregar_historico()

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

st.markdown('<div class="main-title">🎾 Análise de Valor em Apostas de Ténis &mdash; ATP & WTA</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Definições gerais")
    tipo_competicao = st.selectbox("Escolher competição", ["ATP", "WTA"])
    torneios = obter_torneios(tipo_competicao)
    if not torneios:
        st.error(f"Não foi possível obter torneios ativos para {tipo_competicao}.")
        st.stop()
    torneio_nomes = [t["nome"] for t in torneios]
    torneio_selec = st.selectbox("Selecionar Torneio", torneio_nomes)
    superficie_pt = st.selectbox("Superfície", list(superficies_map.keys()))
    btn_atualizar = st.button("🔄 Atualizar Dados", type="primary")

if btn_atualizar:
    st.cache_data.clear()
    st.rerun()

superficie_en = superficies_map[superficie_pt]

url_torneio_selec = next(t["url"] for t in torneios if t["nome"] == torneio_selec)

with st.spinner(f"Carregando bases Elo e yElo para {tipo_competicao}..."):
    elo_df = cache_elo(tipo_competicao)
    yelo_df = cache_yelo(tipo_competicao)

if elo_df is None or yelo_df is None or elo_df.empty or yelo_df.empty:
    st.error(f"Erro ao carregar bases Elo/yElo para {tipo_competicao}.")
    st.stop()

with st.spinner(f"Carregando jogos do torneio {torneio_selec}..."):
    jogos = obter_jogos_do_torneio(url_torneio_selec)

if not jogos:
    st.warning("Nenhum jogo encontrado neste torneio.")
    st.stop()

tab_manual, tab_auto, tab_hist = st.tabs([
    f"{tipo_competicao} - Análise Manual",
    f"{tipo_competicao} - Análise Automática",
    "Histórico"
])

# --- ABA MANUAL ---
with tab_manual:
    st.header(f"Análise Manual de Jogos {tipo_competicao}")
    
    jogo_selecionado_label = st.selectbox("Selecionar jogo:", [j["label"] for j in jogos])
    selecionado = next(j for j in jogos if j["label"] == jogo_selecionado_label)
    
    odd_a_input = st.number_input(f"Odd para {selecionado['jogador_a']}", value=selecionado["odd_a"] or 1.80, step=0.01)
    odd_b_input = st.number_input(f"Odd para {selecionado['jogador_b']}", value=selecionado["odd_b"] or 2.00, step=0.01)
    
    jogador_apostar = st.radio("Selecione o jogador para apostar", (selecionado["jogador_a"], selecionado["jogador_b"]))
    
    idx_a = match_nome(selecionado["jogador_a"], elo_df["Player"])
    idx_b = match_nome(selecionado["jogador_b"], elo_df["Player"])
    if idx_a is None or idx_b is None:
        st.error("Não foi possível encontrar Elo para um dos jogadores.")
        st.stop()
    
    dados_a = elo_df.loc[idx_a]
    dados_b = elo_df.loc[idx_b]
    
    yelo_a = encontrar_yelo(selecionado["jogador_a"], yelo_df)
    yelo_b = encontrar_yelo(selecionado["jogador_b"], yelo_df)
    if yelo_a is None or yelo_b is None:
        st.error("Não consegui encontrar yElo para um dos jogadores.")
        st.stop()
    
    try:
        geral_a = float(dados_a["Elo"])
        esp_a = elo_por_superficie(dados_a, superficie_en)
        yelo_a_f = float(yelo_a)
        elo_final_a = (esp_a / geral_a) * yelo_a_f

        geral_b = float(dados_b["Elo"])
        esp_b = elo_por_superficie(dados_b, superficie_en)
        yelo_b_f = float(yelo_b)
        elo_final_b = (esp_b / geral_b) * yelo_b_f
    except Exception as e:
        st.warning(f"Erro ao calcular Elo final: {e}")
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
    
    stake_usar = stake_a if jogador_apostar == selecionado["jogador_a"] else stake_b
    odd_usar = odd_a if jogador_apostar == selecionado["jogador_a"] else odd_b
    
    st.divider()
    colA, colB = st.columns(2)
    with colA:
        st.metric("Prob. vitória (A)", f"{prob_a*100:.1f}%")
        st.metric("Valor esperado (A)", f"{valor_a*100:.1f}%")
        if (ODD_MAX >= odd_a >= ODD_MIN and (VALOR_MIN - TOLERANCIA) <= valor_a_arred <= (VALOR_MAX + TOLERANCIA)):
            classe_stake = ("stake-low" if stake_a == 5 else "stake-mid" if stake_a == 7.5 else "stake-high" if stake_a == 10 else "")
            st.markdown(f"<span class='faixa-stake {classe_stake}'>Stake recomendada: €{stake_a:.2f}</span>", unsafe_allow_html=True)
            st.success("Valor positivo ✅")
        else:
            st.error("Sem valor")
    with colB:
        st.metric("Prob. vitória (B)", f"{prob_b*100:.1f}%")
        st.metric("Valor esperado (B)", f"{valor_b*100:.1f}%")
        if (ODD_MAX >= odd_b >= ODD_MIN and (VALOR_MIN - TOLERANCIA) <= valor_b_arred <= (VALOR_MAX + TOLERANCIA)):
            classe_stake = ("stake-low" if stake_b == 5 else "stake-mid" if stake_b == 7.5 else "stake-high" if stake_b == 10 else "")
            st.markdown(f"<span class='faixa-stake {classe_stake}'>Stake recomendada: €{stake_b:.2f}</span>", unsafe_allow_html=True)
            st.success("Valor positivo ✅")
        else:
            st.error("Sem valor")

    if st.button("Registrar esta aposta"):
        nova_aposta = {
            "data": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "evento": selecionado["label"],
            "aposta": jogador_apostar,
            "odd": odd_usar,
            "valor_apostado": stake_usar,
            "stake": stake_usar,
            "resultado": "",
            "competicao": tipo_competicao,
        }
        novo_df = pd.DataFrame([nova_aposta])
        st.session_state["historico_apostas_df"] = pd.concat([st.session_state["historico_apostas_df"], novo_df], ignore_index=True)
        salvar_historico(st.session_state["historico_apostas_df"])
        st.success(f"Aposta registrada para {jogador_apostar} com odd {odd_usar} e stake €{stake_usar:.2f}")

# --- ABA AUTOMÁTICA ---
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
        pA = elo_prob(eloFA, eloFB)
        pB = 1 - pA
        rawpA = 1 / oA
        rawpB = 1 / oB
        sRaw = rawpA + rawpB
        cA = rawpA / sRaw
        cB = rawpB / sRaw
        corr_oA = 1 / cA
        corr_oB = 1 / cB
        valA = value_bet(pA, corr_oA)
        valB = value_bet(pB, corr_oB)
        stakeA = stake_por_faixa(valA)
        stakeB = stake_por_faixa(valB)
        resultados.append({
            "Jogo": f"{jogador_a} vs {jogador_b}",
            "Odd A": oA,
            "Odd B": oB,
            "Valor A %": f"{valA*100:.1f}%",
            "Valor B %": f"{valB*100:.1f}%",
            "Stake A (€)": f"{stakeA:.2f}",
            "Stake B (€)": f"{stakeB:.2f}",
            "Valor A (raw)": valA,
            "Valor B (raw)": valB,
            "Jogador A": jogador_a,
            "Jogador B": jogador_b,
            "Stake A raw": stakeA,
            "Stake B raw": stakeB,
            "Odd A raw": oA,
            "Odd B raw": oB,
        })
    if not resultados:
        st.info("Nenhum jogo com valor possível analisado.")
    else:
        df = pd.DataFrame(resultados)
        df_valor_positivo = df[
            ((df["Valor A (raw)"] >= VALOR_MIN) & (df["Valor A (raw)"] <= VALOR_MAX) & (df["Odd A"] >= ODD_MIN) & (df["Odd A"] <= ODD_MAX)) |
            ((df["Valor B (raw)"] >= VALOR_MIN) & (df["Valor B (raw)"] <= VALOR_MAX) & (df["Odd B"] >= ODD_MIN) & (df["Odd B"] <= ODD_MAX))
        ]

        def highlight_stakes(val):
            if val in ["5.00", "7.50", "10.00"]:
                return "background-color:#8ef58e;"
            return ""

        def highlight_valor(row):
            styles = [""] * len(row)
            try:
                idx_val_a = row.index.get_loc("Valor A %")
                idx_val_b = row.index.get_loc("Valor B %")
                if VALOR_MIN <= row["Valor A (raw)"] <= VALOR_MAX and ODD_MIN <= row["Odd A"] <= ODD_MAX:
                    styles[idx_val_a] = "background-color: #8ef58e;"
                if VALOR_MIN <= row["Valor B (raw)"] <= VALOR_MAX and ODD_MIN <= row["Odd B"] <= ODD_MAX:
                    styles[idx_val_b] = "background-color: #8ef58e;"
            except KeyError:
                pass
            return styles

        styled = df_valor_positivo.style.apply(highlight_valor, axis=1).applymap(highlight_stakes, subset=["Stake A (€)", "Stake B (€)"])
        st.dataframe(styled.format(precision=2), use_container_width=True)

        st.markdown("---")
        st.subheader("Registrar apostas automáticas")

        for idx, row in df_valor_positivo.iterrows():
            col1, col2 = st.columns(2)
            with col1:
                if float(row["Stake A (€)"]) > 0:
                    if st.button(f"Registrar aposta A em {row['Jogo']}", key=f"reg_auto_a_{idx}"):
                        nova_aposta = {
                            "data": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "evento": row["Jogo"],
                            "aposta": row["Jogador A"],
                            "odd": row["Odd A raw"],
                            "valor_apostado": row["Stake A raw"],
                            "stake": row["Stake A raw"],
                            "resultado": "",
                            "competicao": tipo_competicao,
                        }
                        novo_df = pd.DataFrame([nova_aposta])
                        st.session_state["historico_apostas_df"] = pd.concat([st.session_state["historico_apostas_df"], novo_df], ignore_index=True)
                        salvar_historico(st.session_state["historico_apostas_df"])
                        st.success(f"Aposta {nova_aposta['aposta']} registrada automaticamente (Jogador A)")
            with col2:
                if float(row["Stake B (€)"]) > 0:
                    if st.button(f"Registrar aposta B em {row['Jogo']}", key=f"reg_auto_b_{idx}"):
                        nova_aposta = {
                            "data": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "evento": row["Jogo"],
                            "aposta": row["Jogador B"],
                            "odd": row["Odd B raw"],
                            "valor_apostado": row["Stake B raw"],
                            "stake": row["Stake B raw"],
                            "resultado": "",
                            "competicao": tipo_competicao,
                        }
                        novo_df = pd.DataFrame([nova_aposta])
                        st.session_state["historico_apostas_df"] = pd.concat([st.session_state["historico_apostas_df"], novo_df], ignore_index=True)
                        salvar_historico(st.session_state["historico_apostas_df"])
                        st.success(f"Aposta {nova_aposta['aposta']} registrada automaticamente (Jogador B)")

# --- ABA HISTÓRICO ---
with tab_hist:
    st.header("📊 Histórico de Apostas e Retorno")

    df_hist = st.session_state["historico_apostas_df"].copy()

    if df_hist.empty:
        st.info("Nenhuma aposta registrada.")
    else:
        cols = df_hist.columns.tolist()
        for c in ["valor_apostado"]:
            if c in cols:
                cols.remove(c)

        nova_ordem = ["data", "competicao"] + [c for c in cols if c not in ["data", "competicao"]]
        df_hist = df_hist[nova_ordem].copy()

        resultados_validos = ["", "ganhou", "perdeu", "cashout"]

        gb = GridOptionsBuilder.from_dataframe(df_hist)

        gb.configure_column("data", header_name="Data")
        gb.configure_column("competicao", header_name="Competição")
        gb.configure_column("evento", header_name="Evento")
        gb.configure_column("aposta", header_name="Aposta")
        gb.configure_column("odd", header_name="Odd")
        gb.configure_column("stake", header_name="Stake")

        gb.configure_column(
            "resultado",
            editable=True,
            cellEditor="agSelectCellEditor",
            cellEditorParams={"values": resultados_validos},
            cellEditorPopup=True,
            header_name="Resultado",
        )

        # Permite seleção múltipla com checkboxes
        gb.configure_selection(selection_mode="multiple", use_checkbox=True)
        grid_options = gb.build()

        response = AgGrid(
            df_hist,
            gridOptions=grid_options,
            allow_unsafe_jscode=True,
            enable_enterprise_modules=False,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            height=400,
            fit_columns_on_grid_load=True,
            reload_data=True,
            theme="fresh",
        )



# Garante que a estrutura está inicializada
if "historico_apostas_df" not in st.session_state:
    st.session_state["historico_apostas_df"] = pd.DataFrame()

# Protege o acesso ao response
selected = response.get("selected_rows", []) if isinstance(response, dict) else []

# Captura as linhas selecionadas sempre após o AgGrid
selected = response.get("selected_rows", []) if response else []

# Mostra na interface quantas apostas estão selecionadas (útil para debug)
st.write(f"Apostas selecionadas: {len(selected)}")

# Botão para remover apostas selecionadas
if st.button("❌ Remover aposta(s) selecionada(s)", type="primary"):
    if len(selected) == 0:
        st.warning("Nenhuma aposta foi selecionada.")
    else:
        df = st.session_state["historico_apostas_df"].reset_index(drop=True)
        for data in selected:
            if not isinstance(data, dict):
                st.warning(f"Dado inesperado em 'selected_rows': {data} (tipo: {type(data)})")
                continue

            row_data = str(data.get("data", "")).strip()
            cond = (df["data"].astype(str).str.strip() == row_data)
            cond &= (df["evento"] == data.get("evento", ""))
            cond &= (df["aposta"] == data.get("aposta", ""))
            try:
                data_odd = float(data.get("odd", 0))
                cond &= (abs(df["odd"].astype(float) - data_odd) < 1e-9)
            except Exception as e:
                st.warning(f"Erro ao processar odd: {e}")
                cond &= False

            indices = df[cond].index
            if not indices.empty:
                df = df.drop(indices)

        st.session_state["historico_apostas_df"] = df.reset_index(drop=True)
        salvar_historico(st.session_state["historico_apostas_df"])
        st.success("Aposta(s) removida(s) com sucesso.")
        st.rerun()  # ou st.rerun() conforme tua versão do Streamlit

# Também podes atualizar o histórico se o usuário editar direto no grid
if response["data"] is not None:
    df_updated = pd.DataFrame(response["data"])

    # Remove colunas extras que não queres guardar, ex:
    if "remove" in df_updated.columns:
        df_updated = df_updated.drop(columns=["remove"])

    df_hist_str = st.session_state["historico_apostas_df"].astype(str)
    df_updated_str = df_updated.astype(str)

    if not df_updated_str.equals(df_hist_str):
        st.session_state["historico_apostas_df"] = df_updated
        salvar_historico(df_updated)

# Análise e Métricas
df_hist_resultado = st.session_state["historico_apostas_df"]
df_hist_resultado = df_hist_resultado[
    df_hist_resultado["resultado"].notna() & (df_hist_resultado["resultado"].str.strip() != "")
].copy()

df_hist_resultado["stake"] = pd.to_numeric(df_hist_resultado["stake"], errors="coerce").fillna(0)
df_hist_resultado["odd"] = pd.to_numeric(df_hist_resultado["odd"], errors="coerce").fillna(0)

def calcular_retorno(row):
    if row["resultado"] == "ganhou":
        return row["stake"] * row["odd"]
    elif row["resultado"] == "cashout":
        return row["stake"] * 0.5
    else:
        return 0

num_apostas = len(df_hist_resultado)
apostas_ganhas = (df_hist_resultado["resultado"] == "ganhou").sum()
apostas_perdidas = (df_hist_resultado["resultado"] == "perdeu").sum()
montante_investido = df_hist_resultado["stake"].sum()
montante_ganho = df_hist_resultado.apply(calcular_retorno, axis=1).sum()
yield_percent = ((montante_ganho - montante_investido) / montante_investido * 100) if montante_investido > 0 else 0.0

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Número de Apostas", num_apostas)
    st.metric("Apostas Ganhas", apostas_ganhas)
    st.metric("Apostas Perdidas", apostas_perdidas)
with col2:
    st.metric("Montante Investido (€)", f"€{montante_investido:.2f}")
    st.metric("Montante Ganho (€)", f"€{montante_ganho:.2f}")
with col3:
    st.metric("Yield (%)", f"{yield_percent:.2f}%")

# Gráfico de lucro acumulado por mês
df_lucro = df_hist_resultado.copy()
if not df_lucro.empty:
    def calc_lucro(row):
        if row["resultado"] == "ganhou":
            return row["stake"] * row["odd"] - row["stake"]
        elif row["resultado"] == "cashout":
            return row["stake"] * 0.5 - row["stake"]
        else:
            return -row["stake"]

    df_lucro["lucro"] = df_lucro.apply(calc_lucro, axis=1)
    df_lucro["ano_mes"] = pd.to_datetime(df_lucro["data"], errors="coerce").dt.strftime('%Y-%m')
    df_lucro = df_lucro[df_lucro["ano_mes"].notna()]

    grupo = df_lucro.groupby(["ano_mes", "competicao"])["lucro"].sum().reset_index()
    tabela = grupo.pivot(index="ano_mes", columns="competicao", values="lucro").fillna(0).sort_index()

    if "ATP" not in tabela.columns:
        tabela["ATP"] = 0
    if "WTA" not in tabela.columns:
        tabela["WTA"] = 0

    tabela["ATP_acum"] = tabela["ATP"].cumsum()
    tabela["WTA_acum"] = tabela["WTA"].cumsum()

    fig, ax = plt.subplots(figsize=(8, 4))
    tabela[["ATP_acum", "WTA_acum"]].plot(ax=ax)
    ax.set_title("Lucro Acumulado por Mês (ATP / WTA)")
    ax.set_ylabel("Lucro acumulado (€)")
    ax.set_xlabel("Ano-Mês")
    ax.legend(["ATP", "WTA"])
    plt.xticks(rotation=45)
    st.pyplot(fig)
else:
    st.info("Ainda não há dados suficientes para gerar o gráfico de lucro acumulado por mês.")

st.divider()
st.caption("Fontes: tennisexplorer.com e tennisabstract.com | App experimental — design demo")
