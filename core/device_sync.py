import os
import psutil
from core.fit_parser import parse_fit_file
from core.training_db import save_activity, get_all_activities

# Arborescences types des activités selon la marque
WATCH_DIRECTORIES = {
    "Garmin": [
        os.path.join("GARMIN", "ACTIVITY"),
        os.path.join("Garmin", "Activity"),
        os.path.join("garmin", "activity")
    ],
    "Coros": [
        "Activities",
        "activities",
        os.path.join("COROS", "Activities"),
        os.path.join("Coros", "Activities"),
        os.path.join("data", "activities")
    ]
}

def scan_connected_watches() -> dict:
    """
    Scanne tous les volumes montés pour détecter une montre Garmin ou Coros.
    Importe automatiquement les fichiers .fit non encore enregistrés en base.
    
    Retourne :
      {"brand": "Garmin" | "Coros" | None, "imported": int, "skipped": int}
    """
    existing_filenames = {a["filename"] for a in get_all_activities()}
    imported_count = 0
    skipped_count = 0
    detected_brand = None

    try:
        partitions = psutil.disk_partitions(all=False)
    except Exception as e:
        print(f"[DeviceSync] Impossible d'énumérer les partitions : {e}")
        return {"brand": None, "imported": 0, "skipped": 0}

    for part in partitions:
        mount = part.mountpoint

        for brand, subpaths in WATCH_DIRECTORIES.items():
            for sp in subpaths:
                candidate_dir = os.path.join(mount, sp)
                if os.path.exists(candidate_dir) and os.path.isdir(candidate_dir):
                    detected_brand = brand
                    try:
                        files = os.listdir(candidate_dir)
                    except Exception as e:
                        print(f"[DeviceSync] Erreur d'accès au dossier {candidate_dir} : {e}")
                        continue

                    for file in files:
                        if file.upper().endswith(".FIT"):
                            if file in existing_filenames:
                                skipped_count += 1
                                continue

                            full_path = os.path.join(candidate_dir, file)
                            try:
                                data = parse_fit_file(full_path)
                                if save_activity(data):
                                    existing_filenames.add(file)
                                    imported_count += 1
                            except Exception as e:
                                print(f"[DeviceSync Error] Échec de lecture pour {file} : {e}")

    return {
        "brand": detected_brand,
        "imported": imported_count,
        "skipped": skipped_count
    }