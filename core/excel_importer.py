import os
from datetime import datetime
import openpyxl
from core.fit_parser import calculate_banister_trimp
from core.training_db import save_activity, get_user_profile, get_all_activities

def import_workouts_from_excel(file_path: str) -> dict:
    """
    Importe les séances depuis le template Excel (onglet Journal_Entrainements).
    Sauvegarde directement chaque sortie dans SQLite user_data.db.
    """
    if not os.path.exists(file_path):
        return {"imported": 0, "skipped": 0, "error": "Fichier introuvable"}

    profile = get_user_profile()
    hr_rest = profile["hr_rest"]
    hr_max = profile["hr_max"]

    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb["Journal_Entrainements"] if "Journal_Entrainements" in wb.sheetnames else wb.active

    existing_filenames = {a["filename"] for a in get_all_activities()}
    imported_count = 0
    skipped_count = 0

    # Les données commencent à la ligne 5
    for row_idx in range(5, ws.max_row + 1):
        date_raw = ws.cell(row=row_idx, column=1).value
        sport_raw = ws.cell(row=row_idx, column=2).value
        title_raw = ws.cell(row=row_idx, column=3).value
        duration_raw = ws.cell(row=row_idx, column=4).value

        # Fin des données si date ou durée vide
        if not date_raw or not duration_raw:
            continue

        # Formatage date
        if isinstance(date_raw, (datetime,)):
            date_str = date_raw.strftime("%Y-%m-%d 10:00:00")
            day_key = date_raw.strftime("%Y%m%d")
        else:
            clean_d = str(date_raw).strip()[:10]
            date_str = f"{clean_d} 10:00:00"
            day_key = clean_d.replace("-", "")

        # Identifiant unique pérenne pour SQLite
        synth_filename = f"manual_excel_{day_key}_{row_idx}.fit"
        if synth_filename in existing_filenames:
            skipped_count += 1
            continue

        sport = str(sport_raw).strip() if sport_raw else "Trail"
        title = str(title_raw).strip() if title_raw else f"Séance {sport}"
        duration_min = float(duration_raw)
        distance_km = float(ws.cell(row=row_idx, column=5).value or 0.0)
        d_plus = float(ws.cell(row=row_idx, column=6).value or 0.0)
        d_minus = float(ws.cell(row=row_idx, column=7).value or d_plus)
        avg_hr = int(ws.cell(row=row_idx, column=8).value or 0)
        max_hr = int(ws.cell(row=row_idx, column=9).value or (avg_hr + 15 if avg_hr > 0 else 0))
        rpe = float(ws.cell(row=row_idx, column=10).value or 5.0)

        # Calcul de charge : Banister si cardio dispo, sinon Session-RPE de Foster
        if avg_hr > hr_rest:
            trimp = calculate_banister_trimp(duration_min, avg_hr, hr_rest, hr_max)
        else:
            trimp = round(duration_min * (rpe / 10.0) * 1.5, 1)

        act_data = {
            "filename": synth_filename,
            "name": title,
            "sport": sport,
            "start_time": date_str,
            "distance_km": distance_km,
            "d_plus": d_plus,
            "d_minus": d_minus,
            "duration_min": duration_min,
            "avg_hr": avg_hr,
            "max_hr": max_hr,
            "trimp": trimp,
            "records": []  # Pas de trace point par point pour une saisie manuelle
        }

        if save_activity(act_data):
            existing_filenames.add(synth_filename)
            imported_count += 1

    return {"imported": imported_count, "skipped": skipped_count, "error": None}