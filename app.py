import streamlit as st
import pandas as pd
import numpy as np

# Configuración inicial de la página (DEBE SER LO PRIMERO EN EJECUTARSE)
st.set_page_config(
    page_title="ColdBrain - Modelo de Análisis Liga MX",
    page_icon="⚽",
    layout="wide"
)

# Importar funciones personalizadas del proyecto
try:
    from data_fetcher import obtener_partidos_proximos, obtener_stats_equipo, mostrar_fuente_datos
    from modelo import simular_partido, calcular_escenarios_goles, calcular_handicaps
except ImportError:
    st.error("Asegúrate de que los archivos 'data_fetcher.py' y 'modelo.py' estén en la misma carpeta del proyecto.")

# Mostrar la fuente de datos en la barra lateral
mostrar_fuente_datos()

# ---------------------------------------------------------
# BARRA LATERAL (Sidebar): Selección e Entradas
# ---------------------------------------------------------
st.sidebar.title("⚙️ Configuración del Partido")

# Obtener lista de partidos desde ESPN (o fallback local)
partidos = obtener_partidos_proximos()

if partidos:
    opciones_partidos = [f"{p['local']} vs {p['visitante']}" for p in partidos]
    partido_seleccionado_str = st.sidebar.selectbox("Selecciona un Partido de la Jornada", opciones_partidos)
    
    # Obtener el objeto del partido seleccionado
    index_partido = opciones_partidos.index(partido_seleccionado_str)
    partido_actual = partidos[index_partido]
    equipo_local = partido_actual['local']
    equipo_visitante = partido_actual['visitante']
else:
    # Valores por defecto si la lista viene vacía
    equipo_local = "Querétaro"
    equipo_visitante = "León"

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Cuotas de la Casa de Apuestas")
cuota_local = st.sidebar.number_input(f"Cuota {equipo_local}", value=2.20, step=0.05)
cuota_empate = st.sidebar.number_input("Cuota Empate", value=3.20, step=0.05)
cuota_visitante = st.sidebar.number_input(f"Cuota {equipo_visitante}", value=3.10, step=0.05)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Recargar Datos de ESPN"):
    st.cache_data.clear()
    st.rerun()

# ---------------------------------------------------------
# OBTENCIÓN DE DATOS Y CÁLCULOS DEL MODELO
# ---------------------------------------------------------
stats_local = obtener_stats_equipo(equipo_local)
stats_visita = obtener_stats_equipo(equipo_visitante)

# Ejecución de la simulación Monte Carlo / Poisson
res_sim = simular_partido(stats_local, stats_visita, num_simulaciones=20000)
prob_local = res_sim['prob_local']
prob_empate = res_sim['prob_empate']
prob_visita = res_sim['prob_visita']
xgp_local = res_sim['xgp_local']
xgp_visita = res_sim['xgp_visita']
matriz_marcadores = res_sim['matriz_marcadores']

# Cálculos de escenarios y hándicaps
escenarios = calcular_escenarios_goles(matriz_marcadores)
handicaps = calcular_handicaps(matriz_marcadores)

# ---------------------------------------------------------
# INTERFAZ PRINCIPAL (DASHBOARD)
# ---------------------------------------------------------
st.title("⚽ Modelo Predictivo y Estadístico - Liga MX")
st.caption(f"Análisis detallado y simulación probabilística: **{equipo_local} vs {equipo_visitante}**")

# ALERTA DE VALOR (VALUE BETTING)
prob_imp_local = (1 / cuota_local) * 100
prob_imp_empate = (1 / cuota_empate) * 100
prob_imp_visita = (1 / cuota_visitante) * 100

edge_local = prob_local - prob_imp_local
edge_empate = prob_empate - prob_imp_empate
edge_visita = prob_visita - prob_imp_visita

# Mostrar notificación si hay valor (+5% de margen)
if edge_local >= 5.0:
    st.success(f"🎯 **¡Oportunidad de Valor Detectada!** Apuesta recomendada: **{equipo_local}** (Ventaja del modelo: +{edge_local:.1f}%)")
elif edge_visita >= 5.0:
    st.success(f"🎯 **¡Oportunidad de Valor Detectada!** Apuesta recomendada: **{equipo_visitante}** (Ventaja del modelo: +{edge_visita:.1f}%)")
elif edge_empate >= 5.0:
    st.success(f"🎯 **¡Oportunidad de Valor Detectada!** Apuesta recomendada: **Empate** (Ventaja del modelo: +{edge_empate:.1f}%)")

tabs = st.tabs(["📊 1. Métricas Base", "🎲 2. Probabilidades 1X2", "🥅 3. Goles y Marcadores", "🛡️ 4. Hándicaps"])

