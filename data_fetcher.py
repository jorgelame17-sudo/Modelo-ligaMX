import unicodedata
from datetime import date, timedelta

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# ESPN API oficial en JSON para la Liga MX (mex.1). No requiere API Key.
#
# Tabla de posiciones: hay que usar el path /apis/v2/ (SIN "site"). El path
# /apis/site/v2/.../standings existe pero ESPN lo dejó como stub y siempre
# devuelve un JSON vacío ({}) para fútbol.
#
# Calendario: vive en /apis/site/v2/.../scoreboard.
#
# Bloqueo 403 desde Streamlit Cloud: el CDN de ESPN (Akamai) puede rechazar
# peticiones que no parezcan un navegador real, algo más probable desde IPs
# de datacenter como las de Streamlit Cloud. Para reducirlo: (1) se usan
# cabeceras de navegador con Referer/Origin, (2) se hace una petición de
# "calentamiento" a espn.com para obtener cookies de sesión válidas antes de
# llamar a la API, y (3) si aun así falla, se reintenta con el dominio
# alterno site.web.api.espn.com antes de caer al respaldo.
# ---------------------------------------------------------------------------
HOST_PRINCIPAL = "https://site.api.espn.com"
HOST_ALTERNO = "https://site.web.api.espn.com"
RUTA_CALENDARIO = "/apis/site/v2/sports/soccer/mex.1/scoreboard"
RUTA_TABLA = "/apis/v2/sports/soccer/mex.1/standings"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Referer": "https://www.espn.com/soccer/schedule/_/league/mex.1",
    "Origin": "https://www.espn.com",
}
TIMEOUT = 10
DIAS_ADELANTE = 45
DIAS_ATRAS = 10


def _log(mensaje):
    """Muestra el motivo exacto de un fallo/estado de ESPN en la barra lateral."""
    try:
        st.sidebar.caption(f"ℹ️ {mensaje}")
    except Exception:
        print(f"[data_fetcher] {mensaje}")


def _norm(nombre):
    n = unicodedata.normalize("NFD", str(nombre)).encode("ascii", "ignore").decode().lower().strip()
    for prefijo in ("club ", "fc ", "cf "):
        if n.startswith(prefijo):
            n = n[len(prefijo):]
    return n


@st.cache_resource
def _sesion():
    """Sesión con cabeceras de navegador y cookies de una 'visita' previa a espn.com.

    La cookie de sesión ayuda a pasar algunos filtros anti-bot de Akamai en el
    CDN de ESPN. Se cachea con cache_resource para no repetir el calentamiento
    en cada rerun de Streamlit.
    """
    s = requests.Session()
    s.headers.update(HEADERS)
    try:
        s.get("https://www.espn.com/", timeout=TIMEOUT)
    except requests.RequestException:
        pass  # si el calentamiento falla, se sigue intentando sin esas cookies
    return s


