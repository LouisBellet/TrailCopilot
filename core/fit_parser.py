import os
import math
from datetime import datetime
import fitparse
from core.training_db import get_user_profile

def calculate_banister_trimp(duration_min: float, hr: float, hr_rest: int, hr_max: int) -> float:
    if hr <= hr_rest or hr_max <= hr_rest:
        return 0.0
    delta_hr = (hr - hr_rest) / (hr_max - hr_rest)
    delta_hr = max(0.0, min(1.0, delta_hr))
    trimp = duration_min * delta_hr * 0.64 * math.exp(1.92 * delta_hr)
    return round(trimp, 1)

def calculate_continuous_trimp(records: list, hr_rest: int, hr_max: int) -> float:
    if not records or hr_max <= hr_rest:
        return 0.0

    total_trimp = 0.0
    last_time = None

    for r in records:
        t = r.get("timestamp")
        hr = r.get("heart_rate")

        if not t or hr is None or hr <= hr_rest:
            if t:
                last_time = t
            continue

        if last_time is not None and isinstance(t, datetime) and isinstance(last_time, datetime):
            dt_sec = max(0.5, min(15.0, (t - last_time).total_seconds()))
            dt_min = dt_sec / 60.0
        else:
            dt_min = 1.0 / 60.0

        last_time = t
        delta_hr = (hr - hr_rest) / (hr_max - hr_rest)
        delta_hr = max(0.0, min(1.0, delta_hr))
        total_trimp += dt_min * delta_hr * 0.64 * math.exp(1.92 * delta_hr)

    return round(total_trimp, 1)

def extract_watch_rpe(fit_file: fitparse.FitFile) -> int:
    rpe_raw = None
    for session in fit_file.get_messages("session"):
        for field in session.fields:
            name = (field.name or "").lower()
            if any(k in name for k in ("perceived_exertion", "rpe", "feel", "effort")):
                val = field.value
                if val is not None and isinstance(val, (int, float)) and val > 0:
                    rpe_raw = float(val)
                    break
        if rpe_raw is not None:
            break

    if rpe_raw is None:
        for act in fit_file.get_messages("activity"):
            for field in act.fields:
                name = (field.name or "").lower()
                if any(k in name for k in ("perceived_exertion", "rpe", "feel")):
                    val = field.value
                    if val is not None and isinstance(val, (int, float)) and val > 0:
                        rpe_raw = float(val)
                        break
            if rpe_raw is not None:
                break

    if rpe_raw is not None:
        if rpe_raw > 20:
            rpe_raw = rpe_raw / 10.0
        if rpe_raw <= 10.0:
            return max(6, min(20, int(round(6.0 + rpe_raw * 1.4))))
        return max(6, min(20, int(round(rpe_raw))))

    return 13

def parse_fit_file(file_path: str) -> dict:
    fit = fitparse.FitFile(file_path)
    profile = get_user_profile()
    hr_rest = profile.get("hr_rest", 50)
    hr_max = profile.get("hr_max", 185)

    records = []
    total_dist = 0.0
    total_dur_min = 0.0
    start_time = None
    sport = "Course"
    d_plus = 0.0
    d_minus = 0.0
    hrs = []
    last_alt = None

    for msg in fit.get_messages("record"):
        rec = {}
        for f in msg.fields:
            val = f.value
            name = f.name
            if name == "timestamp" and val is not None:
                rec["timestamp"] = val
            elif name in ("altitude", "enhanced_altitude") and val is not None:
                rec["altitude"] = round(float(val), 1)
            elif name in ("speed", "enhanced_speed") and val is not None:
                rec["speed"] = round(float(val) * 3.6, 2)
            elif name == "heart_rate" and val is not None:
                rec["heart_rate"] = int(val)
                hrs.append(rec["heart_rate"])
            elif name == "distance" and val is not None:
                rec["distance"] = round(float(val) / 1000.0, 3)

        if "timestamp" in rec:
            if start_time is None:
                start_time = rec["timestamp"]

            alt = rec.get("altitude")
            if alt is not None:
                if last_alt is not None:
                    diff = alt - last_alt
                    if diff > 0.4:
                        d_plus += diff
                    elif diff < -0.4:
                        d_minus += abs(diff)
                last_alt = alt

            records.append(rec)

    for msg in fit.get_messages("session"):
        for f in msg.fields:
            if f.name == "total_distance" and f.value is not None:
                total_dist = round(float(f.value) / 1000.0, 2)
            elif f.name == "total_elapsed_time" and f.value is not None:
                total_dur_min = round(float(f.value) / 60.0, 1)
            elif f.name == "sport" and f.value is not None:
                sport_raw = str(f.value).lower()
                if "trail" in sport_raw:
                    sport = "Trail"
                elif "running" in sport_raw:
                    sport = "Course"
                elif "cycling" in sport_raw or "biking" in sport_raw:
                    sport = "Vélo"
                elif "hiking" in sport_raw:
                    sport = "Randonnée"
            elif f.name == "total_ascent" and f.value is not None:
                d_plus = float(f.value)
            elif f.name == "total_descent" and f.value is not None:
                d_minus = float(f.value)

    if not total_dist and records:
        dists = [r["distance"] for r in records if "distance" in r]
        if dists:
            total_dist = round(max(dists), 2)

    if not total_dur_min and records:
        t_start = records[0].get("timestamp")
        t_end = records[-1].get("timestamp")
        if isinstance(t_start, datetime) and isinstance(t_end, datetime):
            total_dur_min = round((t_end - t_start).total_seconds() / 60.0, 1)

    avg_hr = int(sum(hrs) / len(hrs)) if hrs else 0
    max_hr = int(max(hrs)) if hrs else 0

    if hrs:
        trimp = calculate_continuous_trimp(records, hr_rest, hr_max)
    else:
        trimp = calculate_banister_trimp(total_dur_min, avg_hr, hr_rest, hr_max)

    rpe_val = extract_watch_rpe(fit)
    filename = os.path.basename(file_path)
    start_str = start_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(start_time, datetime) else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Downsampling léger si le tracé est volumineux (> 3600 points) pour fluidité
    serializable_records = []
    step = max(1, len(records) // 3000)
    for r in records[::step]:
        rc = dict(r)
        if "timestamp" in rc and isinstance(rc["timestamp"], datetime):
            rc["timestamp"] = rc["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        serializable_records.append(rc)

    return {
        "filename": filename,
        "name": f"Sortie {sport}",
        "sport": sport,
        "start_time": start_str,
        "distance_km": total_dist,
        "d_plus": round(d_plus, 1),
        "d_minus": round(d_minus, 1),
        "duration_min": total_dur_min,
        "avg_hr": avg_hr,
        "max_hr": max_hr,
        "trimp": trimp,
        "rpe": rpe_val,
        "records": serializable_records
    }