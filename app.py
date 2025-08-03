import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from difflib import get_close_matches
import unicodedata
import importlib.util

# ===== Configuração visual =====
st.set_page_config(page_title="Tennis Value Bets", page_icon="🎾", layout="wide")
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

st.markdown('<div class="main-title">🎾 Análise de Valor em Apostas de Ténis — Torneios ATP</div>', unsafe_allow_html=True)

# ==== Mapeamentos superfícies PT -> EN e inverso ====
superficies_map = {"Piso Duro": "Hard", "Terra": "Clay", "Relva": "Grass"}
superficies_map_inv = {v: k for k, v in superficies_map.items()}

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
    st.error("Dependência obrigatória 'html5lib' ausente. Instale com:\npip install html5lib")
    st.stop()

# ==== Funções utilitárias e de dados ====

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

def obter_torneios_atp_ativos():
    url = f"{BASE_URL}/matches/"
    r = requests.get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")
    torneios = []
    nomes_permitidos = [tp.casefold() for tp in TORNEIOS_PERMITIDOS]
    for a in soup.select("a[href*='/atp-men/']"):
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
        u = BASE_URL + a['href']
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

def obter_elo_table():
    url = "https://tennisabstract.com/reports/atp_elo_ratings.html"
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
        st.error(f"Erro ao obter Elo table: {e}")
        return None

def obter_yelo_table():
    url = "https://tennisabstract.com/reports/atp_season_yelo_ratings.html"
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
                df = df.rename(columns={'player':'Player','yelo':'yElo'})
                return df[['Player','yElo']]
    except Exception as e:
        st.error(f"Erro ao obter Yelo table: {e}")
        return None

@st.cache_data(show_spinner=False)
def cache_elo():
    return obter_elo_table()

@st.cache_data(show_spinner=False)
def cache_yelo():
    return obter_yelo_table()

def elo_prob(elo_a, elo_b):
    return 1/(1 + 10**((elo_b - elo_a)/400))

def value_bet(prob, odd):
    return prob * odd - 1

def stake_por_faixa(valor):
    # Ajustado para os novos valores pedidos
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
    exact_match = df_norm[df_norm==nome_norm]
    if not exact_match.empty:
        return exact_match.index[0]
    else:
        matches = get_close_matches(nome_norm, df_norm.tolist(), n=1, cutoff=0.8)
        if matches:
            return df_norm[df_norm==matches[0]].index[0]
    return None

def elo_por_superficie(df_jogador, superficie_en):
    col_map = {"Hard": "hElo", "Clay": "cElo", "Grass": "gElo"}
    return float(df_jogador[col_map[superficie_en]])

# ========= INTERFACE ==========
torneios = obter_torneios_atp_ativos()
if not torneios:
    st.error("Não foi possível obter torneios ATP ativos.")
    st.stop()
torneio_nomes = [t['nome'] for t in torneios]

with st.sidebar:
    st.header("⚙️ Definições")
    st.caption("Personalize filtros e visualização aqui.")
    st.divider()
    torneio_selec = st.selectbox("Selecionar Torneio", torneio_nomes)
    superficie_pt = st.selectbox("Superfície", list(superficies_map.keys()), index=0)
    atualizar = st.button("🔄 Atualizar Dados", type="primary")

superficie_en = superficies_map[superficie_pt]

if atualizar:
    st.cache_data.clear()
    st.success("Dados atualizados!")

url_torneio_selec = next(t['url'] for t in torneios if t['nome'] == torneio_selec)

with st.spinner("Carregando bases Elo e yElo..."):
    elo_df = cache_elo()
    yelo_df = cache_yelo()
if elo_df is None or yelo_df is None or elo_df.empty or yelo_df.empty:
    st.error("Erro ao carregar bases Elo/yElo.")
    st.stop()

with st.spinner(f"Carregando jogos do torneio {torneio_selec}..."):
    jogos = obter_jogos_do_torneio(url_torneio_selec)
if not jogos:
    st.warning("Nenhum jogo encontrado neste torneio.")
    st.stop()

tab1, tab2 = st.tabs(["🔎 Análise Manual", "🤖 Análise Automática"])

# Tolerância para arredondamento comparações floats
TOLERANCIA = 1e-6

# Limites ajustados
VALOR_MIN = 0.045
VALOR_MAX = 0.275
ODD_MIN = 1.425
ODD_MAX = 3.15

