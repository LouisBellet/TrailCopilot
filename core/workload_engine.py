import math
from datetime import datetime, timedelta
from core.training_db import get_all_activities, get_latest_health, get_health_baselines, get_user_profile

class WorkloadEngine:
    @staticmethod
    def parse_date_safe(date_str: str) -> datetime:
        """Convertit une chaîne de date en objet datetime, avec tolérance aux formats variés."""
        clean = str(date_str).replace("T", " ").split(".")[0].strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(clean, fmt)
            except ValueError:
                continue
        return datetime.now()

    @staticmethod
    def get_athlete_readiness() -> dict:
        activities = get_all_activities()
        if not activities:
            return {
                "acute_load": 0.0, "chronic_load": 0.0, "acwr": 1.0,
                "readiness": 1.0, "status": "Profil Neutre", "color": "#38A169",
                "timeline_days": [], "timeline_acwr": [], "recovery_score": 80
            }

        dates = [WorkloadEngine.parse_date_safe(a["start_time"]) for a in activities]
        ref_date = max(dates)

        timeline_days = []
        timeline_acwr = []

        for offset in range(27, -1, -1):
            day_target = ref_date - timedelta(days=offset)
            timeline_days.append(day_target.strftime("%d/%m"))

            acute_t = sum(a.get("trimp", 0) for a in activities 
                          if 0 <= (day_target - WorkloadEngine.parse_date_safe(a["start_time"])).days <= 7)
            chronic_t = sum(a.get("trimp", 0) for a in activities 
                            if 0 <= (day_target - WorkloadEngine.parse_date_safe(a["start_time"])).days <= 28) / 4.0
            
            val = round(acute_t / chronic_t, 2) if chronic_t > 10 else 1.0
            timeline_acwr.append(val)

        current_acwr = timeline_acwr[-1] if timeline_acwr else 1.0
        acute_load = round(sum(a.get("trimp", 0) for a in activities if 0 <= (ref_date - WorkloadEngine.parse_date_safe(a["start_time"])).days <= 7), 1)
        chronic_load = round(sum(a.get("trimp", 0) for a in activities if 0 <= (ref_date - WorkloadEngine.parse_date_safe(a["start_time"])).days <= 28) / 4.0, 1)

        # 2. Prise en compte de la santé quotidienne (VFC, RHR, Sommeil)
        health = get_latest_health()
        baselines = get_health_baselines()
        rec_score = 80

        if health:
            rec_score = health.get("recovery_score", 80)
        else:
            # Calcul estimé par défaut
            if current_acwr > 1.5:
                rec_score = 55
            elif current_acwr > 1.3:
                rec_score = 70

        # 3. Interprétation globale
        if current_acwr < 0.8:
            readiness = 0.95
            status = "Sous-charge / Récupéré"
            color = "#3182CE"
        elif 0.8 <= current_acwr <= 1.3:
            readiness = 1.0
            status = "Zone Optimale (Sweet Spot)"
            color = "#38A169"
        elif 1.3 < current_acwr <= 1.5:
            readiness = 0.82
            status = "Surcharge modérée"
            color = "#DD6B20"
        else:
            readiness = 0.65
            status = "Zone de danger (Surcharge critique)"
            color = "#E53E3E"

        # Modulation selon le score VFC/Santé du jour
        if rec_score < 60:
            readiness = round(readiness * 0.85, 2)
            status += " + Récupération nerveuse basse"

        return {
            "acute_load": acute_load,
            "chronic_load": chronic_load,
            "acwr": current_acwr,
            "readiness": readiness,
            "status": status,
            "color": color,
            "timeline_days": timeline_days,
            "timeline_acwr": timeline_acwr,
            "recovery_score": rec_score
        }

    @staticmethod
    def simulate_route_impact(d_plus: float, distance_km: float) -> dict:
        """
        Simulateur 'What-If' : Estime l'impact physiologique prévisionnel
        si l'athlète réalise ce topo aujourd'hui.
        """
        profile = get_user_profile()
        vma = profile.get("vma", 15.0)
        hr_rest = profile.get("hr_rest", 50)
        hr_max = profile.get("hr_max", 185)

        # Estimation du temps : règle de Naismith ajustée (1 km = 12 min à plat, 100m D+ = 6 min)
        flat_time_min = (distance_km / (vma * 0.65)) * 60.0
        climb_time_min = (d_plus / 100.0) * 6.5
        est_duration_min = round(flat_time_min + climb_time_min, 0)

        # Fréquence cardiaque estimée en endurance active (75% de la réserve)
        est_hr = int(hr_rest + (hr_max - hr_rest) * 0.75)

        # TRIMP projeté
        delta_hr = (est_hr - hr_rest) / (hr_max - hr_rest)
        projected_trimp = round(est_duration_min * delta_hr * 0.64 * math.exp(1.92 * delta_hr), 1)

        # Impact sur l'ACWR
        readiness_data = WorkloadEngine.get_athlete_readiness()
        cur_acute = readiness_data["acute_load"]
        cur_chronic = readiness_data["chronic_load"]

        new_acute = cur_acute + projected_trimp
        new_acwr = round(new_acute / max(10.0, cur_chronic), 2)

        if new_acwr > 1.5:
            advice = "DANGER : Cette sortie vous fera basculer en zone rouge de surmenage."
            advice_color = "#E53E3E"
        elif new_acwr > 1.3:
            advice = "ATTENTION : Charge élevée, prévoyez au moins 48 h de repos après."
            advice_color = "#DD6B20"
        else:
            advice = "VALIDÉ : Charge parfaitement absorbable par votre forme actuelle."
            advice_color = "#38A169"

        hours = int(est_duration_min // 60)
        mins = int(est_duration_min % 60)

        return {
            "duration_str": f"{hours}h{mins:02d}",
            "projected_trimp": projected_trimp,
            "new_acwr": new_acwr,
            "current_acwr": readiness_data["acwr"],
            "advice": advice,
            "advice_color": advice_color
        }