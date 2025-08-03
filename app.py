import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from difflib import get_close_matches
import unicodedata
import os
import importlib.util

# ===== Verifica se a dependência 'html5lib' está instalada =====
if importlib.util.find_spec("html5lib") is None:
    st.error("Dependência obrigatória 'html5lib' ausente. Instale com:\npip install html5lib")
    st.stop()

# ===== Configurações visuais e CSS =====
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

# Funções para persistência de histórico via CSV
def carregar_historico():
    if os.path.exists(HISTORICO_CSV):
        try:
            return pd.read_csv(HISTORICO_CSV)
        except:
            return pd.DataFrame()
    else:
        return pd.DataFrame()

def salvar_historico(df):
    df.to_csv(HISTORICO_CSV, index=False)

# Todas as outras funções utilitárias (limpar_numero_ranking, ajustar_nome, reorganizar_nome, normalizar_nome,
# obter_torneios, obter_nome_completo, obter_jogos_do_torneio, obter_elo_table, obter_yelo_table,
# cache_elo, cache_yelo, elo_prob, value_bet, stake_por_faixa, encontrar_yelo, match_nome, elo_por_superficie)
# permanecem idênticas às já fornecidas anteriormente (por limitação de espaço não repito aqui,
# mas no seu arquivo devem estar todas incluídas exatamente como antes).

# Vamos carregá-las diretamente (por economia de espaço aqui - você deve incluir o código completo das funções acima).

# Carrega histórico ao iniciar a aplicação
if "historico_apostas_df" not in st.session_state:
    st.session_state["historico_apostas_df"] = carregar_historico()

# Função para calcular retorno no histórico
def calcular_retorno(aposta):
    resultado = aposta.get("resultado", "")
    valor_apostado = aposta.get("valor_apostado", 0.0)
    odd = aposta.get("odd", 0.0)
    if resultado == "ganhou":
        return valor_apostado * odd
    elif resultado == "cashout":
        return valor_apostado * 0.5
    else:
        return 0.0

# ===== Sidebar (com torneio entre competição e superfície) =====
with st.sidebar:
    st.header("⚙️ Definições gerais")
    tipo_competicao = st.selectbox("Escolher competição", ["ATP", "WTA"])
    # Atualiza torneios dinamicamente conforme competição
    torneios = obter_torneios(tipo=tipo_competicao)
    if not torneios:
        st.error(f"Não foi possível obter torneios ativos para {tipo_competicao}.")
        st.stop()
    torneio_nomes = [t['nome'] for t in torneios]
    torneio_selec = st.selectbox("Selecionar Torneio", torneio_nomes)
    superficie_pt = st.selectbox("Superfície", list(superficies_map.keys()), index=0)
    btn_atualizar = st.button("🔄 Atualizar Dados", type="primary")

if btn_atualizar:
    st.cache_data.clear()
    st.experimental_rerun()

superficie_en = superficies_map[superficie_pt]

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

tab_manual, tab_auto, tab_hist = st.tabs([
    f"{tipo_competicao} - Análise Manual",
    f"{tipo_competicao} - Análise Automática",
    "Histórico"
])