# ==== TAB1: Análise Manual ====
with tab1:
    st.header("Selecione o jogo manualmente")
    jogo_selecionado_label = st.selectbox("Jogo:", [j['label'] for j in jogos])
    selecionado = next(j for j in jogos if j['label'] == jogo_selecionado_label)

    odd_a_input = st.number_input(f"Odd para {selecionado['jogador_a']}", value=selecionado['odd_a'] or 1.80, step=0.01)
    odd_b_input = st.number_input(f"Odd para {selecionado['jogador_b']}", value=selecionado['odd_b'] or 2.00, step=0.01)

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

    # === INCLUINDO O EXPANDER DE DETALHES DOS ELOS E CÁLCULOS ===
    with st.expander("📈 Detalhes Elo e Cálculos"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"### {selecionado['jogador_a']}")
            st.write(f"Elo Geral: {geral_a:.2f}")
            st.write(f"Elo {superficie_pt}: {esp_a:.2f}")
            st.write(f"yElo: {yelo_a_f:.2f}")
            st.write(f"Elo Final calculado: {elo_final_a:.2f}")
        with col2:
            st.write(f"### {selecionado['jogador_b']}")
            st.write(f"Elo Geral: {geral_b:.2f}")
            st.write(f"Elo {superficie_pt}: {esp_b:.2f}")
            st.write(f"yElo: {yelo_b_f:.2f}")
            st.write(f"Elo Final calculado: {elo_final_b:.2f}")

    with st.expander("🔬 Explicação dos cálculos e detalhes avançados"):
        st.markdown("""
        - O sistema Elo estima a força relativa dos jogadores.
        - A probabilidade do Jogador A vencer o Jogador B é:
          
          $$ P(A) = \\frac{1}{1 + 10^{\\frac{Elo_B - Elo_A}{400}}} $$
        
        - Odds são corrigidas para retirar margem das casas.
        - Valor esperado é calculado como: 
        
          $$ Valor = Probabilidade \\times Odd_{corrigida} - 1 $$
        
        - A stake recomendada depende do valor esperado:
        
          | Intervalo Valor | Stake (€) |
          |-----------------|-----------|
          | 4,5% a 11%      | 5         |
          | 11% a 18%       | 7.5       |
          | 18% a 27,5%     | 10        |
        """)

    st.markdown('<div class="custom-sep"></div>', unsafe_allow_html=True)

# ==== TAB2: Análise automática ====
with tab2:
    st.header("Jogos com valor positivo")
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
            "Odd A": f"{oA:.2f}",
            "Odd B": f"{oB:.2f}",
            "Valor A %": f"{valA*100:.1f}%",
            "Valor B %": f"{valB*100:.1f}%",
            "Stake A (€)": f"{stakeA:.2f}",
            "Stake B (€)": f"{stakeB:.2f}",
            "Valor A (raw)": valA,
            "Valor B (raw)": valB,
        })
    if not resultados:
        st.info("Nenhum jogo com valor possível analisado.")
    else:
        df = pd.DataFrame(resultados)

        # Arredondar para eliminar problemas de flutuação
        df["Valor A (raw)"] = df["Valor A (raw)"].round(6)
        df["Valor B (raw)"] = df["Valor B (raw)"].round(6)

        df["Odd A"] = df["Odd A"].astype(float)
        df["Odd B"] = df["Odd B"].astype(float)

        df_valor_positivo = df[
            ((df["Valor A (raw)"] >= VALOR_MIN) & (df["Valor A (raw)"] <= VALOR_MAX) & (df["Odd A"] >= ODD_MIN) & (df["Odd A"] <= ODD_MAX)) |
            ((df["Valor B (raw)"] >= VALOR_MIN) & (df["Valor B (raw)"] <= VALOR_MAX) & (df["Odd B"] >= ODD_MIN) & (df["Odd B"] <= ODD_MAX))
        ]

        def highlight_stakes(val):
            if val == "5.00":
                return "background-color:#fff5cc;"
            elif val == "7.50":
                return "background-color:#fff5cc;"
            elif val == "10.00":
                return "background-color:#fff5cc;"
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

        styled = df_valor_positivo.style.apply(highlight_valor, axis=1)\
                                     .applymap(highlight_stakes, subset=["Stake A (€)", "Stake B (€)"])
        st.dataframe(styled.format(precision=2), use_container_width=True)

    st.caption("Legenda stake: 5€ [baixa], 7.5€ [média], 10€ [alta]")

st.divider()
st.caption("Fontes: tennisexplorer.com e tennisabstract.com | App experimental — design demo")