# ---------------------------------------------------------
# TAB 1: MÉTRICAS BASE
# ---------------------------------------------------------
with tabs[0]:
    st.subheader(f"Las métricas, una a una: {equipo_local} vs {equipo_visitante}")
    
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
            f"{stats_local.get('pts_partido', 0):.2f}",
            f"{stats_local.get('gf_partido', 0):.2f}",
            f"{stats_local.get('gc_partido', 0):.2f}",
            f"{stats_local.get('dg_partido', 0):.2f}",
            f"{stats_local.get('posesion', 50.0):.2f}%",
            f"{stats_local.get('tiros_partido', 12.0):.2f}",
            f"{stats_local.get('tiros_puerta_partido', 4.0):.2f}",
            f"{stats_local.get('pct_tiros_puerta', 33.0):.2f}%"
        ],
        equipo_visitante: [
            f"{stats_visita.get('pts_partido', 0):.2f}",
            f"{stats_visita.get('gf_partido', 0):.2f}",
            f"{stats_visita.get('gc_partido', 0):.2f}",
            f"{stats_visita.get('dg_partido', 0):.2f}",
            f"{stats_visita.get('posesion', 50.0):.2f}%",
            f"{stats_visita.get('tiros_partido', 12.0):.2f}",
            f"{stats_visita.get('tiros_puerta_partido', 4.0):.2f}",
            f"{stats_visita.get('pct_tiros_puerta', 33.0):.2f}%"
        ]
    })
    st.table(df_metrics.set_index("Métrica"))

# ---------------------------------------------------------
# TAB 2: PROBABILIDADES 1X2 Y XG
# ---------------------------------------------------------
with tabs[1]:
    st.subheader("Proyección Probabilística (20,000 Simulaciones Monte Carlo)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(f"XGP {equipo_local} (Local)", f"{xgp_local:.2f}")
    with col2:
        st.metric(f"XGP {equipo_visitante} (Visitante)", f"{xgp_visita:.2f}")
        
    st.write("### Probabilidades del Resultado Final (1X2)")
    
    st.write(f"**Gana {equipo_local}: {prob_local:.1f}%** (Casa: {prob_imp_local:.1f}%)")
    st.progress(int(prob_local))
    
    st.write(f"**Empate: {prob_empate:.1f}%** (Casa: {prob_imp_empate:.1f}%)")
    st.progress(int(prob_empate))
    
    st.write(f"**Gana {equipo_visitante}: {prob_visita:.1f}%** (Casa: {prob_imp_visita:.1f}%)")
    st.progress(int(prob_visita))

# ---------------------------------------------------------
# TAB 3: ESCENARIOS DE GOLES Y MARCADORES
# ---------------------------------------------------------
with tabs[2]:
    st.subheader("Escenarios de Goles y Marcadores más Probables")
    
    col_goles, col_marcas = st.columns(2)
    
    with col_goles:
        st.markdown("#### Líneas de Goles (Over / Under)")
        for linea, pct in escenarios['lineas_goles'].items():
            st.write(f"**{linea}:** {pct:.1f}%")
            
        st.markdown("#### Ambos Anotan (BTTS)")
        st.write(f"**Sí:** {escenarios['btts_si']:.1f}%")
        st.write(f"**No:** {escenarios['btts_no']:.1f}%")
        
    with col_marcas:
        st.markdown("#### Top Marcadores Exactos")
        for marcador, pct in escenarios['top_marcadores'].items():
            st.write(f"⚽ **{marcador}** — {pct:.1f}%")

# ---------------------------------------------------------
# TAB 4: HÁNDICAPS Y COBERTURAS
# ---------------------------------------------------------
with tabs[3]:
    st.subheader(f"Diferencia de Goles / Hándicap — Ventaja para {equipo_local}")
    
    df_hc = pd.DataFrame({
        "Línea de Hándicap": ["-1.0", "-0.5", "0.0 (DNB)", "+0.5", "+1.0"],
        equipo_local: [f"{handicaps['local_minus_1']:.1f}%", f"{handicaps['local_minus_05']:.1f}%", f"{handicaps['dnb_local']:.1f}%", f"{handicaps['local_plus_05']:.1f}%", f"{handicaps['local_plus_1']:.1f}%"],
        equipo_visitante: [f"{handicaps['visita_plus_1']:.1f}%", f"{handicaps['visita_plus_05']:.1f}%", f"{handicaps['dnb_visita']:.1f}%", f"{handicaps['visita_minus_05']:.1f}%", f"{handicaps['visita_minus_1']:.1f}%"]
    })
    st.table(df_hc.set_index("Línea de Hándicap"))
