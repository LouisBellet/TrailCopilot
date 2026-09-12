from datetime import datetime
from core.training_db import get_all_activities, get_user_profile
from core.workload_engine import WorkloadEngine

class CoachEngine:
    @staticmethod
    def get_7day_summary() -> dict:
        activities = get_all_activities()
        today = datetime.now().date()

        t_dur, t_dist, t_dp, t_dm, t_trimp, count = 0.0, 0.0, 0.0, 0.0, 0.0, 0
        for a in activities:
            clean = str(a["start_time"]).replace("T", " ").split(".")[0].strip()
            try:
                act_date = datetime.strptime(clean, "%Y-%m-%d %H:%M:%S").date()
            except ValueError:
                try:
                    act_date = datetime.strptime(clean, "%Y-%m-%d").date()
                except ValueError:
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
    def generate_daily_advice() -> dict:
        readiness = WorkloadEngine.get_athlete_readiness()
        profile = get_user_profile()

        acwr = readiness.get("acwr", 1.0)
        risk = readiness.get("injury_risk_pct", 3.3)
        vma = profile.get("vma", 15.0)
        hr_rest = profile.get("hr_rest", 50)
        hr_max = profile.get("hr_max", 185)
        res = hr_max - hr_rest

        z2_bpm = f"{int(hr_rest + res * 0.60)}-{int(hr_rest + res * 0.70)} bpm"
        z4_bpm = f"{int(hr_rest + res * 0.82)}-{int(hr_rest + res * 0.90)} bpm"
        pace_z2 = f"{int(60.0/(vma*0.65))}'{int(((60.0/(vma*0.65))%1)*60):02d}\"/km"

        if acwr > 1.35 or risk > 6.0:
            badge = "RÉCUPÉRATION & RÉGÉNÉRATION TISSULAIRE"
            status_text = f"Surcharge détectée (ACWR: {acwr} | Risque blessure: {risk}%). Priorité au relâchement musculaire."
            status_color = "#E53E3E"

            opt1 = {
                "title": "Option 1 : Protocole Yoga Restauratif & Décompression Lombaire",
                "tag": "Récupération Active / Passive",
                "timing": "Créneau conseillé : Soir avant le coucher (19h00 - 21h00)",
                "recovery_time": "12 h à 18 h avant la prochaine séance",
                "program": [
                    "Posture de l'Enfant (Balasana) : 3 séries de 1 min 30 s (respiration ventrale lente)",
                    "Chien tête en bas doux (Adho Mukha) : 4 x 45 s avec pédalage doux des talons",
                    "Torsion vertébrale au sol (Supta Matsyendrasana) : 2 min par côté",
                    "Jambes surélevées contre le mur (Viparita Karani) : 8 min complètes"
                ],
                "tactical_note": "Hydratation alcaline (eau riche en bicarbonates), aucun impact excentrique."
            }
            opt2 = {
                "title": "Option 2 : Routine Réveil Articulaire + Étirements Ischio-Jambiers/Psoas",
                "tag": "Mobilité & Souplesse",
                "timing": "Créneau conseillé : Matin (8h00 - 9h30)",
                "recovery_time": "12 h",
                "program": [
                    "Cercles articulaires chevilles et hanches : 2 x 15 rotations lentes par sens",
                    "Étirement actif du Psoas (fente basse au sol avec rétroversion du bassin) : 3 x 45 s / côté",
                    "Étirement chaînes postérieures (avec sangle ou élastique sur le dos) : 3 x 1 min / jambe",
                    "Foam Roller (automassage mollets et bandelette ilio-tibiale) : 2 min par groupe musculaire"
                ],
                "tactical_note": "Ne jamais forcer jusqu'à la douleur aiguë. Travaillez sur l'expiration."
            }
            opt3 = {
                "title": "Option 3 : Décrassage doux Vélo sans résistance",
                "tag": "Drainage Métabolique",
                "timing": "Créneau conseillé : Milieu de journée (12h30 ou 16h00)",
                "recovery_time": "18 h",
                "program": [
                    "35 à 45 min de home-trainer ou vélo de route à plat",
                    "Cadence constante de 90-95 rpm, FC strictement inférieure à 60% FC Max",
                    "5 min de marche pieds nus sur herbe pour la proprioception plantaire"
                ],
                "tactical_note": "Consommer 500 ml d'eau avec électrolytes pendant la séance."
            }

        elif acwr < 0.80:
            badge = "DÉVELOPPEMENT & STIMULATION DE VOLUME"
            status_text = f"Sous-charge relative (ACWR: {acwr} | Risque blessure: {risk}%). Fenêtre ouverte pour augmenter le volume aérobie."
            status_color = "#3182CE"

            opt1 = {
                "title": "Option 1 (Combiné Matin + Soir) : Réveil Articulaire PUIS Sortie Trail Longue",
                "tag": "Double Séance Combinée",
                "timing": "Séance 1 : 08h00 (Mobilité 15 min) | Séance 2 : 14h30 (Trail 2h00)",
                "recovery_time": "36 h à 48 h de récupération avant un nouvel effort intense",
                "program": [
                    "Séance 1 (08h00) : Réveil articulaire cheville/bassin + 10 min de gainage abdominal dynamique",
                    "Séance 2 (14h30) : 1h45 à 2h15 en terrain montagnard (+600m à +900m D+)",
                    "Intensité cible : Z2 continue en montée active aux bâtons (FC: " + z2_bpm + ")",
                    "Descente progressive sans survitesse pour réadapter les fibres musculaires"
                ],
                "tactical_note": "Prévoyez 40 g de glucides par heure d'effort en montagne et 600 ml d'eau/h."
            }
            opt2 = {
                "title": "Option 2 : Sortie Route Fondamentale avec variations d'allure",
                "tag": "Course sur Route",
                "timing": "Créneau conseillé : Fin de matinée (10h00 - 11h30)",
                "recovery_time": "24 h",
                "program": [
                    "15 min échauffement Z1 progressif",
                    "50 min en endurance fondamentale stable (allure cible: " + pace_z2 + ")",
                    "5 x 100m en lignes droites accélérées (foulée relâchée, récupération retour marché)",
                    "10 min retour au calme"
                ],
                "tactical_note": "Excellente séance pour renforcer le réseau capillaire et la lipolyse."
            }
            opt3 = {
                "title": "Option 3 : Sortie longue Vélo de Route ou Ski de Randonnée",
                "tag": "Socle Cardiaque Sans Choc",
                "timing": "Créneau conseillé : Matinée complète (09h00 - 12h00)",
                "recovery_time": "24 h à 36 h",
                "program": [
                    "2h30 à 3h15 d'endurance continue à 65-72% FC Max",
                    "En ski de rando : montée fluide sans à-coups, conversions propres et travail des appuis",
                    "15 min d'étirements doux des quadriceps et fessiers au retour"
                ],
                "tactical_note": "Permet d'accumuler du temps de soutien aérobie sans fatigue mécanique ostéo-articulaire."
            }

        else:
            badge = "ZONE OPTIMALE — TRAVAIL DE QUALITÉ & DÉNIVELÉ"
            status_text = f"Sweet Spot atteint (ACWR: {acwr} | Risque blessure: {risk}%). Fenêtre idéale pour progresser."
            status_color = "#38A169"

            opt1 = {
                "title": "Option 1 : Fractionné en Côte Spécifique Montagne / Trail",
                "tag": "Puissance Aérobie en Côte",
                "timing": "Créneau conseillé : Après-midi (15h30 - 17h00)",
                "recovery_time": "48 h avant une autre séance de seuil ou de D+",
                "program": [
                    "20 min échauffement en endurance douce à plat",
                    "Éducatifs de pied : 2 x 30 m montées de genoux + talons-fesses",
                    "Corps de séance : 8 à 10 répétitions de 1 min 15 s dynamique en côte (pente 8-12%)",
                    "Cible cardiaque au sommet des réps : " + z4_bpm,
                    "Récupération : descente en marchant/trottant lentement",
                    "10 min de footing de régénération à plat"
                ],
                "tactical_note": "Gardez le buste droit et le regard vers l'avant dans la côte. Ne cherchez pas à allonger la foulée."
            }
            opt2 = {
                "title": "Option 2 (Combiné Midi + Soir) : Allure Seuil Course PUIS Yoga Récupération",
                "tag": "Séance Clé + Récupération Soir",
                "timing": "Séance 1 : 12h30 (Course au Seuil) | Séance 2 : 20h00 (Yoga 25 min)",
                "recovery_time": "36 h",
                "program": [
                    "Séance 1 (12h30) : 15 min échauffement + 3 x 8 min à allure Seuil 1 (récupération 2 min trot lent) + 10 min calme",
                    "Séance 2 (20h00) : 25 min de Yoga Vinyasa doux centré sur l'ouverture de hanches et les mollets",
                    "3 séries de 45 s de pigeon pose (Eka Pada Rajakapotasana) par côté"
                ],
                "tactical_note": "La séance de yoga le soir même réduit les courbatures du lendemain de 40%."
            }
            opt3 = {
                "title": "Option 3 : Circuit PPG Montagne (Isométrie & Excentrique)",
                "tag": "Prévention Casse Musculaire D-",
                "timing": "Créneau conseillé : Matin ou début de soirée",
                "recovery_time": "24 h à 36 h",
                "program": [
                    "4 tours de circuit (1 min 30 s de repos entre les tours) :",
                    "• Chaise dos au mur : 45 s maintien isométrique strict",
                    "• Fentes avant ralenties (descente en 3 secondes) : 12 répétitions par jambe",
                    "• Montées sur pointes de pieds sur marche d'escalier : 20 répétitions",
                    "• Gainage ventral planche active : 1 min",
                    "20 min de home-trainer ou footing très lent pour évacuer les tensions"
                ],
                "tactical_note": "Ce travail renforce la résistance des tendons rotuliens et des quadriceps pour les descentes de trail."
            }

        return {
            "badge": badge, "status_text": status_text,
            "status_color": status_color, "options": [opt1, opt2, opt3]
        }