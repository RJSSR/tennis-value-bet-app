import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from difflib import get_close_matches
import unicodedata
import importlib.util

# ======== CSS MODERNO E LIMPO ========
st.markdown("""
    <style>
    body, .main {
        background: linear-gradient(120deg, #e3ecfc 0%, #f8fdff 100%);
    }
    div[data-testid="stSidebar"] {
        background: #11336b;
        color: white;
        min-width: 225px;
    }
    .stButton>button {
        background-color:#3164DD; color:white; font-weight:bold; border-radius:8px;
        border:none; padding:7px 0px;
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #254b9c;
    }
    .stDataFrame, .stTable {
        background: #f9fbfd !important;
        border-radius: 10px;
    }
    .stMetric {
        background: #f5f7fb; border-radius: 15px; padding:17px; min-height: 90px;
        box-shadow: 0 2px 8px rgba(80,110,200,.07);
    }
    header, h1, h2, h3 {
        color: #11336b;
        font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif !important;
    }
    .stAlert-success {background-color: #dbffe2;border-left: 7px solid #18af22;}
    .stAlert-error {background-color: #ffeaea;border-left:7px solid #f55;}
    .stAlert-info, .stAlert-warning {border-radius: 8px;}
    .stExpanderHeader {font-weight:bold;font-size:19px;}
    .card {
        background: white;
        border-radius: 18px;
        padding: 32px 26px 20px 26px;
        box-shadow: 0 2px 18px rgba(120,136,180,0.10);
        margin-bottom:20px;
    }
    .value-highlight {background: #e4ffe5; border-radius: 10px; padding: 3px 8px; font-weight: 600;}
    .stDataFrame tbody tr:hover {background-color: #f1f5fc !important;}
    .stDataFrame tbody tr td[rowspan] {background: #e4f2ff !important;}
    </style>
""", unsafe_allow_html=True)

# ======== SIDEBAR com logo e créditos ========
with st.sidebar:
    st.markdown(
        '<div style="text-align:center;"><img src="https://www.tennisexplorer.com/img/te_logo.svg" width="110"></div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div style="font-size:18px; margin-top:20px; text-align:center; color:#dbe3f8;">' +
        'by <b>teambetting</b> experimental</div>',
        unsafe_allow_html=True
    )

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

# Dependência obrigatória
if importlib.util.find_spec("html5lib") is None:
    st.error("Dependência obrigatória 'html5lib' ausente. Instale com:\npip install html5lib")
    st.stop()

# ======== FUNÇÕES DE LIMPEZA E NOME ========
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

# ======== OBTENÇÃO DE DADOS ========
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

# ======== CÁLCULOS E MATCHES ========
def elo_prob(elo_a, elo_b):
    return 1/(1 + 10**((elo_b - elo_a)/400))

def value_bet(prob, odd):
    return prob * odd - 1

def stake_por_faixa(valor):
    if valor < 0.03 or valor > 0.25:
        return 0.0
    elif 0.03 <= valor < 0.11:
        return 5.0
    elif 0.11 <= valor < 0.18:
        return 7.5
    elif 0.18 <= valor <= 0.25:
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

superficies_map = {"Piso Duro":"Hard","Relva":"Grass","Terra Batida":"Clay"}

# ======== INTERFACE E LÓGICA PRINCIPAL ========
st.markdown('<div class="card">', unsafe_allow_html=True)

st.markdown("<h1 style='font-size:2.3em;'>🎾 ATP Bets Value & Stake Analyzer</h1>", unsafe_allow_html=True)
st.write(
    "Obtenha recomendações matemáticas sobre onde pode haver valor em apostas de ténis ATP, com base em Elo, yElo e probabilidades ajustadas. Todos os dados ao vivo e fonte aberta!"
)

with st.container():
    st.markdown("#### 👀 O que o app faz?")
    st.write("- Analisa odds, **Elo/yElo**, surface-specialty, calcula probabilidade, edge (valor) e sugere stake.")
    st.write("- Só sinaliza aposta se **odds** e **valor esperado** encaixarem em parâmetros seguros.")
    st.markdown("---")

st.markdown('</div>', unsafe_allow_html=True)

if st.button("🔄 Atualizar todos os dados", use_container_width=True):
    st.cache_data.clear()
    st.success("Dados atualizados!", icon="✅")

with st.spinner("Carregando bases..."):
    elo_df = cache_elo()
    yelo_df = cache_yelo()

if elo_df is None or yelo_df is None or elo_df.empty or yelo_df.empty:
    st.error("Erro ao carregar bases Elo/yElo.")
    st.stop()

