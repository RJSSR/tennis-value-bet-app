import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from difflib import get_close_matches
import unicodedata
import os
from io import StringIO

# Import para tabela interativa
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

# --------- Definição funções auxiliares ---------

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

# Definir aqui também outras funções auxiliares que você já tem (obter_nome_completo,
# obter_jogos_do_torneio, etc). Para brevidade, mantenho omitidas, pois você já tem implementadas.

# As funções carregar_historico e salvar_historico são essenciais e já colocadas abaixo:

def carregar_historico():
    if os.path.exists(HISTORICO_CSV):
        try:
            return pd.read_csv(HISTORICO_CSV)
        except Exception as e:
            print(f"Erro ao carregar histórico: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def salvar_historico(df):
    try:
        df.to_csv(HISTORICO_CSV, index=False)
    except Exception as e:
        print(f"Erro ao salvar histórico: {e}")

# Outras funções iguais às suas, p.ex., cache_elo, cache_yelo, elo_prob, stake_por_faixa, etc.

# ----------------------------------------------------

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

# Sidebar
with st.sidebar:
    st.header("⚙️ Definições gerais")
    tipo_competicao = st.selectbox("Escolher competição", ["ATP", "WTA"])
    torneios = obter_torneios(tipo=tipo_competicao)
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

# Funções para carregar elo_df e yelo_df aqui (cache_elo, cache_yelo) devem estar definidas conforme seu código original

# Placeholder para elos e jogos (insira seu código para pegar elo_df, yelo_df, jogos)
# elo_df = cache_elo(tipo=tipo_competicao)
# yelo_df = cache_yelo(tipo=tipo_competicao)
# jogos = obter_jogos_do_torneio(url_torneio_selec)

tab_manual, tab_auto, tab_hist = st.tabs([f"{tipo_competicao} - Análise Manual", f"{tipo_competicao} - Análise Automática", "Histórico"])

# --- Aba Manual ---
with tab_manual:
    # Insira aqui código da aba manual, conforme seu app
    pass

# --- Aba Automática ---
with tab_auto:
    # Insira aqui código da aba automática, conforme seu app
    pass

# --- Aba Histórico (usando streamlit-aggrid) ---
with tab_hist:
    st.header("📊 Histórico de Apostas e Retorno")

    df_hist = st.session_state["historico_apostas_df"].copy()

    if df_hist.empty:
        st.info("Nenhuma aposta registrada.")
    else:
        resultados_validos = ["", "ganhou", "perdeu", "cashout"]

        gb = GridOptionsBuilder.from_dataframe(df_hist)

        gb.configure_column(
            "resultado",
            editable=True,
            cellEditor='agSelectCellEditor',
            cellEditorParams={"values": resultados_validos},
            cellEditorPopup=True,
            header_name="Resultado",
        )

        button_renderer = JsCode("""
        class BtnRemoveRenderer {
            init(params) {
                this.params = params;
                this.eButton = document.createElement('button');
                this.eButton.innerHTML = '❌';
                this.eButton.style.backgroundColor = '#ff4b4b';
                this.eButton.style.color = 'white';
                this.eButton.style.border = 'none';
                this.eButton.style.borderRadius = '4px';
                this.eButton.style.cursor = 'pointer';
                this.eButton.onclick = () => {
                    if (confirm('Deseja remover esta aposta?')) {
                        params.api.applyTransaction({remove: [params.node.data]});
                        if (params.context && params.context.remove_callback) {
                            params.context.remove_callback(params.node.data);
                        }
                    }
                };
            }
            getGui() {
                return this.eButton;
            }
        }
        """)

        if "remove" not in df_hist.columns:
            df_hist["remove"] = ""

        gb.configure_column(
            "remove",
            header_name="Remover",
            cellRenderer=button_renderer,
            maxWidth=100,
            suppressMenu=True,
            editable=False,
            filter=False,
            sortable=False,
        )

        grid_options = gb.build()

        def remove_aposta_callback(data):
            df = st.session_state["historico_apostas_df"]
            condition = (
                (df["data"] == data["data"]) &
                (df["evento"] == data["evento"]) &
                (df["aposta"] == data["aposta"]) &
                (df["odd"] == data["odd"])
            )
            indices = df[condition].index
            if not indices.empty:
                st.session_state["historico_apostas_df"] = df.drop(indices).reset_index(drop=True)
                salvar_historico(st.session_state["historico_apostas_df"])
                st.rerun()

        context = {"remove_callback": remove_aposta_callback}

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
            context=context,
        )

        if response["data"] is not None:
            df_updated = pd.DataFrame(response["data"])

            if "remove" in df_updated.columns:
                df_updated = df_updated.drop(columns=["remove"])

            if not df_updated.equals(st.session_state["historico_apostas_df"].astype(str)):
                st.session_state["historico_apostas_df"] = df_updated
                salvar_historico(st.session_state["historico_apostas_df"])

        # Indicadores estatísticos do histórico
        df_hist_resultado = st.session_state["historico_apostas_df"]
        df_hist_resultado = df_hist_resultado[df_hist_resultado["resultado"].str.strip() != ""]

        num_apostas = len(df_hist_resultado)
        apostas_ganhas = (df_hist_resultado["resultado"] == "ganhou").sum()
        apostas_perdidas = (df_hist_resultado["resultado"] == "perdeu").sum()
        montante_investido = df_hist_resultado["stake"].sum()
        montante_ganho = df_hist_resultado.apply(lambda x: x["valor_apostado"] * x["odd"] if x["resultado"] == "ganhou" else (x["valor_apostado"] * 0.5 if x["resultado"] == "cashout" else 0.0), axis=1).sum()
        yield_percent = ((montante_ganho - montante_investido) / montante_investido * 100) if montante_investido > 0 else 0.0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Número de Apostas", num_apostas)
            st.metric("Apostas Ganhas", apostas_ganhas)
            st.metric("Apostas Perdidas", apostas_perdidas)
        with col2:
            st.metric("Montante Investido (€)", f"€{montante_investido:.2f}")
            st.metric("Montante Ganhou (€)", f"€{montante_ganho:.2f}")
        with col3:
            st.metric("Yield (%)", f"{yield_percent:.2f}%")

st.divider()
st.caption("Fontes: tennisexplorer.com e tennisabstract.com | App experimental — design demo")
