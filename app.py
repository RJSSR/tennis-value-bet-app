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
    try:
        r = requests.get(url_torneio)
        st.write(f"URL do torneio: {url_torneio}")
        st.write(f"Status HTTP: {r.status_code}")
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        tables = soup.select("table")
        st.write(f"Número de tabelas encontradas: {len(tables)}")
        if not tables:
            return jogos
        jogador_map = {}
        for a in soup.select("a[href^='/player/']"):
            n = a.text.strip()
            u = BASE_URL + a["href"] if a["href"].startswith("/") else a["href"]
            jogador_map[n] = u
        st.write(f"Jogadores encontrados: {list(jogador_map.keys())[:10]}... (total {len(jogador_map)})")
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
        st.write(f"Número de jogos encontrados: {len(jogos)}")
        return jogos
    except Exception as e:
        st.error(f"Erro ao obter jogos: {e}")
        return jogos

# (restante do código — inclua todas as suas funções auxiliares, cache_elo, cache_yelo, elo_prob, valor_bet, etc., igual anteriormente gerado)

# Abaixo, mantenha seu código principal para carregar histórico, configurar página, sidebar, abas, manual, automático e histórico

# Para não alongar excessivamente a resposta, se desejar, posso enviar todo o código completo atualizado com essa função de obter jogos com debug inserido.  
# Caso queira o código completo com esta alteração, por favor me avise!

