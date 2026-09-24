import pandas as pd  
import os  
  
HISTORIAL_FILE = 'historial_partidos.csv'  
  
def guardar_partido(datos_dict):  
    df_nuevo = pd.DataFrame([datos_dict])  
    if not os.path.exists(HISTORIAL_FILE):  
        df_nuevo.to_csv(HISTORIAL_FILE, index=False)  
    else:  
        df_nuevo.to_csv(HISTORIAL_FILE, mode='a', header=False, index=False)  
  
def cargar_historial():  
    if os.path.exists(HISTORIAL_FILE):  
        return pd.read_csv(HISTORIAL_FILE)  
    return pd.DataFrame()  
