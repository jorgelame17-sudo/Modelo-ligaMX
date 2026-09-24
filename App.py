import streamlit as st
import pandas as pd
from modelo import calcular_xgp, simular_partido_montecarlo
from value_odds import evaluar_valor
from history import guardar_partido, cargar_historial
from data_fetcher import obtener_partidos_proximos, obtener_stats_equipo

st.set_page_config(page_title="Sistema de Análisis - Liga MX", layout="wide")
st.title("⚽ Sistema de Análisis Predictivo & Value Betting")

tab1, tab2 = st.tabs(["📊 Análisis del Partido", "📜 Historial de Pronósticos"])

with tab1:
    st.sidebar.header("0️⃣ Selección de Partido")
    lista_partidos = obtener_partidos_proximos()
    opciones = [p['partido'] for p in lista_partidos]
    partido_sel = st.sidebar.selectbox("Próximos Encuentros", opciones)

    partido_data = next(p for p in lista_partidos if p['partido'] == partido_sel)
    eq_local = partido_data['local']
    eq_visita = partido_data['visita']

    stats_loc = obtener_stats_equipo(eq_local)
    stats_vis = obtener_stats_equipo(eq_visita)

    xg_loc, xg_vis = calcular_xgp(stats_loc, stats_vis)
    sims = simular_partido_montecarlo(xg_loc, xg_vis)

    col1, col2, col3 = st.columns(3)
    col1.metric(f"Goles Esperados ({eq_local})", xg_loc)
    col2.metric("Empate Probable", f"{sims['empate']}%")
    col3.metric(f"Goles Esperados ({eq_visita})", xg_vis)

    st.subheader("🎯 Probabilidades 1X2")
    c1, c2, c3 = st.columns(3)
    c1.progress(sims['local']/100, text=f"Gana {eq_local}: {sims['local']}%")
    c2.progress(sims['empate']/100, text=f"Empate: {sims['empate']}%")
    c3.progress(sims['visitante']/100, text=f"Gana {eq_visita}: {sims['visitante']}%")

    st.subheader("💰 Evaluación de Valor (Value Betting)")
    col_cuota1, col_cuota2, col_cuota3 = st.columns(3)
    c_local = col_cuota1.number_input(f"Cuota {eq_local}", value=2.20)
    c_empate = col_cuota2.number_input("Cuota Empate", value=3.20)
    c_visita = col_cuota3.number_input(f"Cuota {eq_visita}", value=3.10)

    _, edge_loc, val_loc = evaluar_valor(sims['local'], c_local)
    if val_loc:
        st.success(f"¡Oportunidad de Valor en {eq_local}! Edge: +{edge_loc}%")

    if st.button("💾 Guardar Análisis en Historial"):
        guardar_partido({
            "Partido": partido_sel,
            "xG_Local": xg_loc,
            "xG_Visita": xg_vis,
            "Prob_Local": sims['local'],
            "Prob_Empate": sims['empate'],
            "Prob_Visita": sims['visita']
        })
        st.info("Partido registrado correctamente.")

with tab2:
    st.subheader("Historial Registrado")
    df_hist = cargar_historial()
    if not df_hist.empty:
        st.dataframe(df_hist, use_container_width=True)
    else:
        st.write("Aún no hay registros guardados.")
