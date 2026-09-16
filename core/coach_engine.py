from datetime import datetime, timedelta

def parse_date_only(date_str: str):
    clean = str(date_str).replace("T", " ").split(".")[0].strip()[:10]
    return datetime.strptime(clean, "%Y-%m-%d").date()

class CoachEngine:
    @staticmethod
    def compute_7day_summary(activities: list) -> dict:
        today = datetime.now().date()
        t_dur, t_dist, t_dp, t_dm, t_trimp, count = 0.0, 0.0, 0.0, 0.0, 0.0, 0

        for a in activities:
            try:
                act_date = parse_date_only(a["start_time"])
            except Exception:
                continue

            if 0 <= (today - act_date).days <= 6:
                count += 1
                t_dur += float(a.get("duration_min", 0.0))
                t_dist += float(a.get("distance_km", 0.0))
                t_dp += float(a.get("d_plus", 0.0))
                t_dm += float(a.get("d_minus", 0.0))
                t_trimp += float(a.get("trimp", 0.0))

        h = int(t_dur // 60)
        m = int(t_dur % 60)
        return {
            "sessions_count": count, "duration_str": f"{h}h{m:02d}",
            "distance_km": round(t_dist, 1), "d_plus": int(t_dp),
            "d_minus": int(t_dm), "total_trimp": round(t_trimp, 1)
        }

    @staticmethod
    def project_ewma_acwr(load_trimp: float, ewma_a: float, ewma_c: float) -> float:
        l_a = 2.0 / 8.0
        l_c = 2.0 / 29.0
        next_a = (load_trimp * l_a + (1.0 - l_a) * ewma_a) * 7.0
        next_c = (load_trimp * l_c + (1.0 - l_c) * ewma_c) * 7.0
        if next_c < 3.0:
            return 0.0 if next_a < 3.0 else min(2.5, round(next_a / 8.0, 2))
        return round(next_a / next_c, 2)

    @staticmethod
    def compute_daily_advice(activities: list, profile: dict, cur_acwr: float) -> dict:
        today = datetime.now().date()
        daily_map = {}
        for a in activities:
            d = parse_date_only(a["start_time"])
            daily_map[d] = daily_map.get(d, 0.0) + float(a.get("trimp", 0.0))

        l_a = 2.0 / 8.0
        l_c = 2.0 / 29.0
        curr_date = today - timedelta(days=60)
        ewma_a = 0.0
        ewma_c = 0.0

        while curr_date <= today:
            load = daily_map.get(curr_date, 0.0)
            ewma_a = load * l_a + (1.0 - l_a) * ewma_a
            ewma_c = load * l_c + (1.0 - l_c) * ewma_c
            curr_date += timedelta(days=1)

        # Calcul analytique du budget TRIMP pour viser ACWR = 1.05 demain
        target_acwr = 1.05
        num = target_acwr * (1.0 - l_c) * ewma_c - (1.0 - l_a) * ewma_a
        denom = l_a - target_acwr * l_c
        ideal_trimp = max(0.0, round(num / denom, 1)) if denom > 0 else 25.0

        vma = profile.get("vma", 15.0)
        hr_rest = profile.get("hr_rest", 50)
        hr_max = profile.get("hr_max", 185)
        res = hr_max - hr_rest

        z2_bpm = f"{int(hr_rest + res * 0.60)}-{int(hr_rest + res * 0.70)} bpm"
        z4_bpm = f"{int(hr_rest + res * 0.82)}-{int(hr_rest + res * 0.90)} bpm"
        pace_z2 = f"{int(60.0/(vma*0.65))}'{int(((60.0/(vma*0.65))%1)*60):02d}\"/km"

        if cur_acwr > 1.35:
            badge = "SURCHARGE — RÉDUCTION DE FATIGUE CIBLÉE"
            status_text = f"ACWR élevé ({cur_acwr}). Laisser la fatigue chuter naturellement vers 1.10."
            status_color = "#E53E3E"
            t1, t2, t3 = 15.0, 25.0, 0.0

            opt1 = {
                "title": "Option 1 : Protocole Décompression & Yoga Restauratif",
                "tag": "Mobilité & Récupération",
                "trimp": t1,
                "proj_acwr": CoachEngine.project_ewma_acwr(t1, ewma_a, ewma_c),
                "timing": "Créneau : Soirée (19h00 - 20h30)",
                "recovery_time": "12 h",
                "program": [
                    "Posture de l'Enfant (Balasana) : 3 séries de 1 min 30 s respiration diaphragmatique",
                    "Chien tête en bas doux : 4 x 45 s avec alternance talons au sol",
                    "Étirement chaîne postérieure à la sangle : 2 min par côté",
                    "Surélévation des jambes au mur (Viparita Karani) : 10 min complètes"
                ],
                "tactical_note": "Zéro contrainte excentrique. Accélère la baisse de l'ACWR."
            }
            opt2 = {
                "title": "Option 2 : Décrassage doux sur Home-Trainer ou Vélo plat",
                "tag": "Drainage Actif",
                "trimp": t2,
                "proj_acwr": CoachEngine.project_ewma_acwr(t2, ewma_a, ewma_c),
                "timing": "Créneau : Fin d'après-midi (17h00 - 18h00)",
                "recovery_time": "18 h",
                "program": [
                    "35 min de moulinage très fluide (cadence 90-95 rpm)",
                    "Intensité Z1 stricte (FC < 60% FC Max)",
                    "10 min d'automassage au rouleau (mollets et quadriceps)"
                ],
                "tactical_note": "Hydratation alcaline pour tamponner l'acidité musculaire."
            }
            opt3 = {
                "title": "Option 3 : Repos Complet & Sommeil Restaurateur",
                "tag": "Régénération Totale",
                "trimp": t3,
                "proj_acwr": CoachEngine.project_ewma_acwr(t3, ewma_a, ewma_c),
                "timing": "Journée complète de repos",
                "recovery_time": "Prêt pour demain matin",
                "program": [
                    "Aucune activité sportive programmée",
                    "Hydratation régulière (2 litres d'eau)",
                    "Objectif 8h30 de sommeil réparateur"
                ],
                "tactical_note": "Permet à l'ACWR de glisser vers la zone optimale dès demain."
            }
        elif cur_acwr < 0.85:
            badge = "STIMULATION DE CHARGE — PROGRESSION POSITIVE"
            status_text = f"Sous-charge ({cur_acwr}). Pour relancer la condition physique, un apport de ~{ideal_trimp} TRIMP est idéal."
            status_color = "#3182CE"
            t1 = max(60.0, round(ideal_trimp * 1.15, 1))
            t2 = max(45.0, round(ideal_trimp, 1))
            t3 = max(25.0, round(ideal_trimp * 0.65, 1))

            opt1 = {
                "title": "Option 1 : Rando-Course avec Dénivelé Trail (D+)",
                "tag": "Montagne & Pentes",
                "trimp": t1,
                "proj_acwr": CoachEngine.project_ewma_acwr(t1, ewma_a, ewma_c),
                "timing": "Créneau : Matinée ou début d'après-midi",
                "recovery_time": "36 h",
                "program": [
                    "1h30 à 2h00 sur sentier technique (+500m à +800m D+)",
                    "Montée : marche active bâtons en main (FC : " + z2_bpm + ")",
                    "Descentes : foulée souple sans prise de risque",
                    "10 min d'étirements doux au retour"
                ],
                "tactical_note": "Prendre 500 ml d'eau avec électrolytes."
            }
            opt2 = {
                "title": "Option 2 : Sortie Longue Aérobie sur Route / Plat",
                "tag": "Endurance Fondamentale",
                "trimp": t2,
                "proj_acwr": CoachEngine.project_ewma_acwr(t2, ewma_a, ewma_c),
                "timing": "Créneau : Matin (09h00 - 11h00)",
                "recovery_time": "24 h",
                "program": [
                    "15 min d'échauffement progressif",
                    "50 min en endurance fondamentale calée à l'allure cible (" + pace_z2 + ")",
                    "5 lignes droites de 80 m en accélération progressive",
                    "5 min de marche de retour au calme"
                ],
                "tactical_note": "Foulée médio-pied économique et relâchée."
            }
            opt3 = {
                "title": "Option 3 : Sortie Endurance Croisée Vélo / Ski de Rando",
                "tag": "Volume Sans Choc",
                "trimp": t3,
                "proj_acwr": CoachEngine.project_ewma_acwr(t3, ewma_a, ewma_c),
                "timing": "Créneau : Après-midi (14h00 - 16h30)",
                "recovery_time": "24 h",
                "program": [
                    "2h00 en aisance respiratoire continue (Z1/Z2)",
                    "En ski de rando : rythme cardiaque stable et conversions fluides",
                    "15 min de gainage abdominal au retour"
                ],
                "tactical_note": "Développe le cardio sans impacter les tendons d'Achille."
            }
        else:
            badge = "SWEET SPOT — TRAVAIL QUALITATIF & DÉVELOPPEMENT"
            status_text = f"Progression optimale ({cur_acwr}). Dose préconisée aujourd'hui : ~{ideal_trimp} TRIMP."
            status_color = "#38A169"
            t1 = max(55.0, round(ideal_trimp * 1.10, 1))
            t2 = max(40.0, round(ideal_trimp * 0.90, 1))
            t3 = max(20.0, round(ideal_trimp * 0.50, 1))

            opt1 = {
                "title": "Option 1 : Répétitions en Côte Spécifiques Trail",
                "tag": "Puissance & VMA en Côte",
                "trimp": t1,
                "proj_acwr": CoachEngine.project_ewma_acwr(t1, ewma_a, ewma_c),
                "timing": "Créneau : Après-midi (16h00 - 17h30)",
                "recovery_time": "48 h",
                "program": [
                    "20 min footing d'échauffement à plat",
                    "Éducatifs : montées de genoux et griffés",
                    "Corps de séance : 8 répétitions de 1 min dynamique en côte (pente 8-12%)",
                    "Intensité sommet : FC " + z4_bpm + " (Borg 16-17)",
                    "Descente lente en trot/marche pour récupérer",
                    "10 min footing très lent de retour au calme"
                ],
                "tactical_note": "Buste gainé, regard vers le haut de la pente."
            }
            opt2 = {
                "title": "Option 2 (Combiné Midi + Soir) : Allure Tempo PUIS Yoga Récupération",
                "tag": "Séance Clé + Récupération",
                "trimp": t2,
                "proj_acwr": CoachEngine.project_ewma_acwr(t2, ewma_a, ewma_c),
                "timing": "Séance 1 : 12h30 (Course 45 min) | Séance 2 : 20h30 (Yoga 20 min)",
                "recovery_time": "36 h",
                "program": [
                    "Séance 1 (12h30) : 15 min échauffement + 3 x 7 min tempo dynamique + 5 min calme",
                    "Séance 2 (20h30) : 20 min de postures au sol pour étirer fessiers, ischios et mollets"
                ],
                "tactical_note": "Apporte le stimulus cardio tout en facilitant le sommeil."
            }
            opt3 = {
                "title": "Option 3 : Circuit PPG Trail + Isométrie Quadriceps",
                "tag": "Renforcement Excentrique D-",
                "trimp": t3,
                "proj_acwr": CoachEngine.project_ewma_acwr(t3, ewma_a, ewma_c),
                "timing": "Créneau : Matin ou fin d'après-midi",
                "recovery_time": "24 h",
                "program": [
                    "4 tours complets (1 min 30 s de repos entre les séries) :",
                    "• Chaise dos au mur : 45 secondes maintien strict",
                    "• Fentes avant ralenties (descente en 3 s) : 10 par jambe",
                    "• Montées sur pointes de pieds : 20 répétitions",
                    "• Planche ventrale gainage actif : 1 minute",
                    "15 min de décrassage sur vélo sans résistance"
                ],
                "tactical_note": "Renforce la résistance des quadriceps pour les longues descentes."
            }

        projections = [
            {"label": "Opt 1", "trimp": opt1["trimp"], "projected_acwr": opt1["proj_acwr"], "color": "#F6AD55"},
            {"label": "Opt 2", "trimp": opt2["trimp"], "projected_acwr": opt2["proj_acwr"], "color": "#38B2AC"},
            {"label": "Opt 3", "trimp": opt3["trimp"], "projected_acwr": opt3["proj_acwr"], "color": "#63B3ED"}
        ]

        return {
            "badge": badge,
            "status_text": status_text,
            "status_color": status_color,
            "target_budget": ideal_trimp,
            "options": [opt1, opt2, opt3],
            "projections": projections
        }