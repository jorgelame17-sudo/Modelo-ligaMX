import os
import requests
import streamlit as st

# Lee la clave de los Secrets de Streamlit
API_KEY = st.secrets.get("API_FOOTBALL_KEY", st.secrets.get("API_KEY", os.getenv("API_FOOTBALL_KEY", "")))

BASE_URL = "https://v3.football.api-sports.io"
LIGA_ID = 262
TEMPORADA = 2026


def _get(endpoint):
    """GET a API-Sports (nativa). Devuelve el campo 'response' o None si hay error."""
    if not API_KEY:
        return None
    try:
        res = requests.get(
            f"{BASE_URL}/{endpoint}",
            headers={"x-apisports-key": API_KEY},
            timeout=6,
        )
        data = res.json()
    except Exception:
        return None

    # API-Sports responde 200 aunque haya errores (key inválida, plan, límite...)
    if data.get("errors"):
        st.sidebar.warning(f"⚠️ API-Sports: {data['errors']}")
        return None

    return data.get("response") or None


@st.cache_data(ttl=3600)
def obtener_partidos_proximos():
    """Consulta los próximos encuentros reales de la Liga MX en API-Sports."""
    if not API_KEY:
        st.sidebar.warning("⚠️ No se detectó API Key. Usando datos base.")
        return obtener_partidos_mock()

    fixtures = _get(f"fixtures?league={LIGA_ID}&season={TEMPORADA}&next=10")
    if not fixtures:
        return obtener_partidos_mock()

    try:
        return [
            {
                "id": f["fixture"]["id"],
                "partido": f"{f['teams']['home']['name']} vs {f['teams']['away']['name']}",
                "local": f["teams"]["home"]["name"],
                "visita": f["teams"]["away"]["name"],
                "id_local": f["teams"]["home"]["id"],
                "id_visita": f["teams"]["away"]["id"],
            }
            for f in fixtures
        ]
    except (KeyError, TypeError):
        return obtener_partidos_mock()


@st.cache_data(ttl=3600)
def obtener_stats_equipo(nombre_equipo, id_equipo=None):
    """Obtiene las estadísticas del torneo para un equipo.

    Con id_equipo y API_KEY usa promedios reales de API-Sports (goles a favor,
    goles en contra y puntos por partido). Los campos que ese endpoint no
    ofrece (posesión, tiros, tiros a puerta) se toman de la base local.
    """
    stats = obtener_stats_mock(nombre_equipo)

    if not id_equipo or not API_KEY:
        return stats

    r = _get(f"teams/statistics?league={LIGA_ID}&season={TEMPORADA}&team={id_equipo}")
    if not r:
        return stats

    try:
        gf = float(r["goals"]["for"]["average"]["total"])
        gc = float(r["goals"]["against"]["average"]["total"])
        stats["goles_favor"] = gf
        stats["goles_contra"] = gc
        stats["goles_partido"] = round(gf + gc, 2)

        jugados = r["fixtures"]["played"]["total"] or 0
        if jugados > 0:
            pts = 3 * r["fixtures"]["wins"]["total"] + r["fixtures"]["draws"]["total"]
            stats["puntos_partido"] = round(pts / jugados, 2)
    except (KeyError, TypeError, ValueError):
        pass

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
    # .copy() para no modificar la base al sobrescribir con datos reales
    return stats_base.get(nombre_equipo, {'puntos_partido': 1.40, 'goles_favor': 1.30, 'goles_contra': 1.20, 'posesion': 50.0, 'tiros': 12.0, 'tiros_puerta': 4.0}).copy()
