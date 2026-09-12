import math
from datetime import datetime, timedelta
from core.training_db import get_all_activities, get_user_profile

def parse_date_safe(date_str: str) -> datetime:
    clean = str(date_str).replace("T", " ").split(".")[0].strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(clean, fmt)
        except ValueError:
            continue
    return datetime.now()

class WorkloadEngine:
    @staticmethod
    def calculate_blanch_gabbett_risk(acwr: float) -> float:
        risk = 9.98 * (acwr ** 2) - 18.42 * acwr + 11.73
        return max(1.0, min(99.0, round(risk, 1)))

    @staticmethod
    def normalize_borg_rpe(val: float) -> int:
        if val <= 10.0:
            return max(6, min(20, int(round(6.0 + val * 1.4))))
        return max(6, min(20, int(round(val))))

    @staticmethod
    def get_athlete_readiness() -> dict:
        activities = get_all_activities()
        today = datetime.now().date()

        timeline_days = []
        timeline_acwr = []
        timeline_acute = []
        timeline_chronic = []
        timeline_daily_load = []
        timeline_risk = []

        # 28 jours calendaires glissants jusqu'à AUJOURD'HUI
        for offset in range(27, -1, -1):
            day_target = today - timedelta(days=offset)
            timeline_days.append(day_target.strftime("%d/%m"))

            acute_val = sum(
                float(a.get("trimp", 0)) for a in activities 
                if 0 <= (day_target - parse_date_safe(a["start_time"]).date()).days <= 6
            )
            chronic_val = sum(
                float(a.get("trimp", 0)) for a in activities 
                if 0 <= (day_target - parse_date_safe(a["start_time"]).date()).days <= 27
            ) / 4.0

            daily_load = sum(
                float(a.get("trimp", 0)) for a in activities 
                if (day_target - parse_date_safe(a["start_time"]).date()).days == 0
            )

            acwr = round(acute_val / chronic_val, 2) if chronic_val > 10.0 else 1.0
            risk = WorkloadEngine.calculate_blanch_gabbett_risk(acwr)

            timeline_acute.append(round(acute_val, 1))
            timeline_chronic.append(round(chronic_val, 1))
            timeline_acwr.append(acwr)
            timeline_daily_load.append(round(daily_load, 1))
            timeline_risk.append(risk)

        # 14 derniers jours pour l'accueil
        recent_days_labels = []
        recent_distances = []
        recent_durations = []
        for offset in range(13, -1, -1):
            day_target = today - timedelta(days=offset)
            recent_days_labels.append(day_target.strftime("%d/%m"))
            d_sum = sum(
                float(a.get("distance_km", 0.0)) for a in activities 
                if (day_target - parse_date_safe(a["start_time"]).date()).days == 0
            )
            t_sum = sum(
                float(a.get("duration_min", 0.0)) for a in activities 
                if (day_target - parse_date_safe(a["start_time"]).date()).days == 0
            )
            recent_distances.append(round(d_sum, 1))
            recent_durations.append(round(t_sum, 1))

        current_acwr = timeline_acwr[-1] if timeline_acwr else 1.0
        current_acute = timeline_acute[-1] if timeline_acute else 0.0
        current_chronic = timeline_chronic[-1] if timeline_chronic else 0.0
        current_risk = WorkloadEngine.calculate_blanch_gabbett_risk(current_acwr)

        if current_acwr < 0.80:
            readiness = 0.95
            status = "Sous-charge relative (Capacité disponible pour s'entraîner)"
            color = "#3182CE"
        elif 0.80 <= current_acwr <= 1.30:
            readiness = 1.0
            status = "Sweet Spot (Condition optimale & Risque faible)"
            color = "#38A169"
        elif 1.30 < current_acwr <= 1.50:
            readiness = 0.82
            status = "Surcharge modérée (Vigilance requise)"
            color = "#DD6B20"
        else:
            readiness = 0.65
            status = "Zone de danger (Spike critique d'après Blanch & Gabbett)"
            color = "#E53E3E"

        return {
            "acute_load": current_acute,
            "chronic_load": current_chronic,
            "acwr": current_acwr,
            "injury_risk_pct": current_risk,
            "readiness": readiness,
            "status": status,
            "color": color,
            "timeline_days": timeline_days,
            "timeline_acwr": timeline_acwr,
            "timeline_acute": timeline_acute,
            "timeline_chronic": timeline_chronic,
            "timeline_daily_load": timeline_daily_load,
            "timeline_risk": timeline_risk,
            "recent_distances": recent_distances,
            "recent_durations": recent_durations,
            "recent_days_labels": recent_days_labels
        }

    @staticmethod
    def simulate_route_impact(d_plus: float, distance_km: float) -> dict:
        profile = get_user_profile()
        vma = profile.get("vma", 15.0)
        hr_rest = profile.get("hr_rest", 50)
        hr_max = profile.get("hr_max", 185)

        flat_time_min = (distance_km / (vma * 0.65)) * 60.0
        climb_time_min = (d_plus / 100.0) * 6.5
        est_duration_min = round(flat_time_min + climb_time_min, 0)

        est_hr = int(hr_rest + (hr_max - hr_rest) * 0.75)
        delta_hr = (est_hr - hr_rest) / max(1, (hr_max - hr_rest))
        projected_trimp = round(est_duration_min * delta_hr * 0.64 * math.exp(1.92 * delta_hr), 1)

        readiness_data = WorkloadEngine.get_athlete_readiness()
        new_acute = readiness_data["acute_load"] + projected_trimp
        new_acwr = round(new_acute / max(10.0, readiness_data["chronic_load"]), 2)
        new_risk = WorkloadEngine.calculate_blanch_gabbett_risk(new_acwr)

        if new_acwr > 1.5:
            advice = f"DANGER : Bascule en zone rouge (Risque blessure : {new_risk}%)."
            advice_color = "#E53E3E"
        elif new_acwr > 1.3:
            advice = f"ATTENTION : Pic de charge (Risque blessure : {new_risk}%)."
            advice_color = "#DD6B20"
        else:
            advice = f"VALIDÉ : Charge bien absorbée (Risque blessure : {new_risk}%)."
            advice_color = "#38A169"

        hours = int(est_duration_min // 60)
        mins = int(est_duration_min % 60)

        return {
            "duration_str": f"{hours}h{mins:02d}",
            "projected_trimp": projected_trimp,
            "new_acwr": new_acwr,
            "new_risk": new_risk,
            "current_acwr": readiness_data["acwr"],
            "advice": advice,
            "advice_color": advice_color
        }