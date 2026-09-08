from core.dem_engine import DEMEngine

class FeasibilityEngine:
    @staticmethod
    def evaluate(route: dict, weather: dict, snow_pct: float, bera: dict, activity: str, user_readiness: float = 1.0) -> dict:
        score = 100
        alerts = []
        
        # 1. Évaluation météo
        rain = weather.get("rain_72h_mm", 0)
        if rain > 40:
            score -= 30
            alerts.append(f"Sol très boueux / lessivé (Pluie 72h : {rain} mm)")
        elif rain > 20:
            score -= 15
            alerts.append(f"Humidité marquée sur les zones d'ombre ({rain} mm récents)")

        # 2. Pentes du tracé
        coords = route.get("coords", [])
        elevations = route.get("elevations", [1000, 1500])
        slope_metrics = DEMEngine.analyze_slopes(coords, elevations)

        # 3. Règles d'arbitrage par discipline
        if activity == "trail":
            if snow_pct > 30:
                score -= 40
                alerts.append(f"Névés persistants sur le secteur (Couverture satellite : {snow_pct:.0f}%)")
            elif snow_pct > 10:
                score -= 20
                alerts.append(f"Bancs de neige résiduelle ({snow_pct:.0f}%)")
                
            if slope_metrics["has_critical_slopes"]:
                score -= 15
                alerts.append(f"Pentes soutenues (Max: {slope_metrics['max_slope_deg']}°) : attention sur sol glissant")
        else:
            if snow_pct < 40:
                score -= 45
                alerts.append(f"Enneigement discontinu : portage requis ({snow_pct:.0f}% neige)")
            
            risk = bera.get("risk_level", 1)
            if risk >= 3 and slope_metrics["has_critical_slopes"]:
                score -= 40
                alerts.append(f"DANGER AVALANCHE : Risque {risk}/5 et pentes > 30°")
            elif risk >= 3:
                score -= 20
                alerts.append(f"Vigilance avalanche : Risque {risk}/5 sur le massif")

        # 4. Modulateur physiologique interne (Ratio de fatigue de l'athlète)
        d_minus = route.get("elevation_loss", route.get("elevation_gain", 0))
        if user_readiness < 0.8:
            penalty = int((1.0 - user_readiness) * 45)
            score -= penalty
            if d_minus > 800:
                alerts.append(f"Fatigue aiguë détectée (ACWR élevé) : ce dénivelé négatif ({d_minus} m) risque de casser les fibres musculaires.")
            else:
                alerts.append("Niveau de fatigue résiduelle élevé : sortie exigeante pour votre état de forme actuel.")

        # 5. Normalisation
        score = max(5, min(100, score))
        if score >= 75:
            status = "Conditions Favorables"
            color = "#2ECC71"
        elif score >= 50:
            status = "Vigilance & Technique"
            color = "#E67E22"
        else:
            status = "Déconseillé"
            color = "#E74C3C"

        return {
            "score": score,
            "status": status,
            "color": color,
            "alerts": alerts,
            "snow_pct": snow_pct,
            "slope_metrics": slope_metrics
        }