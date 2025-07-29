
# Aplicativo simples para avaliar se uma aposta tem valor com base nos Elo ratings do Tennis Abstract

import streamlit as st
import math

# Função para calcular probabilidade com base na diferença de Elo
def elo_prob(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

# Função para calcular o Elo final ponderado (com base na superfície)
def elo_final(surface_elo, general_elo, yelo):
    if general_elo == 0:
        return 0
    return (surface_elo / general_elo) * yelo

# Função para calcular valor esperado
def value_bet(prob, odd):
    return (prob * odd) - 1

st.title("Análise de Valor em Apostas de Ténis com Elo (Tennis Abstract)")

# Entrada de dados
st.subheader("Jogador A")
elo_a = st.number_input("Elo geral de A", value=1700.0)
surf_elo_a = st.number_input("Elo por superfície de A", value=1700.0)
yelo_a = st.number_input("yElo de A (forma atual)", value=1700.0)
odd_a = st.number_input("Odd para o Jogador A", value=1.80)

st.subheader("Jogador B")
elo_b = st.number_input("Elo geral de B", value=1600.0)
surf_elo_b = st.number_input("Elo por superfície de B", value=1600.0)
yelo_b = st.number_input("yElo de B (forma atual)", value=1600.0)

# Cálculo dos Elos finais
final_elo_a = elo_final(surf_elo_a, elo_a, yelo_a)
final_elo_b = elo_final(surf_elo_b, elo_b, yelo_b)

# Probabilidades
prob_a = elo_prob(final_elo_a, final_elo_b)
prob_b = 1 - prob_a

# Value
value = value_bet(prob_a, odd_a)

# Mostrar resultados
st.markdown("---")
st.metric("Probabilidade estimada de A vencer", f"{prob_a*100:.2f}%")
st.metric("Valor esperado da aposta em A", f"{value*100:.2f}%")

if value > 0:
    st.success("Aposta com valor! ✅")
elif value < 0:
    st.error("Sem valor na aposta ❌")
else:
    st.info("Aposta neutra.")
