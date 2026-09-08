import os
import math
from datetime import datetime
from fitparse import FitFile
from core.training_db import get_user_profile

def semicircles_to_degrees(semicircles):
    """Convertit l'unité semicircles de Garmin/FIT en degrés WGS84."""
    if semicircles is None:
        return None
    return round(float(semicircles) * (180.0 / (2**31)), 5)

def calculate_banister_trimp(duration_min: float, avg_hr: float, hr_rest: int, hr_max: int) -> float:
    """
    Calcule la charge cardiaque selon le modèle de Banister :
    TRIMP = Durée (min) * Delta_FC * 0.64 * exp(1.92 * Delta_FC)
    """
    if avg_hr <= hr_rest or hr_max <= hr_rest:
        return 0.0
    delta_hr = (avg_hr - hr_rest) / (hr_max - hr_rest)
    delta_hr = max(0.0, min(1.0, delta_hr))
    trimp = duration_min * delta_hr * 0.64 * math.exp(1.92 * delta_hr)
    return round(trimp, 1)

def parse_fit_file(file_path: str) -> dict:
    """
    Lit et extrait l'ensemble des séries temporelles d'un fichier .fit.
    """
    profile = get_user_profile()
    hr_rest = profile["hr_rest"]
    hr_max = profile["hr_max"]

    fitfile = FitFile(file_path)

    # 1. Extraction des métadonnées de session globale
    sport = "Trail / Rando"
    start_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
    distance_km = 0.0
    total_ascent = 0.0
    total_descent = 0.0
    duration_min = 0.0
    avg_hr = 0
    session_max_hr = 0

    for session in fitfile.get_messages("session"):
        session_data = {f.name: f.value for f in session}
        if "sport" in session_data and session_data["sport"]:
            sport = str(session_data["sport"]).capitalize()
        if "start_time" in session_data and session_data["start_time"]:
            start_time = session_data["start_time"].strftime("%Y-%m-%d %H:%M:%S")
        if "total_distance" in session_data and session_data["total_distance"]:
            distance_km = round(session_data["total_distance"] / 1000.0, 2)
        if "total_ascent" in session_data and session_data["total_ascent"]:
            total_ascent = round(float(session_data["total_ascent"]), 0)
        if "total_descent" in session_data and session_data["total_descent"]:
            total_descent = round(float(session_data["total_descent"]), 0)
        if "total_timer_time" in session_data and session_data["total_timer_time"]:
            duration_min = round(session_data["total_timer_time"] / 60.0, 1)
        if "avg_heart_rate" in session_data and session_data["avg_heart_rate"]:
            avg_hr = int(session_data["avg_heart_rate"])
        if "max_heart_rate" in session_data and session_data["max_heart_rate"]:
            session_max_hr = int(session_data["max_heart_rate"])

    # 2. Extraction des points chronométrés (records)
    records = []
    hr_samples = []
    prev_alt = None
    calc_ascent = 0.0
    calc_descent = 0.0

    for record in fitfile.get_messages("record"):
        rec = {f.name: f.value for f in record}
        lat = semicircles_to_degrees(rec.get("position_lat"))
        lon = semicircles_to_degrees(rec.get("position_long"))
        alt = rec.get("enhanced_altitude") or rec.get("altitude")
        hr = rec.get("heart_rate")
        timestamp = rec.get("timestamp")
        dist = rec.get("distance")

        if alt is not None and prev_alt is not None:
            diff = alt - prev_alt
            if diff > 0.5:
                calc_ascent += diff
            elif diff < -0.5:
                calc_descent += abs(diff)
        if alt is not None:
            prev_alt = alt

        if hr:
            hr_samples.append(hr)

        # Enregistrement allégé (1 point toutes les 3 secondes pour préserver la mémoire)
        if alt is not None or hr is not None:
            records.append({
                "time": timestamp.strftime("%H:%M:%S") if timestamp else "",
                "lat": lat,
                "lon": lon,
                "alt": round(alt, 1) if alt is not None else None,
                "hr": hr,
                "distance_km": round(dist / 1000.0, 2) if dist is not None else None
            })

    # Ajustement des totaux si la session FIT n'avait pas d'en-tête récapitulatif
    if total_ascent == 0.0:
        total_ascent = round(calc_ascent, 0)
    if total_descent == 0.0:
        total_descent = round(calc_descent, 0)
    if avg_hr == 0 and hr_samples:
        avg_hr = int(sum(hr_samples) / len(hr_samples))
    if session_max_hr == 0 and hr_samples:
        session_max_hr = int(max(hr_samples))
    if duration_min == 0.0 and len(records) > 1:
        duration_min = round(len(records) / 60.0, 1)

    trimp = calculate_banister_trimp(duration_min, avg_hr, hr_rest, hr_max)

    return {
        "filename": os.path.basename(file_path),
        "name": f"{sport} du {start_time[:10]}",
        "sport": sport,
        "start_time": start_time,
        "distance_km": distance_km,
        "d_plus": total_ascent,
        "d_minus": total_descent,
        "duration_min": duration_min,
        "avg_hr": avg_hr,
        "max_hr": session_max_hr,
        "trimp": trimp,
        "records": records
    }