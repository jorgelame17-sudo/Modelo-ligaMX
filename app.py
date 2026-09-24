import streamlit as st
import pandas as pd
from modelo import calcular_xgp, simular_partido_montecarlo
from value_odds import evaluar_valor
from history import guardar_partido, cargar_historial
from data_fetcher import obtener_partidos_proximos, obtener_stats_equipo

st.set_page_config(page_title="Sistema de Análisis - Liga MX", layout="wide")
st.title("⚽ Sistema de Análisis Predictivo & Value Betting (Autónomo)")

tab1, tab2 = st.tabs(["📊 Análisis del Partido", "📜 Historial de Pronósticos"])

with tab1:
    st.sidebar.header("⚙️ Configuración del Partido")
    
    # Carga autónoma de partidos
    lista_partidos = obtener_partidos_proximos()
    opciones = [p['partido'] for p in lista_partidos]
    partido_sel = st.sidebar.selectbox("Selecciona un Partido de la Jornada", opciones)

    partido_data = next(p for p in lista_partidos if p['partido'] == partido_sel)
    eq_local = partido_data['local']
    eq_visita = partido_data['visita']

    # Extracción autónoma de métricas
    stats_loc = obtener_stats_equipo(eq_local, partido_data.get('id_local'))
    stats_vis = obtener_stats_equipo(eq_visita, partido_data.get('id_visita'))

    # Cálculo del modelo de forma automática
    xg_loc, xg_vis = calcular_xgp(stats_loc, stats_vis)
    sims = simular_partido_montecarlo(xg_loc, xg_vis)

    # Mostrar Resultados Principales
    st.subheader(f"🏟️ {eq_local} vs {eq_visita}")
    col1, col2, col3 = st.columns(3)
    col1.metric(f"xG Esperados ({eq_local})", xg_loc)
    col2.metric("Empate Probable", f"{sims['empate']}%")
    col3.metric(f"xG Esperados ({eq_visita})", xg_vis)

    st.markdown("---")
    st.subheader("🎯 Probabilidades del Modelo (1X2)")
    c1, c2, c3 = st.columns(3)
    c1.progress(sims['local']/100, text=f"Gana {eq_local}: {sims['local']}%")
    c2.progress(sims['empate']/100, text=f"Empate: {sims['empate']}%")
    c3.progress(sims['visitante']/100, text=f"Gana {eq_visita}: {sims['visitante']}%")

    st.markdown("---")
    st.subheader("💡 Escenarios de Mercado")
    m1, m2, m3 = st.columns(3)
    m1.metric("Más de 2.5 Goles", f"{sims['over25']}%")
    m2.metric("Menos de 2.5 Goles", f"{sims['under25']}%")
    m3.metric("Ambos Anotan (BTTS)", f"{sims['btts_si']}%")

    st.markdown("---")
    st.sidebar.subheader("💰 Cuotas de la Casa de Apuestas")
    c_local = st.sidebar.number_input(f"Cuota {eq_local}", value=2.20, step=0.05)
    c_empate = st.sidebar.number_input("Cuota Empate", value=3.20, step=0.05)
    c_visita = st.sidebar.number_input(f"Cuota {eq_visita}", value=3.10, step=0.05)

    st.subheader("⚖️ Análisis de Valor (Value Betting)")
    _, edge_loc, val_loc = evaluar_valor(sims['local'], c_local)
    _, edge_emp, val_emp = evaluar_valor(sims['empate'], c_empate)
    _, edge_vis, val_vis = evaluar_valor(sims['visitante'], c_visita)

    v_col1, v_col2, v_col3 = st.columns(3)
    if val_loc:
        v_col1.success(f"¡VALOR DETECTADO! {eq_local} | Edge: +{edge_loc}%")
    else:
        v_col1.info(f"Edge {eq_local}: {edge_loc}%")

    if val_emp:
        v_col2.success(f"¡VALOR DETECTADO! Empate | Edge: +{edge_emp}%")
    else:
        v_col2.info(f"Edge Empate: {edge_emp}%")

    if val_vis:
        v_col3.success(f"¡VALOR DETECTADO! {eq_visita} | Edge: +{edge_vis}%")
    else:
        v_col3.info(f"Edge {eq_visita}: {edge_vis}%")

    st.markdown("---")
    if st.button("💾 Guardar Análisis en Historial", use_container_width=True):
        guardar_partido({
            "Partido": partido_sel,
            "xG_Local": xg_loc,
            "xG_Visita": xg_vis,
            "Prob_Local": sims['local'],
            "Prob_Empate": sims['empate'],
            "Prob_Visita": sims['visitante'],
            "Cuota_Local": c_local,
            "Cuota_Empate": c_empate,
            "Cuota_Visita": c_visita
        })
        st.success("Partido registrado correctamente en el historial.")

with tab2:
    st.subheader("📜 Historial de Análisis Registrados")
    df_hist = cargar_historial()
    if not df_hist.empty:
        st.dataframe(df_hist, use_container_width=True)
    else:
        st.info("Aún no hay análisis guardados en el historial.")
