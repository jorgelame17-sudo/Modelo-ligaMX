import numpy as np  
from scipy.stats import poisson  
  
def calcular_xgp(stats_local, stats_visitante, promedio_liga_goles=1.35):  
    # Fuerza ofensiva y defensiva basada en promedios  
    fuerza_of_local = stats_local['goles_favor'] / promedio_liga_goles  
    fuerza_def_local = stats_local['goles_contra'] / promedio_liga_goles  
    fuerza_of_vis = stats_visitante['goles_favor'] / promedio_liga_goles  
    fuerza_def_vis = stats_visitante['goles_contra'] / promedio_liga_goles  
  
    # Factor ventaja localía (~1.15x)  
    xg_local = fuerza_of_local * fuerza_def_vis * promedio_liga_goles * 1.15  
    xg_visitante = fuerza_of_vis * fuerza_def_local * promedio_liga_goles * 0.85  
  
    return round(xg_local, 2), round(xg_visitante, 2)  
  
def simular_partido_montecarlo(xg_local, xg_visitante, n_simulaciones=20000):  
    goles_local = np.random.poisson(xg_local, n_simulaciones)  
    goles_vis = np.random.poisson(xg_visitante, n_simulaciones)  
  
    prob_local = np.mean(goles_local > goles_vis) * 100  
    prob_empate = np.mean(goles_local == goles_vis) * 100  
    prob_vis = np.mean(goles_local < goles_vis) * 100  
  
    totales = goles_local + goles_vis  
    prob_over25 = np.mean(totales > 2.5) * 100  
    prob_under25 = 100 - prob_over25  
    prob_btts = np.mean((goles_local > 0) & (goles_vis > 0)) * 100  
  
    return {  
        'local': round(prob_local, 1),  
        'empate': round(prob_empate, 1),  
        'visitante': round(prob_vis, 1),  
        'over25': round(prob_over25, 1),  
        'under25': round(prob_under25, 1),  
        'btts_si': round(prob_btts, 1),  
        'btts_no': round(100 - prob_btts, 1)  
    }  