st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("🌎 1. Escolha o Torneio ATP")
with st.spinner("Procurando torneios em andamento..."):
    torneios = obter_torneios_atp_ativos()
if not torneios:
    st.warning("Nenhum torneio ATP ativo encontrado.")
    st.stop()

nome_torneio = st.selectbox("Torneio:", [t['nome'] for t in torneios])
url_torneio = next(t['url'] for t in torneios if t['nome'] == nome_torneio)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("🛣️ 2. Superfície")
superficie_nome = st.selectbox("Superfície", list(superficies_map.keys()))
superficie = superficies_map[superficie_nome]
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("🎯 3. Escolha o Jogo")
with st.spinner(f"Carregando jogos do {nome_torneio}..."):
    jogos = obter_jogos_do_torneio(url_torneio)
if not jogos:
    st.warning("Nenhum jogo encontrado neste torneio.")
    st.stop()

selecionado_label = st.selectbox("Jogo:", [j['label'] for j in jogos])
selecionado = next(j for j in jogos if j['label'] == selecionado_label)

odd_a = st.number_input(f"Odd para {selecionado['jogador_a']}", value=selecionado['odd_a'] or 1.80, step=0.01, format="%.2f")
odd_b = st.number_input(f"Odd para {selecionado['jogador_b']}", value=selecionado['odd_b'] or 2.00, step=0.01, format="%.2f")

st.markdown('</div>', unsafe_allow_html=True)

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

# Cálculo dos Elo finais combinados
try:
    geral_a = float(dados_a['Elo'])
    esp_a = float(dados_a[{'Hard':'hElo','Clay':'cElo','Grass':'gElo'}[superficie]])
    yelo_a_f = float(yelo_a)
    elo_final_a = (esp_a / geral_a) * yelo_a_f
except:
    elo_final_a = None

try:
    geral_b = float(dados_b['Elo'])
    esp_b = float(dados_b[{'Hard':'hElo','Clay':'cElo','Grass':'gElo'}[superficie]])
    yelo_b_f = float(yelo_b)
    elo_final_b = (esp_b / geral_b) * yelo_b_f
except:
    elo_final_b = None

if elo_final_a is None or elo_final_b is None:
    st.warning("Elo final indisponível para um ou ambos os jogadores.")
    st.stop()

if yelo_a is None or yelo_b is None:
    st.error("Não consegui encontrar yElo para um dos jogadores.")
    st.stop()

# Odds e cálculo das probabilidades & valores
try:
    odd_a_f = float(odd_a)
    odd_b_f = float(odd_b)
except:
    st.error("Odds inválidas.")
    st.stop()

prob_a = elo_prob(elo_final_a, elo_final_b)
prob_b = 1 - prob_a

raw_p_a = 1 / odd_a_f
raw_p_b = 1 / odd_b_f
soma_raw = raw_p_a + raw_p_b
corr_p_a = raw_p_a / soma_raw
corr_p_b = raw_p_b / soma_raw
corr_odd_a = 1 / corr_p_a
corr_odd_b = 1 / corr_p_b

valor_a = value_bet(prob_a, corr_odd_a)
valor_b = value_bet(prob_b, corr_odd_b)

stake_a = stake_por_faixa(valor_a)
stake_b = stake_por_faixa(valor_b)