# ABA Manual com explicações e registro de apostas com persistência
with tab_manual:
    # (Inclusão do código conforme versão anterior detalhada, com:
    # seleção do jogo,
    # cálculo de probabilidades, valores, stake,
    # botões para registrar aposta atualizando st.session_state["historico_apostas_df"] e
    # salvando CSV,
    # exibir detalhes em expanders,
    # garantindo que sempre o histórico se mantém salvo.)

    # Exemplo do registro integrado com persistência:
    # No lugar de append, concatena DataFrame, salva e atualiza st.session_state["historico_apostas_df"]

    # [Código do tab_manual exatamente como detalhado anteriormente,
    # substituindo o registro de apostas por:]

    import numpy as np

    st.header(f"Análise Manual de Jogos {tipo_competicao}")

    jogo_selecionado_label = st.selectbox("Selecionar jogo:", [j['label'] for j in jogos])
    selecionado = next(j for j in jogos if j['label'] == jogo_selecionado_label)

    odd_a_input = st.number_input(f"Odd para {selecionado['jogador_a']}", value=selecionado['odd_a'] or 1.80, step=0.01)
    odd_b_input = st.number_input(f"Odd para {selecionado['jogador_b']}", value=selecionado['odd_b'] or 2.00, step=0.01)

    jogador_apostar = st.radio("Selecione o jogador para apostar", (selecionado['jogador_a'], selecionado['jogador_b']))

    idx_a = match_nome(selecionado['jogador_a'], elo_df['Player'])
    idx_b = match_nome(selecionado['jogador_b'], elo_df['Player'])
    if idx_a is None or idx_b is None:
        st.error("Não foi possível encontrar Elo para um dos jogadores.")
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
    except Exception as e:
        st.warning(f"Erro ao calcular Elo final: {e}")
        st.stop()

    prob_a = elo_prob(elo_final_a, elo_final_b)
    prob_b = 1 - prob_a

    odd_a, odd_b = float(odd_a_input), float(odd_b_input)
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

    if st.button("Registrar esta aposta"):
        nova_aposta = {
            "data": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "evento": selecionado['label'],
            "aposta": jogador_apostar,
            "odd": odd_usar,
            "valor_apostado": stake_usar,
            "stake": stake_usar,
            "resultado": ""
        }
        novo_df = pd.DataFrame([nova_aposta])
        st.session_state["historico_apostas_df"] = pd.concat(
            [st.session_state["historico_apostas_df"], novo_df],
            ignore_index=True
        )
        salvar_historico(st.session_state["historico_apostas_df"])
        st.success(f"Aposta registrada em {jogador_apostar} com odd {odd_usar} e stake €{stake_usar:.2f}")

    with st.expander("📈 Detalhes dos ELOs e Cálculos"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"### {selecionado['jogador_a']}")
            st.write(f"- Elo Geral: {geral_a:.2f}")
            st.write(f"- Elo {superficie_pt}: {esp_a:.2f}")
            st.write(f"- yElo: {yelo_a_f:.2f}")
            st.write(f"- Elo Final calculado: {elo_final_a:.2f}")
        with col2:
            st.write(f"### {selecionado['jogador_b']}")
            st.write(f"- Elo Geral: {geral_b:.2f}")
            st.write(f"- Elo {superficie_pt}: {esp_b:.2f}")
            st.write(f"- yElo: {yelo_b_f:.2f}")
            st.write(f"- Elo Final calculado: {elo_final_b:.2f}")

    with st.expander("🔬 Explicação dos Cálculos e Detalhes Avançados"):
        st.markdown(
            """
            - O sistema **Elo** estima a força relativa dos jogadores.
            - A probabilidade do Jogador A vencer o Jogador B é:
              $$ P(A) = \\frac{1}{1 + 10^{\\frac{Elo_B - Elo_A}{400}}} $$
            - As odds são corrigidas para eliminar a margem das casas de apostas:
              $$ \\text{Odd corrigida} = \\frac{1}{\\text{Probabilidade normalizada}} $$
            - O valor esperado ("value bet") é calculado como:
              $$ Valor = Probabilidade \\times Odd_{corrigida} - 1 $$
            - A stake recomendada depende do valor esperado:
              | Intervalo de Valor Esperado | Stake (€) |
              |-----------------------------|-----------|
              | 4,5% a 11%                  | 5         |
              | 11% a 18%                   | 7.5       |
              | 18% a 27,5%                 | 10        |
            """
        )
    st.markdown('<div class="custom-sep"></div>', unsafe_allow_html=True)

