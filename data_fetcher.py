import time
import unicodedata
from datetime import date, timedelta
from io import StringIO

import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Fuentes
#   1) FBref (principal): tabla de posiciones y, si existen, tiros/xG de la temporada actual.
#   2) ESPN (respaldo y calendario): endpoints públicos sin API Key.
#   3) Base local (obtener_stats_mock / obtener_partidos_mock): último recurso.
# ---------------------------------------------------------------------------
FBREF_TABLA = "https://fbref.com/en/comps/31/Liga-MX-Stats"
FBREF_TIROS = "https://fbref.com/en/comps/31/shooting/Liga-MX-Stats"
ESPN_TABLA = "https://site.api.espn.com/apis/v2/sports/soccer/mex.1/standings"
ESPN_CALENDARIO = "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard"

HEADERS_WEB = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}
HEADERS_JSON = {"User-Agent": "Mozilla/5.0 (compatible; liga-mx-app/1.0)"}
TIMEOUT = 12

_ALIAS = {
    "chivas": "guadalajara",
    "tigres": "tigres uanl",
    "pumas": "pumas unam",
    "atletico": "atletico san luis",
    "san luis": "atletico san luis",
    "atletico de san luis": "atletico san luis",
    "santos": "santos laguna",
}


def _norm(nombre):
    n = unicodedata.normalize("NFD", str(nombre)).encode("ascii", "ignore").decode().lower().strip()
    for prefijo in ("club ", "fc ", "cf "):
        if n.startswith(prefijo):
            n = n[len(prefijo):]
    if n.endswith(" fc"):
        n = n[:-3]
    return n


def _clave(nombre):
    """Clave común para comparar nombres de equipos entre fuentes."""
    n = _norm(nombre)
    return _ALIAS.get(n, n)


# ---------------------------------------------------------------------------
# FBref (web scraping con pandas.read_html)
# ---------------------------------------------------------------------------
def _descargar_html(url):
    res = requests.get(url, headers=HEADERS_WEB, timeout=TIMEOUT)
    res.raise_for_status()  # 403/429 => excepción (y así no se guarda en caché)
    return res.text


def _leer_tablas(html):
    # FBref esconde varias tablas dentro de comentarios HTML: se "destapan" antes de leerlas.
    html = html.replace("<!--", "").replace("-->", "")
    tablas = pd.read_html(StringIO(html))
    for t in tablas:
        if isinstance(t.columns, pd.MultiIndex):
            t.columns = [str(c[-1]) for c in t.columns]
    return tablas


def _buscar_tabla(tablas, requeridas):
    for t in tablas:
        if set(requeridas).issubset(set(t.columns)):
            return t.copy()
    return None


def _num(serie):
    return pd.to_numeric(serie, errors="coerce")


@st.cache_data(ttl=86400, show_spinner="Actualizando estadísticas de la Liga MX...")
def _tabla_fbref():
    """Promedios por partido de cada equipo desde FBref. Lanza excepción si falla."""
    tabla = _buscar_tabla(_leer_tablas(_descargar_html(FBREF_TABLA)),
                          ["Squad", "MP", "GF", "GA", "Pts"])
    if tabla is None:
        raise ValueError("No se encontró la tabla de posiciones en FBref")

    for c in ("MP", "GF", "GA", "Pts", "xG", "xGA"):
        if c in tabla.columns:
            tabla[c] = _num(tabla[c])
    tabla = tabla.dropna(subset=["MP"])
    tabla = tabla[tabla["MP"] > 0]

    # Tiros: FBref quitó los datos avanzados (Opta) en enero de 2026. Si la tabla de
    # tiros vuelve a existir se usa automáticamente; si no, se ignora.
    tiros = {}
    try:
        time.sleep(3)  # cortesía: FBref limita la frecuencia de peticiones
        t_sh = _buscar_tabla(_leer_tablas(_descargar_html(FBREF_TIROS)), ["Squad", "Sh", "SoT"])
        if t_sh is not None:
            for _, r in t_sh.iterrows():
                sh = _num(pd.Series([r.get("Sh/90")])).iloc[0] if "Sh/90" in t_sh.columns else float("nan")
                sot = _num(pd.Series([r.get("SoT/90")])).iloc[0] if "SoT/90" in t_sh.columns else float("nan")
                if pd.notna(sh):
                    tiros[_clave(r["Squad"])] = (float(sh), None if pd.isna(sot) else float(sot))
    except Exception:
        tiros = {}

    resultado = {}
    for _, r in tabla.iterrows():
        mp = float(r["MP"])
        gf, gc = float(r["GF"]) / mp, float(r["GA"]) / mp
        reg = {
            "puntos_partido": round(float(r["Pts"]) / mp, 2),
            "goles_favor": round(gf, 2),
            "goles_contra": round(gc, 2),
            "goles_partido": round(gf + gc, 2),
            "partidos": int(mp),
        }
        if "xG" in tabla.columns and pd.notna(r["xG"]):
            reg["xg_favor"] = round(float(r["xG"]) / mp, 2)
        if "xGA" in tabla.columns and pd.notna(r["xGA"]):
            reg["xg_contra"] = round(float(r["xGA"]) / mp, 2)
        clave = _clave(r["Squad"])
        if clave in tiros:
            reg["tiros"] = round(tiros[clave][0], 2)
            if tiros[clave][1] is not None:
                reg["tiros_puerta"] = round(tiros[clave][1], 2)
        resultado[clave] = reg
    if not resultado:
        raise ValueError("La tabla de FBref llegó vacía")
    return resultado


