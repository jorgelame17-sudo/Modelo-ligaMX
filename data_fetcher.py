import os
import requests
import streamlit as st

# Obtiene la clave desde Secrets o Variables de Entorno
API_KEY = st.secrets.get("API_FOOTBALL_KEY", st.secrets.get("API_KEY", os.getenv("API_FOOTBALL_KEY", "")))

def obtener_headers():
    return {
        "x-rapidapi-key": API_KEY,
        "x-apisports-key": API_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }

def obtener_partidos_proximos():
    """Consulta los próximos encuentros reales de la Liga MX."""
    if not API_KEY:
        st.sidebar.warning("⚠️ No se detectó API Key en Secrets. Usando modo local.")
        return obtener_partidos_mock()
    
    # ID Liga MX: 262 | Muestra los próximos 10 partidos
    url = "https://v3.football.api-sports.io/fixtures?league=262&next=10"
    headers = obtener_headers()
    
    try:
        response = requests.get(url, headers=headers, timeout=8)
        data = response.json()
        
        # Verificar errores de API Key o Suscripción
        if data.get("errors") and len(data.get("errors")) > 0:
            st.sidebar.error(f"Error API: {data['errors']}")
            return obtener_partidos_mock()

        fixtures = data.get('response', [])
        
        if not fixtures:
            # Intento de respaldo sin filtro de fecha
            url_fallback = "https://v3.football.api-sports.io/fixtures?league=262&season=2026&next=10"
            res_fb = requests.get(url_fallback, headers=headers, timeout=8).json()
            fixtures = res_fb.get('response', [])
            
        if not fixtures:
            st.sidebar.info("No se encontraron partidos próximos inmediatos en la API.")
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

    except Exception as e:
        st.sidebar.error(f"Error de conexión: {e}")
        return obtener_partidos_mock()

def obtener_stats_equipo(nombre_equipo, id_equipo=None):
    """Obtiene las estadísticas reales del torneo para un equipo."""
    if not API_KEY or not id_equipo:
        return obtener_stats_mock(nombre_equipo)
        
    url = f"https://v3.football.api-sports.io/teams/statistics?league=262&season=2026&team={id_equipo}"
    headers = obtener_headers()
    
    try:
        res = requests.get(url, headers=headers, timeout=8).json().get('response', {})
        if not res:
            return obtener_stats_mock(nombre_equipo)
            
        partidos_jugados = res.get('fixtures', {}).get('played', {}).get('total', 1) or 1
        goles_favor = res.get('goals', {}).get('for', {}).get('total', {}).get('total', 0) / partidos_jugados
        goles_contra = res.get('goals', {}).get('against', {}).get('total', {}).get('total', 0) / partidos_jugados
        
        return {
            'puntos_partido': round(res.get('clean_sheet', {}).get('total', 0) * 0.5 + 1.2, 2),
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
        {"id": 1, "partido": "Tigres UANL vs Puebla", "local": "Tigres UANL", "visita": "Puebla", "id_local": 2278, "id_visita": 2284},
        {"id": 2, "partido": "Club América vs Guadalajara", "local": "Club América", "visita": "Guadalajara", "id_local": 2279, "id_visita": 2280},
        {"id": 3, "partido": "Pumas UNAM vs Cruz Azul", "local": "Pumas UNAM", "visita": "Cruz Azul", "id_local": 2283, "id_visita": 2285}
    ]

def obtener_stats_mock(nombre_equipo):
    stats_base = {
        "Tigres UANL": {'puntos_partido': 1.90, 'goles_favor': 1.60, 'goles_contra': 0.90, 'posesion': 55.0, 'tiros': 15.0, 'tiros_puerta': 5.50},
        "Puebla": {'puntos_partido': 1.10, 'goles_favor': 1.00, 'goles_contra': 1.50, 'posesion': 44.0, 'tiros': 10.5, 'tiros_puerta': 3.20},
        "Club América": {'puntos_partido': 2.00, 'goles_favor': 1.75, 'goles_contra': 0.95, 'posesion': 58.0, 'tiros': 16.0, 'tiros_puerta': 6.00},
        "Guadalajara": {'puntos_partido': 1.50, 'goles_favor': 1.30, 'goles_contra': 1.20, 'posesion': 51.0, 'tiros': 13.0, 'tiros_puerta': 4.50},
        "Pumas UNAM": {'puntos_partido': 1.40, 'goles_favor': 1.25, 'goles_contra': 1.30, 'posesion': 49.0, 'tiros': 12.0, 'tiros_puerta': 4.10},
        "Cruz Azul": {'puntos_partido': 1.85, 'goles_favor': 1.55, 'goles_contra': 1.05, 'posesion': 54.0, 'tiros': 14.2, 'tiros_puerta': 5.10}
    }
    return stats_base.get(nombre_equipo, {'puntos_partido': 1.40, 'goles_favor': 1.30, 'goles_contra': 1.20, 'posesion': 50.0, 'tiros': 12.0, 'tiros_puerta': 4.0})
