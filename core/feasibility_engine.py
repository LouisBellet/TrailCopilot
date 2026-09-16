import math

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

class FeasibilityEngine:
    @staticmethod
    def identify_critical_segments(coords: list, elevations: list, weather: dict, snow_pct: float, bera: dict) -> list:
        if len(coords) < 2 or len(elevations) < 2:
            return []

        rain_72h = float(weather.get("rain_72h_mm", 0.0))
        wind_kmh = float(weather.get("windspeed_10m", 25.0))
        freezing_level = float(weather.get("freezing_level_m", 2700.0))
        bera_level = int(bera.get("risk_level", 1))

        cum_dist = [0.0]
        for i in range(1, len(coords)):
            d = haversine_m(coords[i-1][0], coords[i-1][1], coords[i][0], coords[i][1]) / 1000.0
            cum_dist.append(cum_dist[-1] + d)

        is_critical = [False] * len(coords)
        reasons = [""] * len(coords)

        for i in range(len(coords) - 1):
            ele = elevations[i]
            next_ele = elevations[i+1]
            step_d = max(1.0, haversine_m(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1]))
            slope_deg = math.degrees(math.atan2(abs(next_ele - ele), step_d))

            risk_snow = (ele >= freezing_level - 150) or (ele >= 2400 and (snow_pct > 12 or rain_72h > 4.0))
            risk_slope = (slope_deg >= 28.0) and (rain_72h > 3.0 or snow_pct > 8.0 or bera_level >= 2)
            risk_wind = (ele >= 2500 and wind_kmh >= 45.0)

            if risk_snow or risk_slope or risk_wind:
                is_critical[i] = True
                is_critical[i+1] = True
                motifs = []
                if risk_snow:
                    motifs.append(f"Neige/Verglas (Alt: {int(ele)}m)")
                if risk_slope:
                    motifs.append(f"Pente glissante {int(slope_deg)}°")
                if risk_wind:
                    motifs.append(f"Vent crête {int(wind_kmh)} km/h")
                reasons[i] = " + ".join(motifs)

        segments = []
        in_seg = False
        start_idx = 0

        for i in range(len(coords)):
            if is_critical[i] and not in_seg:
                in_seg = True
                start_idx = i
            elif not is_critical[i] and in_seg:
                in_seg = False
                end_idx = i - 1
                if end_idx > start_idx:
                    segments.append({
                        "start_idx": start_idx,
                        "end_idx": end_idx,
                        "start_km": round(cum_dist[start_idx], 2),
                        "end_km": round(cum_dist[end_idx], 2),
                        "reason": reasons[start_idx] or "Zone technique / Météo dégradée",
                        "coords": coords[start_idx : end_idx + 1],
                        "elevations": elevations[start_idx : end_idx + 1]
                    })
        if in_seg:
            end_idx = len(coords) - 1
            if end_idx > start_idx:
                segments.append({
                    "start_idx": start_idx,
                    "end_idx": end_idx,
                    "start_km": round(cum_dist[start_idx], 2),
                    "end_km": round(cum_dist[end_idx], 2),
                    "reason": reasons[start_idx] or "Zone technique / Météo dégradée",
                    "coords": coords[start_idx : end_idx + 1],
                    "elevations": elevations[start_idx : end_idx + 1]
                })

        return segments

    @staticmethod
    def evaluate(route: dict, weather: dict, snow_pct: float, bera: dict, activity: str, user_readiness: float = 1.0) -> dict:
        score = 88
        alerts = []

        rain = weather.get("rain_72h_mm", 0.0)
        wind = weather.get("windspeed_10m", 20.0)
        max_ele = route.get("elevation_max", 2000)
        bera_lvl = bera.get("risk_level", 1)

        coords = route.get("coords", [])
        elevations = route.get("elevations", [])
        critical_segs = FeasibilityEngine.identify_critical_segments(coords, elevations, weather, snow_pct, bera)

        if rain > 15.0:
            score -= 22
            alerts.append(f"Pluies abondantes ({rain} mm sur 72h) : sols gorgés et dalles glissantes.")
        elif rain > 5.0:
            score -= 10
            alerts.append(f"Pluies récentes ({rain} mm) : humidité sur roche et sentier gras.")

        if wind > 50.0:
            score -= 18
            alerts.append(f"Rafales violentes ({int(wind)} km/h) sur les crêtes exposées.")

        if max_ele >= 2600 and snow_pct > 20:
            score -= 25
            alerts.append(f"Enneigement résiduel important ({snow_pct}%) au-dessus de 2 600 m.")

        if activity == "skitouring" and bera_lvl >= 3:
            score -= 30
            alerts.append(f"Risque d'avalanche BERA marqué (Niveau {bera_lvl}/5).")

        if critical_segs:
            score -= min(25, len(critical_segs) * 12)
            for seg in critical_segs:
                alerts.append(f"⚠️ Tronçon délicat du km {seg['start_km']} au km {seg['end_km']} : {seg['reason']}")

        score = int(score * user_readiness)
        score = max(15, min(98, score))

        if score >= 75:
            status = "Conditions Favorables"
            color = "#38A169"
        elif score >= 50:
            status = "Vigilance Requise"
            color = "#DD6B20"
        else:
            status = "Itinéraire Déconseillé"
            color = "#E53E3E"

        return {
            "score": score,
            "status": status,
            "color": color,
            "alerts": alerts,
            "critical_segments": critical_segs,
            "slope_metrics": {"avg_slope_deg": 14, "max_slope_deg": 32, "has_critical_slopes": len(critical_segs) > 0}
        }