# ---------------------------------------------------------------------------
# ESPN (respaldo de la tabla + calendario)
# ---------------------------------------------------------------------------
def _get_json(url, params=None):
    res = requests.get(url, headers=HEADERS_JSON, params=params, timeout=TIMEOUT)
    res.raise_for_status()
    return res.json()


@st.cache_data(ttl=3600)
def _tabla_espn():
    """Respaldo: promedios por partido desde ESPN. Lanza excepción si falla."""
    data = _get_json(ESPN_TABLA)
    entradas = []
    for hijo in data.get("children", []):
        entradas = hijo.get("standings", {}).get("entries", [])
        if entradas:
            break
    if not entradas:
        entradas = data.get("standings", {}).get("entries", [])

    tabla = {}
    for e in entradas:
        try:
            s = {x["name"]: x.get("value") for x in e.get("stats", [])}
            pj = float(s.get("gamesPlayed") or 0)
            if pj <= 0:
                continue
            gf = float(s["pointsFor"]) / pj
            gc = float(s["pointsAgainst"]) / pj
            reg = {
                "puntos_partido": round(float(s["points"]) / pj, 2),
                "goles_favor": round(gf, 2),
                "goles_contra": round(gc, 2),
                "goles_partido": round(gf + gc, 2),
                "partidos": int(pj),
            }
            tabla[_clave(e["team"]["displayName"])] = reg
            tabla[str(e["team"]["id"])] = reg
        except (KeyError, TypeError, ValueError):
            continue
    if not tabla:
        raise ValueError("Tabla de ESPN vacía")
    return tabla


@st.cache_data(ttl=3600)
def _calendario_espn():
    """Próximos partidos desde ESPN. Lanza excepción si falla o no hay partidos."""
    hoy = date.today()
    rango = f"{hoy:%Y%m%d}-{hoy + timedelta(days=21):%Y%m%d}"
    data = _get_json(ESPN_CALENDARIO, params={"dates": rango, "limit": 100})

    eventos = [e for e in data.get("events", []) if e["status"]["type"]["state"] == "pre"]
    eventos.sort(key=lambda e: e.get("date", ""))
    partidos = []
    for e in eventos[:10]:
        equipos = e["competitions"][0]["competitors"]
        local = next(c for c in equipos if c["homeAway"] == "home")["team"]
        visita = next(c for c in equipos if c["homeAway"] == "away")["team"]
        partidos.append({
            "id": e["id"],
            "partido": f"{local['displayName']} vs {visita['displayName']}",
            "local": local["displayName"],
            "visita": visita["displayName"],
            "id_local": local["id"],
            "id_visita": visita["id"],
        })
    if not partidos:
        raise ValueError("Sin partidos próximos")
    return partidos


