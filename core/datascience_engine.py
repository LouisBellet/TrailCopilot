from datetime import datetime
import numpy as np
from core.training_db import get_user_profile

RUN_KEYWORDS = ["course", "trail", "run", "footing"]
EXCLUDE_KEYWORDS = ["velo", "vélo", "bike", "cycling", "natation", "swim", "ski", "yoga", "renfo", "muscu", "marche", "rando"]

def is_run_or_trail(sport_str: str) -> bool:
    s = str(sport_str).lower().strip()
    if not s or any(bad in s for bad in EXCLUDE_KEYWORDS):
        return False
    return any(good in s for good in RUN_KEYWORDS)

def parse_date_short(date_str: str) -> str:
    clean = str(date_str).replace("T", " ").split(".")[0].strip()[:10]
    try:
        return datetime.strptime(clean, "%Y-%m-%d").strftime("%d/%m")
    except Exception:
        return clean[-5:].replace("-", "/")

def compute_polarization_zones(records: list, hr_rest: int, hr_max: int, fallback_rpe: int = 13) -> tuple:
    """
    Détermine la ventilation du temps en 3 tiers selon le modèle de Seiler :
    - Basse intensité (Z1-Z2) : < 75% FC Réserve
    - Seuil / Tempo (Z3)      : 75% à 85% FC Réserve
    - Haute intensité (Z4-Z5) : > 85% FC Réserve
    """
    valid_hrs = [r.get("heart_rate") for r in records if r.get("heart_rate") and r.get("heart_rate") > hr_rest]

    if len(valid_hrs) >= 20 and hr_max > hr_rest:
        res = hr_max - hr_rest
        t1 = hr_rest + res * 0.72
        t2 = hr_rest + res * 0.85

        z_low = sum(1 for h in valid_hrs if h < t1)
        z_mod = sum(1 for h in valid_hrs if t1 <= h < t2)
        z_high = sum(1 for h in valid_hrs if h >= t2)
        tot = len(valid_hrs)
        return (round(z_low / tot * 100, 1), round(z_mod / tot * 100, 1), round(z_high / tot * 100, 1))

    # Repli estimé via l'effort perçu Borg si pas de cardio haute fréquence
    if fallback_rpe <= 12:
        return (90.0, 10.0, 0.0)
    elif fallback_rpe <= 15:
        return (35.0, 55.0, 10.0)
    else:
        return (15.0, 25.0, 60.0)

def run_pure_kmeans(data: np.ndarray, k: int = 3, max_iter: int = 30) -> np.ndarray:
    n = len(data)
    if n < k:
        return np.zeros(n, dtype=int)
    rng = np.random.RandomState(42)
    indices = rng.choice(n, size=k, replace=False)
    centers = data[indices]
    labels = np.zeros(n, dtype=int)

    for _ in range(max_iter):
        distances = np.linalg.norm(data[:, np.newaxis] - centers, axis=2)
        new_labels = np.argmin(distances, axis=1)
        if np.array_equal(labels, new_labels):
            break
        labels = new_labels
        for j in range(k):
            members = data[labels == j]
            if len(members) > 0:
                centers[j] = members.mean(axis=0)
    return labels

class DataScienceEngine:
    @staticmethod
    def get_focused_analytics(activities: list) -> dict:
        if not activities:
            return {"empty": True, "reason": "no_activities"}

        profile = get_user_profile()
        hr_rest = profile.get("hr_rest", 50)
        hr_max = profile.get("hr_max", 185)

        runs = []
        for a in reversed(activities):
            sport = a.get("sport", "")
            if not is_run_or_trail(sport):
                continue

            dist = float(a.get("distance_km") or 0.0)
            dur = float(a.get("duration_min") or 0.0)
            rpe = float(a.get("rpe") or 13.0)
            raw_hr = a.get("avg_hr")

            if dist < 0.5 or dur < 3.0:
                continue

            speed_kmh = round(dist / (dur / 60.0), 2)
            has_real_hr = bool(raw_hr and int(raw_hr) > 40)
            fc_val = int(raw_hr) if has_real_hr else int(rpe * 10)
            ef_ratio = round((speed_kmh / fc_val) * 100.0, 2)

            records = a.get("records") or []
            z_low, z_mod, z_high = compute_polarization_zones(records, hr_rest, hr_max, rpe)

            runs.append({
                "id": a["id"],
                "date": parse_date_short(a.get("start_time", "")),
                "name": a.get("name", "Sortie"),
                "sport": sport,
                "dist": dist,
                "dur": dur,
                "speed": speed_kmh,
                "fc": fc_val,
                "has_real_hr": has_real_hr,
                "rpe": rpe,
                "trimp": float(a.get("trimp") or 0.0),
                "ef": ef_ratio,
                "z_low": z_low,
                "z_mod": z_mod,
                "z_high": z_high
            })

        if not runs:
            return {"empty": True, "reason": "no_running_found"}

        n = len(runs)
        dates = [r["date"] for r in runs]
        ef_list = [r["ef"] for r in runs]
        speeds = [r["speed"] for r in runs]
        dists = [r["dist"] for r in runs]
        fcs = [r["fc"] for r in runs]
        rpes = [r["rpe"] for r in runs]
        z_lows = [r["z_low"] for r in runs]
        z_mods = [r["z_mod"] for r in runs]
        z_highs = [r["z_high"] for r in runs]

        # K-Means Allure / Distance
        k = 3 if n >= 6 else (2 if n >= 3 else 1)
        matrix = np.column_stack([dists, speeds])
        std_matrix = (matrix - matrix.mean(axis=0)) / np.maximum(matrix.std(axis=0), 1e-4)
        labels = run_pure_kmeans(std_matrix, k=k)

        cluster_names = {}
        for c_idx in range(k):
            mask = (labels == c_idx)
            if not np.any(mask):
                continue
            mean_d = float(np.mean(matrix[mask, 0]))
            mean_v = float(np.mean(matrix[mask, 1]))
            if mean_d > np.median(dists) * 1.25:
                name = "Sortie Longue"
            elif mean_v > np.median(speeds) * 1.05:
                name = "Séance Seuil / Allure"
            else:
                name = "Endurance / Récupération"
            cluster_names[c_idx] = name

        return {
            "empty": False,
            "runs": runs,
            "dates": dates,
            "ef_list": ef_list,
            "speeds": speeds,
            "dists": dists,
            "fcs": fcs,
            "rpes": rpes,
            "z_lows": z_lows,
            "z_mods": z_mods,
            "z_highs": z_highs,
            "clusters": labels.tolist(),
            "cluster_names": cluster_names,
            "last_run_idx": n - 1
        }