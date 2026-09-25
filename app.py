import streamlit as st
import pandas as pd
import numpy as np

# Configuración inicial de la página
st.set_page_config(
    page_title="ColdBrain - Modelo de Análisis Liga MX",
    page_icon="⚽",
    layout="wide"
)

# Importar módulos personalizados
try:
    import data_fetcher
    import modelo
except ImportError as e:
    st.error(f"Error importando módulos: {e}. Asegúrate de que 'data_fetcher.py' y 'modelo.py' estén subidos al repositorio.")
    st.stop()

# Mostrar la fuente de datos en la barra lateral
if hasattr(data_fetcher, 'mostrar_fuente_datos'):
    data_fetcher.mostrar_fuente_datos()

# ---------------------------------------------------------
# BARRA LATERAL (Sidebar): Selección de Partidos
# ---------------------------------------------------------
st.sidebar.title("⚙️ Configuración del Partido")

# Obtener próximos partidos usando data_fetcher
partidos = data_fetcher.obtener_partidos_proximos()

opciones_partidos = []
partidos_validos = []

if partidos:
    for p in partidos:
        # Extraer nombres según la estructura exacta de data_fetcher.py ("local" y "visita")
        loc = p.get('local') or p.get('equipo_local') or 'Local'
        vis = p.get('visita') or p.get('visitante') or p.get('equipo_visitante') or 'Visitante'
        id_loc = p.get('id_local')
        id_vis = p.get('id_visita')
        
        opciones_partidos.append(f"{loc} vs {vis}")
        partidos_validos.append({'local': loc, 'visita': vis, 'id_local': id_loc, 'id_visita': id_vis})

if opciones_partidos:
    partido_seleccionado_str = st.sidebar.selectbox("Selecciona un Partido de la Jornada", opciones_partidos)
    idx = opciones_partidos.index(partido_seleccionado_str)
    
    equipo_local = partidos_validos[idx]['local']
    equipo_visitante = partidos_validos[idx]['visita']
    id_local = partidos_validos[idx]['id_local']
    id_visitante = partidos_validos[idx]['id_visita']
else:
    # Contingencia por si la lista viniera vacía
    equipo_local = st.sidebar.text_input("Equipo Local", value="Tigres UANL")
    equipo_visitante = st.sidebar.text_input("Equipo Visitante", value="Puebla")
    id_local = None
    id_visitante = None

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Cuotas de la Casa de Apuestas")
cuota_local = st.sidebar.number_input(f"Cuota {equipo_local}", value=2.20, step=0.05)
cuota_empate = st.sidebar.number_input("Cuota Empate", value=3.20, step=0.05)
cuota_visitante = st.sidebar.number_input(f"Cuota {equipo_visitante}", value=3.10, step=0.05)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Recargar Datos"):
    st.cache_data.clear()
    st.rerun()

# ---------------------------------------------------------
# OBTENCIÓN DE DATOS Y CÁLCULOS DEL MODELO
# ---------------------------------------------------------
stats_local = data_fetcher.obtener_stats_equipo(equipo_local, id_local)
stats_visita = data_fetcher.obtener_stats_equipo(equipo_visitante, id_visitante)

# Ejecución del modelo de simulación
if hasattr(modelo, 'simular_partido'):
    res_sim = modelo.simular_partido(stats_local, stats_visita, num_simulaciones=20000)
    prob_local = res_sim.get('prob_local', 33.3)
    prob_empate = res_sim.get('prob_empate', 33.3)
    prob_visita = res_sim.get('prob_visita', 33.3)
    xgp_local = res_sim.get('xgp_local', 1.0)
    xgp_visita = res_sim.get('xgp_visita', 1.0)
    matriz_marcadores = res_sim.get('matriz_marcadores', None)
    
    escenarios = modelo.calcular_escenarios_goles(matriz_marcadores) if hasattr(modelo, 'calcular_escenarios_goles') else {'lineas_goles': {}, 'btts_si': 50, 'btts_no': 50, 'top_marcadores': {}}
    handicaps = modelo.calcular_handicaps(matriz_marcadores) if hasattr(modelo, 'calcular_handicaps') else {}
else:
    st.error("No se encontró la función 'simular_partido' en modelo.py.")
    st.stop()

# ---------------------------------------------------------
# INTERFAZ PRINCIPAL (DASHBOARD)
# ---------------------------------------------------------
st.title("⚽ Modelo Predictivo y Estadístico - Liga MX")
st.caption(f"Análisis detallado y simulación probabilística: **{equipo_local} vs {equipo_visitante}**")

# VALOR EN CUOTAS (VALUE BETTING)
prob_imp_local = (1 / cuota_local) * 100 if cuota_local > 0 else 0
prob_imp_empate = (1 / cuota_empate) * 100 if cuota_empate > 0 else 0
prob_imp_visita = (1 / cuota_visitante) * 100 if cuota_visitante > 0 else 0

edge_local = prob_local - prob_imp_local
edge_empate = prob_empate - prob_imp_empate
edge_visita = prob_visita - prob_imp_visita

if edge_local >= 5.0:
    st.success(f"🎯 **¡Oportunidad de Valor Detectada!** Apuesta recomendada: **{equipo_local}** (Ventaja del modelo: +{edge_local:.1f}%)")
elif edge_visita >= 5.0:
    st.success(f"🎯 **¡Oportunidad de Valor Detectada!** Apuesta recomendada: **{equipo_visitante}** (Ventaja del modelo: +{edge_visita:.1f}%)")
elif edge_empate >= 5.0:
    st.success(f"🎯 **¡Oportunidad de Valor Detectada!** Apuesta recomendada: **Empate** (Ventaja del modelo: +{edge_empate:.1f}%)")