# ===== Aba Automática =====
with tab_auto:
    # Mantém a mesma lógica, mas registra apostas usando persistência (DataFrame + salvar CSV) ao clicar em botões

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
            "Odd A": f"{oA:.2f}",
            "Odd B": f"{oB:.2f}",
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
        df["Valor A (raw)"] = df["Valor A (raw)"].round(6)
        df["Valor B (raw)"] = df["Valor B (raw)"].round(6)
        df["Odd A"] = df["Odd A"].astype(float)
        df["Odd B"] = df["Odd B"].astype(float)

        df_valor_positivo = df[
            ((df["Valor A (raw)"] >= VALOR_MIN) & (df["Valor A (raw)"] <= VALOR_MAX) &
             (df["Odd A"] >= ODD_MIN) & (df["Odd A"] <= ODD_MAX)) |
            ((df["Valor B (raw)"] >= VALOR_MIN) & (df["Valor B (raw)"] <= VALOR_MAX) &
             (df["Odd B"] >= ODD_MIN) & (df["Odd B"] <= ODD_MAX))
        ]

        def highlight_stakes(val):
            if val == "5.00":
                return "background-color:#8ef58e;"
            elif val == "7.50":
                return "background-color:#8ef58e;"
            elif val == "10.00":
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

        styled = df_valor_positivo.style.apply(highlight_valor, axis=1)\
                                      .applymap(highlight_stakes, subset=["Stake A (€)", "Stake B (€)"])

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
                            "resultado": ""
                        }
                        novo_df = pd.DataFrame([nova_aposta])
                        st.session_state["historico_apostas_df"] = pd.concat([
                            st.session_state["historico_apostas_df"], novo_df
                        ], ignore_index=True)
                        salvar_historico(st.session_state["historico_apostas_df"])
                        st.success(f"Aposta em {nova_aposta['aposta']} registrada automaticamente (Jogador A)")
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
                            "resultado": ""
                        }
                        novo_df = pd.DataFrame([nova_aposta])
                        st.session_state["historico_apostas_df"] = pd.concat([
                            st.session_state["historico_apostas_df"], novo_df
                        ], ignore_index=True)
                        salvar_historico(st.session_state["historico_apostas_df"])
                        st.success(f"Aposta em {nova_aposta['aposta']} registrada automaticamente (Jogador B)")

    st.caption("Legenda stake: 5€ [baixa], 7.5€ [média], 10€ [alta]")

# ===== Aba Histórico =====
with tab_hist:
    st.header("📊 Histórico de Apostas e Retorno")

    df_hist = st.session_state["historico_apostas_df"]
    if not df_hist.empty:
        df_hist_display = df_hist.copy()
        df_hist_display["retorno"] = df_hist_display.apply(calcular_retorno, axis=1)

        st.dataframe(df_hist_display.drop(columns=["retorno"]), use_container_width=True)

        st.metric("Retorno Total (€)", f"{df_hist_display['retorno'].sum():.2f}")
        st.metric("Número de Apostas", len(df_hist))
        st.metric("Apostas Ganhas", (df_hist["resultado"] == "ganhou").sum())
    else:
        st.info("Nenhuma aposta registrada até o momento.")

    st.markdown("---")
    st.subheader("Atualizar resultado de apostas")

    if not df_hist.empty:
        opcoes_evento = [
            f"{i}: {a['evento']} - {a['aposta']} (Resultado: {a['resultado'] or 'não definido'})"
            for i, a in df_hist.iterrows()
        ]
        selecionado_idx = st.selectbox("Escolher aposta para atualizar", options=range(len(opcoes_evento)), format_func=lambda i: opcoes_evento[i])

        nova_res = st.selectbox("Resultado", ["", "ganhou", "perdeu", "cashout"], index=0)

        if st.button("Atualizar resultado"):
            if nova_res:
                st.session_state["historico_apostas_df"].loc[selecionado_idx, "resultado"] = nova_res
                salvar_historico(st.session_state["historico_apostas_df"])
                st.success("Resultado atualizado!")
            else:
                st.error("Selecione um resultado válido para atualização.")
    else:
        st.write("Nenhuma aposta para atualizar.")

st.divider()
st.caption("Fontes: tennisexplorer.com e tennisabstract.com | App experimental — design demo")
