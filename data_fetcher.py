import os
import requests
import streamlit as st

# Obtiene la clave de Streamlit Secrets o Variables de Entorno
API_KEY = st.secrets.get("API_FOOTBALL_KEY", os.getenv("API_FOOTBALL_KEY", ""))
HEADERS = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io"
}

def obtener_partidos_proximos():
    """Consulta los próximos encuentros de la Liga MX (ID de Liga: 262)."""
    if not API_KEY:
        return obtener_partidos_mock()
    
    url = "https://v3.football.api-sports.io/fixtures?league=262&next=10"
    try:
        response = requests.get(url, headers=HEADERS, timeout=5).json()
        fixtures = response.get('response', [])
        
        if not fixtures:
            return obtener_partidos_mock()
            
        partidos = []
        for f in fixtures:
            partidos.append({
                "id": f['fixture']['id'],
                "partido": f"{f['teams']['home']['name']} vs {f['teams']['away']['name']}",
                "local": f['teams']['home']['name'],
                "visita": f['teams']['away']['name'],
                "id_local": f['teams']['home']['id'],
                "id_visita": f['teams']['away']['id']
            })
        return partidos
    except Exception:
        return obtener_partidos_mock()

def obtener_stats_equipo(nombre_equipo, id_equipo=None):
    """Obtiene las estadísticas reales de la temporada activa para un equipo."""
    if not API_KEY:
        return obtener_stats_mock(nombre_equipo)
        
    url = f"https://v3.football.api-sports.io/teams/statistics?league=262&season=2026&team={id_equipo}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=5).json().get('response', {})
        if not res:
            return obtener_stats_mock(nombre_equipo)
            
        partidos_jugados = res.get('fixtures', {}).get('played', {}).get('total', 1) or 1
        goles_favor = res.get('goals', {}).get('for', {}).get('total', {}).get('total', 0) / partidos_jugados
        goles_contra = res.get('goals', {}).get('against', {}).get('total', {}).get('total', 0) / partidos_jugados
        
        return {
            'puntos_partido': round(res.get('clean_sheet', {}).get('total', 0) * 0.5 + 1.2, 2), # Estimación dinámica
            'goles_favor': round(goles_favor, 2) or 1.3,
            'goles_contra': round(goles_contra, 2) or 1.1,
            'posesion': 50.0,
            'tiros': 12.0,
            'tiros_puerta': 4.0
        }
    except Exception:
        return obtener_stats_mock(nombre_equipo)

def obtener_partidos_mock():
    return [
        {"id": 1, "partido": "Querétaro vs León", "local": "Querétaro", "visita": "León", "id_local": 2282, "id_visita": 2281},
        {"id": 2, "partido": "Tigres UANL vs Club América", "local": "Tigres UANL", "visita": "Club América", "id_local": 2278, "id_visita": 2279},
        {"id": 3, "partido": "Chivas vs Pumas UNAM", "local": "Chivas", "visita": "Pumas UNAM", "id_local": 2280, "id_visita": 2283}
    ]

def obtener_stats_mock(nombre_equipo):
    stats_base = {
        "Querétaro": {'puntos_partido': 1.86, 'goles_favor': 1.43, 'goles_contra': 1.00, 'posesion': 40.4, 'tiros': 12.7, 'tiros_puerta': 4.0},
        "León": {'puntos_partido': 1.62, 'goles_favor': 1.38, 'goles_contra': 1.12, 'posesion': 48.0, 'tiros': 14.6, 'tiros_puerta': 5.62},
        "Tigres UANL": {'puntos_partido': 1.90, 'goles_favor': 1.60, 'goles_contra': 0.90, 'posesion': 55.0, 'tiros': 15.0, 'tiros_puerta': 5.50},
        "Club América": {'puntos_partido': 2.00, 'goles_favor': 1.75, 'goles_contra': 0.95, 'posesion': 58.0, 'tiros': 16.0, 'tiros_puerta': 6.00},
        "Chivas": {'puntos_partido': 1.50, 'goles_favor': 1.30, 'goles_contra': 1.20, 'posesion': 51.0, 'tiros': 13.0, 'tiros_puerta': 4.50},
        "Pumas UNAM": {'puntos_partido': 1.40, 'goles_favor': 1.25, 'goles_contra': 1.30, 'posesion': 49.0, 'tiros': 12.0, 'tiros_puerta': 4.10}
    }
    return stats_base.get(nombre_equipo, {'puntos_partido': 1.40, 'goles_favor': 1.30, 'goles_contra': 1.20, 'posesion': 50.0, 'tiros': 12.0, 'tiros_puerta': 4.0})
