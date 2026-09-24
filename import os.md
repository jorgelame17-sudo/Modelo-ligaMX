import os  
import requests  
  
API_KEY = os.getenv("API_FOOTBALL_KEY", "")  
  
def obtener_partidos_proximos():  
    # Retorna partidos de prueba (mock) si no hay clave cargada  
    if not API_KEY:  
        return [  
            {"id": 1, "partido": "Querétaro vs León", "local": "Querétaro", "visita": "León"},  
            {"id": 2, "partido": "Tigres vs América", "local": "Tigres", "visita": "América"},  
            {"id": 3, "partido": "Chivas vs Pumas", "local": "Chivas", "visita": "Pumas"}  
        ]  
      
    url = "https://v3.football.api-sports.io/fixtures?league=262&next=5"  
    headers = {"x-apisports-key": API_KEY}  
    try:  
        response = requests.get(url, headers=headers).json()  
        partidos = []  
        for item in response.get('response', []):  
            partidos.append({  
                "id": item['fixture']['id'],  
                "partido": f"{item['teams']['home']['name']} vs {item['teams']['away']['name']}",  
                "local": item['teams']['home']['name'],  
                "visita": item['teams']['away']['name']  
            })  
        return partidos if partidos else obtener_partidos_proximos()  
    except:  
        return obtener_partidos_proximos()  
  
def obtener_stats_equipo(nombre_equipo):  
    # Valores estadísticos base  
    return {  
        'puntos_partido': 1.45,  
        'goles_favor': 1.40,  
        'goles_contra': 1.10,  
        'posesion': 50.0,  
        'tiros': 12.5,  
        'tiros_puerta': 4.5  
    }  
