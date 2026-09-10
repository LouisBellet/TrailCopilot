from datetime import datetime, timedelta
from core.training_db import get_all_activities, get_user_profile
from core.workload_engine import WorkloadEngine

class CoachEngine:
    @staticmethod
    def get_7day_summary() -> dict:
        activities = get_all_activities()
        now = datetime.now()

        total_duration = 0.0
        total_distance = 0.0
        total_d_plus = 0.0
        total_d_minus = 0.0
        total_trimp = 0.0
        sessions_count = 0
        sports_count = {}

        for a in activities:
            clean_date = str(a["start_time"]).replace("T", " ").split(".")[0].strip()
            try:
                act_date = datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    act_date = datetime.strptime(clean_date, "%Y-%m-%d")
                except ValueError:
                    continue

            if 0 <= (now - act_date).days <= 7:
                sessions_count += 1
                total_duration += float(a.get("duration_min", 0.0))
                total_distance += float(a.get("distance_km", 0.0))
                total_d_plus += float(a.get("d_plus", 0.0))
                total_d_minus += float(a.get("d_minus", 0.0))
                total_trimp += float(a.get("trimp", 0.0))
                
                sp = a.get("sport", "Autre")
                sports_count[sp] = sports_count.get(sp, 0) + 1

        hours = int(total_duration // 60)
        mins = int(total_duration % 60)

        return {
            "sessions_count": sessions_count,
            "duration_str": f"{hours}h{mins:02d}",
            "distance_km": round(total_distance, 1),
            "d_plus": int(total_d_plus),
            "d_minus": int(total_d_minus),
            "total_trimp": round(total_trimp, 1),
            "dominant_sport": max(sports_count, key=sports_count.get) if sports_count else "Aucun"
        }

    @staticmethod
    def generate_daily_advice() -> dict:
        summary = CoachEngine.get_7day_summary()
        readiness = WorkloadEngine.get_athlete_readiness()
        profile = get_user_profile()

        acwr = readiness.get("acwr", 1.0)
        vma = profile.get("vma", 15.0)
        hr_rest = profile.get("hr_rest", 50)
        hr_max = profile.get("hr_max", 185)
        reserve = hr_max - hr_rest

        z2_min = int(hr_rest + reserve * 0.60)
        z2_max = int(hr_rest + reserve * 0.72)
        z4_min = int(hr_rest + reserve * 0.82)
        z4_max = int(hr_rest + reserve * 0.90)

        v_z2 = vma * 0.65
        pace_z2_min = int(60.0 / v_z2)
        pace_z2_sec = int((60.0 / v_z2 - pace_z2_min) * 60)
        pace_z2_str = f"{pace_z2_min}'{pace_z2_sec:02d}\"/km"

        v_seuil = vma * 0.83
        pace_seuil_min = int(60.0 / v_seuil)
        pace_seuil_sec = int((60.0 / v_seuil - pace_seuil_min) * 60)
        pace_seuil_str = f"{pace_seuil_min}'{pace_seuil_sec:02d}\"/km"

        if acwr > 1.35 or summary["d_minus"] > 2500:
            status_text = "Vigilance : Surcharge ou fatigue musculaire résiduelle (D- important)."
            status_color = "#DD6B20"
            rec_badge = "RÉCUPÉRATION / ENDURANCE BASSE"

            opt1 = {
                "title": "Option 1 : Randonnée active ou marche en forêt",
                "tag": "Terrain Naturel",
                "duration": "1h00 à 1h15",
                "target": f"FC basse < {z2_min} bpm",
                "desc": "Marche avec bâtons sur terrain peu accidenté. Zéro course en descente pour préserver les quadriceps. Travail du pied et oxygénation pure."
            }
            opt2 = {
                "title": "Option 2 : Footing léger régénérant",
                "tag": "Plat / Asphalte ou Piste",
                "duration": "40 à 45 min",
                "target": f"Allure {pace_z2_str} | FC < {z2_min} bpm",
                "desc": "Footing très lent sur sol régulier. Relâchement des épaules, foulée rasante sans impact violent. Vous devez pouvoir parler en continu sans forcer."
            }
            opt3 = {
                "title": "Option 3 : Décrassage sans impact (Vélo / Home-Trainer)",
                "tag": "Entraînement Croisé",
                "duration": "50 min",
                "target": "Cadence 90 rpm | Effort très modéré",
                "desc": "Moulinage fluide sur petit braquet. Permet d'évacuer les toxines et de drainer les fibres musculaires sans subir le poids du corps."
            }

        elif acwr < 0.80:
            status_text = "Sous-charge relative : Capacité disponible pour un stimulus de volume."
            status_color = "#3182CE"
            rec_badge = "DÉVELOPPEMENT VOLUME AÉROBIE"

            opt1 = {
                "title": "Option 1 : Rando-Course vallonnée (D+)",
                "tag": "Montagne / Sentier",
                "duration": "1h45 à 2h15",
                "target": f"Montée : {z2_max}-{z4_min} bpm | Descente souple",
                "desc": "Alterner marche active bâtons en main dans les montées raides et trot régulier sur le plat/faux-plat. Accumuler entre 600m et 900m de D+."
            }
            opt2 = {
                "title": "Option 2 : Sortie longue rythmée sur le plat",
                "tag": "Course sur Route",
                "duration": "1h15 à 1h30",
                "target": f"Allure {pace_z2_str} (Z2 constante)",
                "desc": "Séance clé d'endurance fondamentale. Maintenir une cadence stable de 170-180 pas/minute. Optimisation de l'utilisation des graisses (lipolyse)."
            }
            opt3 = {
                "title": "Option 3 : Sortie longue Vélo ou Ski de Randonnée",
                "tag": "Endurance Longue Croisée",
                "duration": "2h30 à 3h00",
                "target": f"FC entre {z2_min} et {z2_max} bpm",
                "desc": "Excellente construction de socle cardiovasculaire sans casse articulaire. En ski de rando : montée à allure conversationnelle continue."
            }

        else:
            status_text = "Charge optimale : Fenêtre parfaite pour le travail de puissance et de dénivelé."
            status_color = "#38A169"
            rec_badge = "SÉANCE QUALITÉ & DÉNIVELÉ"

            opt1 = {
                "title": "Option 1 : Fractionné en côte spécifique Trail",
                "tag": "Pente 8 à 15%",
                "duration": "1h10 (Échauffement + Corps + Retour au calme)",
                "target": f"Effort : 85-92% FC Max ({z4_min}-{z4_max} bpm)",
                "desc": "20 min d'échauffement + 8 à 10 répétitions de 1 min dynamique en montée raide (récupération en descente trottée) + 15 min de footing calme."
            }
            opt2 = {
                "title": "Option 2 : Séance de train au Seuil sur le plat",
                "tag": "Route / Piste",
                "duration": "1h00",
                "target": f"Allure cible {pace_seuil_str}",
                "desc": "20 min échauffement + 3 x 8 min à allure semi-marathon / seuil (récupération 2 min trot lent) + 10 min régénération. Développe la cylindrée aérobie."
            }
            opt3 = {
                "title": "Option 3 : PPG Spécifique Montagne + Home-Trainer",
                "tag": "Maison / Salle de sport",
                "duration": "1h00",
                "target": "Renforcement musculaire excentrique",
                "desc": "30 min de circuit bas du corps (fentes sautées, chaise isométrique 4x45s, montées de banc, gainage gaine ventrale) suivi de 30 min de vélo Z2 pour délier."
            }

        return {
            "status_text": status_text,
            "status_color": status_color,
            "badge": rec_badge,
            "options": [opt1, opt2, opt3]
        }