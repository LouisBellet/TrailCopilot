import requests

def get_recent_weather(lat: float, lon: float) -> dict:
    """Récupère les précipitations sur 72h via Open-Meteo avec repli instantané hors-ligne."""
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&past_days=3&forecast_days=1&"
        f"hourly=precipitation,windspeed_10m,freezinglevel_height&timezone=auto"
    )
    try:
        # Timeout très court : 1.5s pour la connexion, 2s pour la réponse
        resp = requests.get(url, timeout=(1.5, 2.0))
        if resp.status_code == 200:
            data = resp.json()
            hourly = data.get("hourly", {})
            precip = hourly.get("precipitation", [])
            rain_72h = sum(precip[:72]) if len(precip) >= 72 else sum(precip)
            return {
                "rain_72h_mm": round(rain_72h, 1),
                "temp_c": 14.0,
                "is_offline": False
            }
    except Exception:
        # Repli silencieux en mode hors-ligne
        pass

    return {
        "rain_72h_mm": 0.0,
        "temp_c": 12.0,
        "is_offline": True
    }

def get_avalanche_risk(massif_name: str) -> dict:
    """Récupère le risque BERA ou renvoie une estimation par défaut sécurisée."""
    url = f"https://donneespubliques.meteofrance.fr/donnees_libres/Pdf/BRA/BRA.{massif_name}.xml"
    try:
        resp = requests.get(url, timeout=(1.5, 2.0))
        if resp.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.content)
            risk_el = root.find(".//RISQUE")
            if risk_el is not None:
                risk_max = int(risk_el.attrib.get("RISQUEMAX", 1))
                return {"risk_level": risk_max, "is_offline": False}
    except Exception:
        pass

    return {
        "risk_level": 2,  # Risque modéré par défaut
        "is_offline": True
    }