# ---------------------------------------------------------------------------
# Funciones públicas (misma interfaz que antes)
# ---------------------------------------------------------------------------
def obtener_partidos_proximos():
    """Próximos encuentros de la Liga MX. Cae en el mock si la fuente falla."""
    try:
        return _calendario_espn()
    except Exception:
        st.sidebar.warning("⚠️ No se pudo consultar el calendario en vivo. Usando datos base.")
        return obtener_partidos_mock()


def obtener_stats_equipo(nombre_equipo, id_equipo=None):
    """Estadísticas del torneo para un equipo: FBref -> ESPN -> base local.

    Los campos que ninguna fuente entregue (posesión, tiros, etc.) se toman de la base local.
    """
    stats = obtener_stats_mock(nombre_equipo)
    clave = _clave(nombre_equipo)

    try:
        reg = _tabla_fbref().get(clave)
        fuente = "FBref"
    except Exception:
        reg, fuente = None, None

    if not reg:
        try:
            tabla = _tabla_espn()
            reg = tabla.get(clave) or tabla.get(str(id_equipo))
            fuente = "ESPN"
        except Exception:
            reg = None

    if reg:
        stats.update(reg)
        stats["fuente"] = fuente
    return stats


def obtener_partidos_mock():
    """Jornada actual y partidos relevantes de la Liga MX."""
    return [
        {"id": 1, "partido": "Tigres UANL vs Puebla", "local": "Tigres UANL", "visita": "Puebla", "id_local": 2278, "id_visita": 2284},
        {"id": 2, "partido": "Club América vs Guadalajara", "local": "Club América", "visita": "Guadalajara", "id_local": 2279, "id_visita": 2280},
        {"id": 3, "partido": "Pumas UNAM vs Cruz Azul", "local": "Pumas UNAM", "visita": "Cruz Azul", "id_local": 2283, "id_visita": 2285},
        {"id": 4, "partido": "Monterrey vs Toluca", "local": "Monterrey", "visita": "Toluca", "id_local": 2281, "id_visita": 2282},
        {"id": 5, "partido": "Pachuca vs León", "local": "Pachuca", "visita": "León", "id_local": 2286, "id_visita": 2287}
    ]


def obtener_stats_mock(nombre_equipo):
    stats_base = {
        "Tigres UANL": {'puntos_partido': 1.90, 'goles_favor': 1.60, 'goles_contra': 0.90, 'posesion': 55.0, 'tiros': 15.0, 'tiros_puerta': 5.50},
        "Puebla": {'puntos_partido': 1.10, 'goles_favor': 1.00, 'goles_contra': 1.50, 'posesion': 44.0, 'tiros': 10.5, 'tiros_puerta': 3.20},
        "Club América": {'puntos_partido': 2.00, 'goles_favor': 1.75, 'goles_contra': 0.95, 'posesion': 58.0, 'tiros': 16.0, 'tiros_puerta': 6.00},
        "Guadalajara": {'puntos_partido': 1.50, 'goles_favor': 1.30, 'goles_contra': 1.20, 'posesion': 51.0, 'tiros': 13.0, 'tiros_puerta': 4.50},
        "Pumas UNAM": {'puntos_partido': 1.40, 'goles_favor': 1.25, 'goles_contra': 1.30, 'posesion': 49.0, 'tiros': 12.0, 'tiros_puerta': 4.10},
        "Cruz Azul": {'puntos_partido': 1.85, 'goles_favor': 1.55, 'goles_contra': 1.05, 'posesion': 54.0, 'tiros': 14.2, 'tiros_puerta': 5.10},
        "Monterrey": {'puntos_partido': 1.80, 'goles_favor': 1.65, 'goles_contra': 1.00, 'posesion': 56.0, 'tiros': 14.5, 'tiros_puerta': 5.20},
        "Toluca": {'puntos_partido': 1.70, 'goles_favor': 1.80, 'goles_contra': 1.35, 'posesion': 53.0, 'tiros': 13.8, 'tiros_puerta': 4.80}
    }
    clave = _clave(nombre_equipo)
    for nombre, datos in stats_base.items():
        if _clave(nombre) == clave:
            return datos.copy()
    return {'puntos_partido': 1.40, 'goles_favor': 1.30, 'goles_contra': 1.20, 'posesion': 50.0, 'tiros': 12.0, 'tiros_puerta': 4.0}