# === Exibição dos elos finais ===
st.markdown('<div class="card">', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.metric("🔵 Elo Final " + selecionado['jogador_a'], f"{elo_final_a:.2f}")
with col2:
    st.metric("🟠 Elo Final " + selecionado['jogador_b'], f"{elo_final_b:.2f}")
st.markdown('</div>', unsafe_allow_html=True)

# === Exibição das probabilidades, valor esperado e stakes ===
st.markdown('<div class="card">', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.metric("Prob. vitória (A)", f"{prob_a*100:.2f}%")
    st.metric("Valor esperado (A)", f"{valor_a*100:.2f}%")
    st.markdown(f"Stake recomendada: <span class='value-highlight'>€{stake_a:.2f}</span>", unsafe_allow_html=True)
    if 3.00 >= odd_a_f >= 1.45 and 0.03 <= valor_a <= 0.25:
        st.success("Valor positivo ✅")
    else:
        st.error("Sem valor", icon="❌")
with col2:
    st.metric("Prob. vitória (B)", f"{prob_b*100:.2f}%")
    st.metric("Valor esperado (B)", f"{valor_b*100:.2f}%")
    st.markdown(f"Stake recomendada: <span class='value-highlight'>€{stake_b:.2f}</span>", unsafe_allow_html=True)
    if 3.00 >= odd_b_f >= 1.45 and 0.03 <= valor_b <= 0.25:
        st.success("Valor positivo ✅")
    else:
        st.error("Sem valor", icon="❌")
st.markdown('</div>', unsafe_allow_html=True)

# ===== EXPANDERS: explicação e análise automática =======
with st.expander("📊 ENTENDA O CÁLCULO – Detalhes Elo/yElo"):
    st.write(f"##### {selecionado['jogador_a']}")
    st.json(dados_a.to_dict())
    st.write(f"YElo (estimativa): {float(yelo_a):.2f}" if yelo_a else "YElo: não disponível")
    st.write(f"##### {selecionado['jogador_b']}")
    st.json(dados_b.to_dict())
    st.write(f"YElo (estimativa): {float(yelo_b):.2f}" if yelo_b else "YElo: não disponível")

    st.markdown(r"""
    ### Como funciona o cálculo?

    O sistema Elo estima a força relativa dos jogadores em confrontos diretos. A probabilidade do Jogador A vencer o Jogador B é calculada por:

    $$
    P(A) = \frac{1}{1 + 10^{\frac{Elo_B - Elo_A}{400}}}
    $$

    O Elo final ajustado segundo a superfície e o yElo é:

    $$
    Elo_{final} = \left(\frac{Elo_{superfície}}{Elo_{geral}}\right) \times yElo
    $$

    O valor esperado da aposta é calculado removendo a margem da casa (juice) das odds:

    $$
    Valor = Probabilidade \times Odd_{corrigida} - 1
    $$

    A stake recomendada é definida em faixas fixas segundo o valor esperado:
    - 3% a 11% → 5€
    - 11% a 18% → 7.5€
    - 18% a 25% → 10€
    """, unsafe_allow_html=True)

with st.expander("🚦 Análise automática: jogos com valor positivo"):
    if st.button("Analisar todos os jogos!", use_container_width=True):
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
                eSA = float(dA[{"Hard":"hElo","Clay":"cElo","Grass":"gElo"}[superficie]])
                yFA = float(yA)
                eGB = float(dB["Elo"])
                eSB = float(dB[{"Hard":"hElo","Clay":"cElo","Grass":"gElo"}[superficie]])
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
                "Prob A %": f"{pA*100:.2f}%",
                "Prob B %": f"{pB*100:.2f}%",
                "Valor A %": f"{valA*100:.2f}%",
                "Valor B %": f"{valB*100:.2f}%",
                "Stake A (€)": f"{stakeA:.2f}",
                "Stake B (€)": f"{stakeB:.2f}",
                "Valor A (raw)": valA,
                "Valor B (raw)": valB,
            })

        if not resultados:
            st.info("Nenhum jogo com valor possível analisado.")
        else:
            df = pd.DataFrame(resultados)
            df["Odd A"] = df["Odd A"].astype(float)
            df["Odd B"] = df["Odd B"].astype(float)

            df_valor_positivo = df[
                ((df["Valor A (raw)"] >= 0.03) & (df["Valor A (raw)"] <= 0.25) & (df["Odd A"] >= 1.45) & (df["Odd A"] <= 3.00)) |
                ((df["Valor B (raw)"] >= 0.03) & (df["Valor B (raw)"] <= 0.25) & (df["Odd B"] >= 1.45) & (df["Odd B"] <= 3.00))
            ]

            def highlight_valor(row):
                styles = [""] * len(row)
                try:
                    idx_val_a = row.index.get_loc("Valor A %")
                    idx_val_b = row.index.get_loc("Valor B %")
                    if 0.03 <= row["Valor A (raw)"] <= 0.25 and 1.45 <= row["Odd A"] <= 3.00:
                        styles[idx_val_a] = "background-color: #8ef58e;"
                    if 0.03 <= row["Valor B (raw)"] <= 0.25 and 1.45 <= row["Odd B"] <= 3.00:
                        styles[idx_val_b] = "background-color: #8ef58e;"
                except KeyError:
                    pass
                return styles

            styled = df_valor_positivo.style.apply(highlight_valor, axis=1)
            st.markdown("#### <span style='color:green; font-weight:700;'>Linha verde = aposta valiosa | Clique para ordenar!</span>", unsafe_allow_html=True)
            st.dataframe(styled, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center;opacity:.67;'>Fontes: tennisexplorer.com e tennisabstract.com | Design by teambetting+AI</div>",
    unsafe_allow_html=True
)
