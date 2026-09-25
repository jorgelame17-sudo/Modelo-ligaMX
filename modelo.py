import numpy as np

def calcular_xgp(stats_local, stats_visita):
    """
    Calcula los Expected Goals Proyectados (XGP) ajustando la potencia ofensiva 
    y defensiva de cada equipo según las estadísticas de la temporada.
    """
    gf_loc = float(stats_local.get('goles_favor', 1.30))
    gc_loc = float(stats_local.get('goles_contra', 1.20))
    
    gf_vis = float(stats_visita.get('goles_favor', 1.30))
    gc_vis = float(stats_visita.get('goles_contra', 1.20))
    
    # Factor de ventaja de localía estándar (~1.15x)
    FACTOR_LOCALIA = 1.15
    
    # Proyección base de goles esperados
    xgp_local = ((gf_loc + gc_vis) / 2.0) * FACTOR_LOCALIA
    xgp_visita = ((gf_vis + gc_loc) / 2.0) / FACTOR_LOCALIA
    
    # Límites lógicos mínimos y máximos para evitar distorsiones extremas
    xgp_local = float(np.clip(xgp_local, 0.2, 4.5))
    xgp_visita = float(np.clip(xgp_visita, 0.2, 4.5))
    
    return xgp_local, xgp_visita


def simular_partido(stats_local, stats_visita, num_simulaciones=20000):
    """
    Simula el partido 'num_simulaciones' veces utilizando una distribución de Poisson 
    para los goles esperados de cada equipo.
    """
    xgp_loc, xgp_vis = calcular_xgp(stats_local, stats_visita)
    
    # Simulación de goles usando distribución de Poisson
    goles_local = np.random.poisson(xgp_loc, num_simulaciones)
    goles_visita = np.random.poisson(xgp_vis, num_simulaciones)
    
    # Contadores de resultados 1X2
    victorias_local = np.sum(goles_local > goles_visita)
    empates = np.sum(goles_local == goles_visita)
    victorias_visita = np.sum(goles_local < goles_visita)
    
    # Matriz de marcadores exactos (hasta 8x8 goles)
    matriz_marcadores = np.zeros((9, 9), dtype=int)
    for l, v in zip(goles_local, goles_visita):
        if l < 9 and v < 9:
            matriz_marcadores[l, v] += 1
            
    # Porcentajes probabilísticos
    prob_local = (victorias_local / num_simulaciones) * 100
    prob_empate = (empates / num_simulaciones) * 100
    prob_visita = (victorias_visita / num_simulaciones) * 100
    
    return {
        "xgp_local": xgp_loc,
        "xgp_visita": xgp_vis,
        "prob_local": prob_local,
        "prob_empate": prob_empate,
        "prob_visita": prob_visita,
        "matriz_marcadores": matriz_marcadores,
        "num_simulaciones": num_simulaciones
    }


def calcular_escenarios_goles(matriz_marcadores):
    """
    Calcula probabilidades de líneas de Over/Under, BTTS (Ambos Anotan) 
    y los marcadores exactos más probables.
    """
    if matriz_marcadores is None:
        return {'lineas_goles': {}, 'btts_si': 50.0, 'btts_no': 50.0, 'top_marcadores': {}}
    
    total_sims = np.sum(matriz_marcadores)
    if total_sims == 0:
        return {'lineas_goles': {}, 'btts_si': 50.0, 'btts_no': 50.0, 'top_marcadores': {}}
    
    # 1. Líneas de Over / Under
    lineas = [1.5, 2.5, 3.5]
    res_lineas = {}
    for l in lineas:
        over_count = 0
        for i in range(9):
            for j in range(9):
                if (i + j) > l:
                    over_count += matriz_marcadores[i, j]
        res_lineas[f"Over {l}"] = (over_count / total_sims) * 100
        res_lineas[f"Under {l}"] = 100.0 - res_lineas[f"Over {l}"]
        
    # 2. Ambos Anotan (BTTS)
    btts_si_count = np.sum(matriz_marcadores[1:, 1:])
    btts_si = (btts_si_count / total_sims) * 100
    btts_no = 100.0 - btts_si
    
    # 3. Top Marcadores Exactos
    marcadores_flat = []
    for i in range(9):
        for j in range(9):
            cnt = matriz_marcadores[i, j]
            if cnt > 0:
                pct = (cnt / total_sims) * 100
                marcadores_flat.append((f"{i} - {j}", pct))
                
    marcadores_flat.sort(key=lambda x: x[1], reverse=True)
    top_marcadores = dict(marcadores_flat[:5])
    
    return {
        'lineas_goles': res_lineas,
        'btts_si': btts_si,
        'btts_no': btts_no,
        'top_marcadores': top_marcadores
    }


def calcular_handicaps(matriz_marcadores):
    """
    Calcula las probabilidades para coberturas y hándicaps asiáticos / europeos.
    """
    if matriz_marcadores is None:
        return {}
        
    total_sims = np.sum(matriz_marcadores)
    if total_sims == 0:
        return {}
        
    loc_minus_1 = 0
    loc_minus_05 = 0
    dnb_loc = 0
    loc_plus_05 = 0
    loc_plus_1 = 0
    
    for i in range(9):
        for j in range(9):
            cnt = matriz_marcadores[i, j]
            diff = i - j
            
            if diff > 1:
                loc_minus_1 += cnt
            if diff > 0:
                loc_minus_05 += cnt
                dnb_loc += cnt
            if diff >= 0:
                loc_plus_05 += cnt
            if diff > -1:
                loc_plus_1 += cnt
                
    # Normalizar si hay empates para DNB (Draw No Bet)
    empates = np.trace(matriz_marcadores)
    sims_sin_empate = total_sims - empates
    prob_dnb_loc = (dnb_loc / sims_sin_empate * 100) if sims_sin_empate > 0 else 50.0
    
    return {
        'local_minus_1': (loc_minus_1 / total_sims) * 100,
        'local_minus_05': (loc_minus_05 / total_sims) * 100,
        'dnb_local': prob_dnb_loc,
        'local_plus_05': (loc_plus_05 / total_sims) * 100,
        'local_plus_1': (loc_plus_1 / total_sims) * 100,
        
        'visita_minus_1': 100.0 - ((loc_plus_1) / total_sims * 100),
        'visita_minus_05': 100.0 - ((loc_plus_05) / total_sims * 100),
        'dnb_visita': 100.0 - prob_dnb_loc,
        'visita_plus_05': 100.0 - ((loc_minus_05) / total_sims * 100),
        'visita_plus_1': 100.0 - ((loc_minus_1) / total_sims * 100),
    }