tabs = st.tabs(["📊 1. Métricas Base", "🎲 2. Probabilidades 1X2", "🥅 3. Goles y Marcadores", "🛡️ 4. Hándicaps"])

# TAB 1: MÉTRICAS BASE
with tabs[0]:
    st.subheader(f"Las métricas, una a una: {equipo_local} vs {equipo_visitante}")
    
    # Mapeo exacto con los nombres de llaves de data_fetcher.py
    pts_l = stats_local.get('puntos_partido', 0.0)
    gf_l = stats_local.get('goles_favor', 0.0)
    gc_l = stats_local.get('goles_contra', 0.0)
    pos_l = stats_local.get('posesion', 50.0)
    tir_l = stats_local.get('tiros', 12.0)
    tp_l = stats_local.get('tiros_puerta', 4.0)
    pct_tp_l = (tp_l / tir_l * 100) if tir_l > 0 else 0.0

    pts_v = stats_visita.get('puntos_partido', 0.0)
    gf_v = stats_visita.get('goles_favor', 0.0)
    gc_v = stats_visita.get('goles_contra', 0.0)
    pos_v = stats_visita.get('posesion', 50.0)
    tir_v = stats_visita.get('tiros', 12.0)
    tp_v = stats_visita.get('tiros_puerta', 4.0)
    pct_tp_v = (tp_v / tir_v * 100) if tir_v > 0 else 0.0

    df_metrics = pd.DataFrame({
        "Métrica": [
            "Puntos / partido", 
            "Goles a favor / partido", 
            "Goles en contra / partido", 
            "Diferencia de gol / partido",
            "Posesión %",
            "Tiros / partido",
            "Tiros a puerta / partido",
            "% tiros a puerta"
        ],
        equipo_local: [
            f"{pts_l:.2f}",
            f"{gf_l:.2f}",
            f"{gc_l:.2f}",
            f"{(gf_l - gc_l):.2f}",
            f"{pos_l:.1f}%",
            f"{tir_l:.1f}",
            f"{tp_l:.1f}",
            f"{pct_tp_l:.1f}%"
        ],
        equipo_visitante: [
            f"{pts_v:.2f}",
            f"{gf_v:.2f}",
            f"{gc_v:.2f}",
            f"{(gf_v - gc_v):.2f}",
            f"{pos_v:.1f}%",
            f"{tir_v:.1f}",
            f"{tp_v:.1f}",
            f"{pct_tp_v:.1f}%"
        ]
    })
    st.table(df_metrics.set_index("Métrica"))

# TAB 2: PROBABILIDADES 1X2 Y XG
with tabs[1]:
    st.subheader("Proyección Probabilística (20,000 Simulaciones Monte Carlo)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(f"XGP {equipo_local} (Local)", f"{xgp_local:.2f}")
    with col2:
        st.metric(f"XGP {equipo_visitante} (Visitante)", f"{xgp_visita:.2f}")
        
    st.write("### Probabilidades del Resultado Final (1X2)")
    
    st.write(f"**Gana {equipo_local}: {prob_local:.1f}%** (Casa: {prob_imp_local:.1f}%)")
    st.progress(min(max(int(prob_local), 0), 100))
    
    st.write(f"**Empate: {prob_empate:.1f}%** (Casa: {prob_imp_empate:.1f}%)")
    st.progress(min(max(int(prob_empate), 0), 100))
    
    st.write(f"**Gana {equipo_visitante}: {prob_visita:.1f}%** (Casa: {prob_imp_visita:.1f}%)")
    st.progress(min(max(int(prob_visita), 0), 100))

# TAB 3: ESCENARIOS DE GOLES Y MARCADORES
with tabs[2]:
    st.subheader("Escenarios de Goles y Marcadores más Probables")
    col_goles, col_marcas = st.columns(2)
    
    with col_goles:
        st.markdown("#### Líneas de Goles (Over / Under)")
        for linea, pct in escenarios.get('lineas_goles', {}).items():
            st.write(f"**{linea}:** {pct:.1f}%")
            
        st.markdown("#### Ambos Anotan (BTTS)")
        st.write(f"**Sí:** {escenarios.get('btts_si', 0):.1f}%")
        st.write(f"**No:** {escenarios.get('btts_no', 0):.1f}%")
        
    with col_marcas:
        st.markdown("#### Top Marcadores Exactos")
        for marcador, pct in escenarios.get('top_marcadores', {}).items():
            st.write(f"⚽ **{marcador}** — {pct:.1f}%")

# TAB 4: HÁNDICAPS Y COBERTURAS
with tabs[3]:
    st.subheader(f"Diferencia de Goles / Hándicap — Ventaja para {equipo_local}")
    if handicaps:
        df_hc = pd.DataFrame({
            "Línea de Hándicap": ["-1.0", "-0.5", "0.0 (DNB)", "+0.5", "+1.0"],
            equipo_local: [
                f"{handicaps.get('local_minus_1', 0):.1f}%", 
                f"{handicaps.get('local_minus_05', 0):.1f}%", 
                f"{handicaps.get('dnb_local', 0):.1f}%", 
                f"{handicaps.get('local_plus_05', 0):.1f}%", 
                f"{handicaps.get('local_plus_1', 0):.1f}%"
            ],
            equipo_visitante: [
                f"{handicaps.get('visita_plus_1', 0):.1f}%", 
                f"{handicaps.get('visita_plus_05', 0):.1f}%", 
                f"{handicaps.get('dnb_visita', 0):.1f}%", 
                f"{handicaps.get('visita_minus_05', 0):.1f}%", 
                f"{handicaps.get('visita_minus_1', 0):.1f}%"
            ]
        })
        st.table(df_hc.set_index("Línea de Hándicap"))
    else:
        st.info("No hay datos de hándicap disponibles.")
