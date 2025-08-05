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
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

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
    # ... (mantém igual, lista dos torneios ATP)
    "Acapulco", "Adelaide", "Adelaide 2", "Almaty", "Antwerp", "Astana", "Atlanta", "ATP Cup",
    # ... restante da lista ...
    "Winston Salem", "Zhuhai"
]

TORNEIOS_WTA_PERMITIDOS = [
    # ... (mantém igual, lista dos torneios WTA)
    "Abu Dhabi WTA", "Adelaide", "Adelaide 2", "Andorra WTA", "Angers WTA", "Antalya 2 WTA", "Antalya 3 WTA",
    # ... restante da lista ...
    "Wuhan", "Zhengzhou 2 WTA"
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
        seletor = "a[href*='/atp-men/']" if tipo == "ATP" else "a[href*='/wta-women/']"
        for a in soup.select(seletor):
            nome = a.text.strip()
            href = a.get("href", "")
            if not href:
                continue
            url_full = BASE_URL + href if href.startswith("/") else href
            if nome.casefold() in nomes_permitidos and url_full not in {t["url"] for t in torneios}:
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

# ... (ABA MANUAL e ABA AUTOMÁTICA - igual ao anterior) ...

# --- Aba Histórico ---
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
            theme="fresh"
        )

        # Remoção de apostas selecionadas, robusto!
        selected = response.get("selected_rows", [])
        if len(selected) > 0 and st.button("❌ Remover aposta(s) selecionada(s)", type="primary"):
            df = st.session_state["historico_apostas_df"].reset_index(drop=True)
            for data in selected:
                # uso .get e casts + str.strip() para máxima robustez!
                row_data = str(data.get("data", "")).strip()
                cond = (
                    df["data"].astype(str).str.strip() == row_data
                )
                cond &= (df["evento"] == data.get("evento", ""))
                cond &= (df["aposta"] == data.get("aposta", ""))
                # odd, sempre float!
                try:
                    data_odd = float(data.get("odd", 0))
                    cond &= (abs(df["odd"].astype(float) - data_odd) < 1e-9)
                except Exception:
                    cond &= False

                indices = df[cond].index
                if not indices.empty:
                    df = df.drop(indices)
            st.session_state["historico_apostas_df"] = df.reset_index(drop=True)
            salvar_historico(st.session_state["historico_apostas_df"])
            st.success("Aposta(s) removida(s) com sucesso.")
            st.experimental_rerun()

        # Atualização pós-edição no grid
        if response["data"] is not None:
            df_updated = pd.DataFrame(response["data"])
            if not df_updated.equals(st.session_state["historico_apostas_df"].astype(str)):
                st.session_state["historico_apostas_df"] = df_updated
                salvar_historico(st.session_state["historico_apostas_df"])

        # Estatísticas e gráfico - mantém igual
        df_hist_resultado = st.session_state["historico_apostas_df"]
        df_hist_resultado = df_hist_resultado[
            df_hist_resultado["resultado"].notna() & (df_hist_resultado["resultado"].str.strip() != "")
        ]
        df_hist_resultado["stake"] = pd.to_numeric(df_hist_resultado["stake"], errors="coerce").fillna(0)
        df_hist_resultado["odd"] = pd.to_numeric(df_hist_resultado["odd"], errors="coerce").fillna(0)

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

        # Gráfico mensal do lucro...
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
            df_lucro["ano_mes"] = pd.to_datetime(df_lucro["data"]).dt.strftime('%Y-%m')
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
