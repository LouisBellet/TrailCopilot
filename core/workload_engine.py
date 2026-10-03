import math
from datetime import datetime, timedelta
from core.training_db import get_user_profile

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
    def compute_readiness(activities: list) -> dict:
        today = datetime.now().date()

        daily_map = {}
        for a in activities:
            d = parse_date_safe(a["start_time"]).date()
            daily_map[d] = daily_map.get(d, 0.0) + float(a.get("trimp", 0.0))

        lambda_a = 2.0 / (7.0 + 1.0)
        lambda_c = 2.0 / (28.0 + 1.0)

        start_date = today - timedelta(days=60)
        curr_date = start_date
        ewma_a = 0.0
        ewma_c = 0.0
        history = {}

        while curr_date <= today:
            load = daily_map.get(curr_date, 0.0)
            ewma_a = load * lambda_a + (1.0 - lambda_a) * ewma_a
            ewma_c = load * lambda_c + (1.0 - lambda_c) * ewma_c

            acute_val = round(ewma_a * 7.0, 1)
            chronic_val = round(ewma_c * 7.0, 1)

            if chronic_val < 3.0:
                acwr = 0.0 if acute_val < 3.0 else min(2.5, round(acute_val / 8.0, 2))
            else:
                acwr = round(acute_val / chronic_val, 2)

            history[curr_date] = {
                "load": load,
                "acute": acute_val,
                "chronic": chronic_val,
                "acwr": acwr,
                "raw_ewma_a": ewma_a,
                "raw_ewma_c": ewma_c
            }
            curr_date += timedelta(days=1)

        timeline_days = []
        timeline_acwr = []
        timeline_acute = []
        timeline_chronic = []
        timeline_daily_load = []

        for offset in range(27, -1, -1):
            day_target = today - timedelta(days=offset)
            h = history.get(day_target, {"load": 0.0, "acute": 0.0, "chronic": 0.0, "acwr": 0.0})
            timeline_days.append(day_target.strftime("%d/%m"))
            timeline_acwr.append(h["acwr"])
            timeline_acute.append(h["acute"])
            timeline_chronic.append(h["chronic"])
            timeline_daily_load.append(h["load"])

        # 1. 14 derniers jours quotidiens (Distance & Temps)
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

        # 2. 8 dernières semaines calendaires (Lundi au Dimanche)
        monday_curr = today - timedelta(days=today.weekday())
        weekly_labels = []
        weekly_distances = []
        weekly_durations_min = []
        weekly_durations_h = []

        for w_offset in range(7, -1, -1):
            start_w = monday_curr - timedelta(weeks=w_offset)
            end_w = start_w + timedelta(days=6)
            weekly_labels.append(f"Sem {start_w.strftime('%d/%m')}")

            w_dist = sum(
                float(a.get("distance_km", 0.0)) for a in activities
                if start_w <= parse_date_safe(a["start_time"]).date() <= end_w
            )
            w_dur = sum(
                float(a.get("duration_min", 0.0)) for a in activities
                if start_w <= parse_date_safe(a["start_time"]).date() <= end_w
            )
            weekly_distances.append(round(w_dist, 1))
            weekly_durations_min.append(round(w_dur, 1))
            weekly_durations_h.append(round(w_dur / 60.0, 1))

        current_acwr = timeline_acwr[-1] if timeline_acwr else 0.0
        current_acute = timeline_acute[-1] if timeline_acute else 0.0
        current_chronic = timeline_chronic[-1] if timeline_chronic else 0.0

        if current_acwr == 0.0:
            readiness = 0.90
            status = "Sous-charge totale (Désentraînement / Inactif)"
            color = "#3182CE"
        elif current_acwr < 0.80:
            readiness = 0.95
            status = "Sous-charge relative (Capacité disponible pour s'entraîner)"
            color = "#3182CE"
        elif 0.80 <= current_acwr <= 1.30:
            readiness = 1.0
            status = "Sweet Spot (Progression optimale & Risque faible)"
            color = "#38A169"
        elif 1.30 < current_acwr <= 1.50:
            readiness = 0.82
            status = "Surcharge modérée (Vigilance requise)"
            color = "#DD6B20"
        else:
            readiness = 0.65
            status = "Zone de danger (Pic critique de fatigue)"
            color = "#E53E3E"

        tomorrow_label = (today + timedelta(days=1)).strftime("%d/%m")

        return {
            "acute_load": current_acute,
            "chronic_load": current_chronic,
            "acwr": current_acwr,
            "readiness": readiness,
            "status": status,
            "color": color,
            "timeline_days": timeline_days,
            "timeline_acwr": timeline_acwr,
            "timeline_acute": timeline_acute,
            "timeline_chronic": timeline_chronic,
            "timeline_daily_load": timeline_daily_load,
            "recent_distances": recent_distances,
            "recent_durations": recent_durations,
            "recent_days_labels": recent_days_labels,
            "weekly_labels": weekly_labels,
            "weekly_distances": weekly_distances,
            "weekly_durations_min": weekly_durations_min,
            "weekly_durations_h": weekly_durations_h,
            "tomorrow_label": tomorrow_label,
            "projections": [],
            "today_ewma_a": history[today]["raw_ewma_a"],
            "today_ewma_c": history[today]["raw_ewma_c"]
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

        from core.data_manager import DataManager
        readiness_data = DataManager.get_readiness()

        ewma_a = readiness_data.get("today_ewma_a", 10.0)
        ewma_c = readiness_data.get("today_ewma_c", 10.0)
        l_a = 2.0 / 8.0
        l_c = 2.0 / 29.0
        next_a = (projected_trimp * l_a + (1.0 - l_a) * ewma_a) * 7.0
        next_c = (projected_trimp * l_c + (1.0 - l_c) * ewma_c) * 7.0
        new_acwr = round(next_a / max(3.0, next_c), 2)

        if new_acwr > 1.5:
            advice = "DANGER : Bascule en zone rouge de surmenage."
            advice_color = "#E53E3E"
        elif new_acwr > 1.3:
            advice = "ATTENTION : Pic de charge temporaire."
            advice_color = "#DD6B20"
        else:
            advice = "VALIDÉ : Charge idéale pour progresser."
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