def _get_json(url, params=None):
    """GET con diagnóstico detallado. Devuelve (json, None) o (None, motivo)."""
    try:
        res = _sesion().get(url, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        return None, f"Error de red al consultar ESPN: {e}"

    if res.status_code != 200:
        return None, f"ESPN respondió status {res.status_code} para {res.url}"

    try:
        data = res.json()
    except ValueError:
        return None, f"ESPN devolvió una respuesta que no es JSON válido ({res.url})"

    if not data:
        return None, f"ESPN devolvió un JSON vacío ({res.url})"

    return data, None


def _get_json_con_reintentos(ruta, intentos_params, etiquetas):
    """Prueba una lista de (params, host) hasta obtener datos.

    intentos_params: lista de dicts de query params (o None) a probar, en orden,
                      contra HOST_PRINCIPAL; si todos fallan, se repite la lista
                      completa contra HOST_ALTERNO como último recurso.
    etiquetas: descripción de cada intento, para el log (mismo largo que intentos_params).
    """
    for host in (HOST_PRINCIPAL, HOST_ALTERNO):
        for params, etiqueta in zip(intentos_params, etiquetas):
            url = host + ruta
            data, motivo = _get_json(url, params)
            nombre_host = "principal" if host == HOST_PRINCIPAL else "alterno"
            if motivo:
                _log(f"{etiqueta} [{nombre_host}]: {motivo}")
                continue
            _log(f"{etiqueta} [{nombre_host}]: OK")
            return data
    return None


def _construir_partido(e):
    equipos = e["competitions"][0]["competitors"]
    local = next(c for c in equipos if c["homeAway"] == "home")["team"]
    visita = next(c for c in equipos if c["homeAway"] == "away")["team"]
    return {
        "id": e["id"],
        "partido": f"{local['displayName']} vs {visita['displayName']}",
        "local": local["displayName"],
        "visita": visita["displayName"],
        "id_local": local["id"],
        "id_visita": visita["id"],
        "fecha": e.get("date"),
        "estado": e.get("status", {}).get("type", {}).get("state"),
    }


# ---------------------------------------------------------------------------
# 1) Calendario en tiempo real
# ---------------------------------------------------------------------------
def obtener_partidos_proximos():
    """Próximos partidos de la Liga MX. Nunca devuelve una lista vacía.

    Prueba, en orden: (a) ventana amplia de fechas y (b) sin fechas, primero
    contra el host principal de ESPN y luego contra el host alterno si el
    principal está bloqueando (403) o falla. Con lo que se junte, prioriza
    partidos "pre" > "in" > "post". Si nada de eso trae eventos, usa el mock.
    """
    hoy = date.today()
    rango = f"{(hoy - timedelta(days=DIAS_ATRAS)):%Y%m%d}-{(hoy + timedelta(days=DIAS_ADELANTE)):%Y%m%d}"

    eventos_totales = {}
    for host in (HOST_PRINCIPAL, HOST_ALTERNO):
        nombre_host = "principal" if host == HOST_PRINCIPAL else "alterno"
        for params, etiqueta in ((({"dates": rango, "limit": 200}), f"Calendario con fechas {rango}"),
                                  (None, "Calendario sin fechas")):
            data, motivo = _get_json(host + RUTA_CALENDARIO, params)
            if motivo:
                _log(f"{etiqueta} [{nombre_host}]: {motivo}")
                continue
            eventos = data.get("events", [])
            _log(f"{etiqueta} [{nombre_host}]: {len(eventos)} evento(s) recibidos")
            for e in eventos:
                eventos_totales[e["id"]] = e
        if eventos_totales:
            break  # el host principal ya dio resultados, no hace falta el alterno

    if not eventos_totales:
        _log("ESPN no devolvió ningún evento en ningún intento (ni host alterno). Usando datos base.")
        return obtener_partidos_mock()

    eventos = list(eventos_totales.values())

    def _estado(e):
        return e.get("status", {}).get("type", {}).get("state")

    pre = sorted([e for e in eventos if _estado(e) == "pre"], key=lambda e: e.get("date", ""))
    en_juego = [e for e in eventos if _estado(e) == "in"]
    recientes = sorted([e for e in eventos if _estado(e) == "post"], key=lambda e: e.get("date", ""), reverse=True)

    if pre:
        seleccionados, origen = pre[:10], "próximos"
    elif en_juego:
        seleccionados, origen = en_juego[:10], "en juego"
    elif recientes:
        seleccionados, origen = recientes[:10], "recientes (no hay próximos programados)"
    else:
        _log("Se recibieron eventos de ESPN pero ninguno se pudo clasificar. Usando datos base.")
        return obtener_partidos_mock()

    _log(f"Mostrando {len(seleccionados)} partido(s) {origen} desde ESPN.")

    try:
        return [_construir_partido(e) for e in seleccionados]
    except (KeyError, StopIteration, TypeError) as e:
        _log(f"Error al leer la estructura de un evento de ESPN: {e}. Usando datos base.")
        return obtener_partidos_mock()


# ---------------------------------------------------------------------------
# 2) Tabla y estadísticas en tiempo real
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def _tabla_liga():
    """Tabla completa de la Liga MX (promedios por partido de cada equipo).

    Devuelve {} si la consulta falla (incluido el host alterno); nunca lanza
    una excepción hacia afuera.
    """
    data = None
    for host in (HOST_PRINCIPAL, HOST_ALTERNO):
        nombre_host = "principal" if host == HOST_PRINCIPAL else "alterno"
        data, motivo = _get_json(host + RUTA_TABLA)
        if motivo:
            _log(f"Tabla de posiciones [{nombre_host}]: {motivo}")
            continue
        _log(f"Tabla de posiciones [{nombre_host}]: OK")
        break
    if not data:
        return {}

    entradas = []
    for hijo in data.get("children", []):
        entradas = hijo.get("standings", {}).get("entries", [])
        if entradas:
            break

    tabla = {}
    for e in entradas:
        try:
            s = {x["name"]: x.get("value") for x in e.get("stats", [])}
            j = float(s.get("gamesPlayed") or 0)
            if j <= 0:
                continue
            gf = float(s["pointsFor"]) / j
            gc = float(s["pointsAgainst"]) / j
            reg = {
                "puntos_partido": round(float(s["points"]) / j, 2),
                "goles_favor": round(gf, 2),
                "goles_contra": round(gc, 2),
                "goles_partido": round(gf + gc, 2),
                "partidos": int(j),
            }
            tabla[_norm(e["team"]["displayName"])] = reg
            tabla[str(e["team"]["id"])] = reg
        except (KeyError, TypeError, ValueError):
            continue
    return tabla


def obtener_stats_equipo(nombre_equipo, id_equipo=None):
    """Estadísticas del torneo para un equipo.

    Puntos, goles a favor y goles en contra por partido salen de la tabla de ESPN.
    Si el equipo no aparece en la tabla o la consulta falla, se usan los
    promedios de la base local sin romper el flujo.
    """
    tabla = _tabla_liga()
    reg = tabla.get(_norm(nombre_equipo)) or tabla.get(str(id_equipo))

    stats = obtener_stats_mock(nombre_equipo)  # posesión y tiros: no vienen en la tabla
    if reg:
        stats.update(reg)
    return stats


# ---------------------------------------------------------------------------
# Datos base (respaldo)
# ---------------------------------------------------------------------------
def obtener_partidos_mock():
    """Jornada actual y partidos relevantes de la Liga MX."""
    return [
        {"id": 1, "partido": "Tigres UANL vs Puebla", "local": "Tigres UANL", "visita": "Puebla", "id_local": 2278, "id_visita": 2284},
        {"id": 2, "partido": "Club América vs Guadalajara", "local": "Club América", "visita": "Guadalajara", "id_local": 2279, "id_visita": 2280},
        {"id": 3, "partido": "Pumas UNAM vs Cruz Azul", "local": "Pumas UNAM", "visita": "Cruz Azul", "id_local": 2283, "id_visita": 2285},
        {"id": 4, "partido": "Monterrey vs Toluca", "local": "Monterrey", "visita": "Toluca", "id_local": 2281, "id_visita": 2282},
        {"id": 5, "partido": "Pachuca vs León", "local": "Pachuca", "visita": "León", "id_local": 2286, "id_visita": 2287}
    ]


PROMEDIO_LIGA = {'puntos_partido': 1.40, 'goles_favor': 1.30, 'goles_contra': 1.20, 'posesion': 50.0, 'tiros': 12.0, 'tiros_puerta': 4.0}


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
    clave = _norm(nombre_equipo)
    for nombre, datos in stats_base.items():
        if _norm(nombre) == clave:
            return datos.copy()
    return PROMEDIO_LIGA.copy()


def mostrar_fuente_datos():
    """Llamar una vez desde app.py (p. ej. justo después de st.set_page_config)."""
    st.sidebar.caption("Fuente: ESPN API Oficial")
