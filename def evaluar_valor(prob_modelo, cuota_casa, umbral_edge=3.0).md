def evaluar_valor(prob_modelo, cuota_casa, umbral_edge=3.0):  
    if cuota_casa <= 1.0:  
        return 0.0, 0.0, False  
      
    prob_implicita = (1 / cuota_casa) * 100  
    edge = prob_modelo - prob_implicita  
    tiene_valor = edge >= umbral_edge  
      
    return round(prob_implicita, 1), round(edge, 1), tiene_valor  
