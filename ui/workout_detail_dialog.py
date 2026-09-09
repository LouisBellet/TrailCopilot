from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QGroupBox
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from core.training_db import get_user_profile

class WorkoutDetailDialog(QDialog):
    def __init__(self, act_data: dict, parent=None):
        super().__init__(parent)
        self.act = act_data
        self.profile = get_user_profile()
        self.setWindowTitle(f"Détail de la Séance — {self.act.get('name', 'Activité')}")
        self.resize(850, 600)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        grp_stats = QGroupBox("Indicateurs Clés & Performance")
        grid = QGridLayout(grp_stats)
        
        weight = self.profile.get("weight_kg", 70.0)
        dist = self.act.get("distance_km", 0.0)
        dur = self.act.get("duration_min", 0.0)
        dp = self.act.get("d_plus", 0.0)
        dm = self.act.get("d_minus", 0.0)
        avg_hr = self.act.get("avg_hr", 0)
        trimp = self.act.get("trimp", 0.0)
        
        speed_kmh = round((dist / (dur / 60.0)), 2) if dur > 0 else 0.0
        vam_mh = round((dp / (dur / 60.0)), 0) if dur > 0 else 0.0
        calories = int(dur * (avg_hr / 140.0) * 10.5) if avg_hr > 0 else int(dist * weight * 1.05 + dp * 0.1)

        grid.addWidget(QLabel(f"<b>Date :</b> {self.act.get('start_time', '')[:10]}"), 0, 0)
        grid.addWidget(QLabel(f"<b>Discipline :</b> {self.act.get('sport', '')}"), 0, 1)
        grid.addWidget(QLabel(f"<b>Durée :</b> {dur} min"), 0, 2)
        grid.addWidget(QLabel(f"<b>Distance :</b> {dist} km"), 0, 3)

        grid.addWidget(QLabel(f"<b>Dénivelé + :</b> +{int(dp)} m"), 1, 0)
        grid.addWidget(QLabel(f"<b>Dénivelé - :</b> -{int(dm)} m"), 1, 1)
        grid.addWidget(QLabel(f"<b>Vitesse Moy :</b> {speed_kmh} km/h"), 1, 2)
        grid.addWidget(QLabel(f"<b>VAM :</b> {int(vam_mh)} m/h"), 1, 3)

        grid.addWidget(QLabel(f"<b>FC Moyenne :</b> {avg_hr} bpm"), 2, 0)
        grid.addWidget(QLabel(f"<b>FC Max :</b> {self.act.get('max_hr', 0)} bpm"), 2, 1)
        grid.addWidget(QLabel(f"<b>Charge TRIMP :</b> <span style='color:#38B2AC;'><b>{trimp}</b></span>"), 2, 2)
        grid.addWidget(QLabel(f"<b>Énergie estimée :</b> ~{calories} kcal"), 2, 3)

        layout.addWidget(grp_stats)

        records = self.act.get("records", [])
        if records:
            self.fig = Figure(figsize=(8, 3.8), facecolor="#1F242D")
            self.canvas = FigureCanvas(self.fig)
            self.ax_alt = self.fig.add_subplot(111)
            self.ax_hr = self.ax_alt.twinx()
            self.ax_alt.set_facecolor("#16191E")

            distances, alts, hrs = [], [], []
            last_d = 0.0
            for r in records:
                d = r.get("distance_km")
                if d is not None:
                    last_d = d
                distances.append(last_d)
                alts.append(r.get("alt"))
                hrs.append(r.get("hr"))

            valid_alts = [a for a in alts if a is not None]
            if valid_alts:
                clean_alts = [a if a is not None else min(valid_alts) for a in alts]
                self.ax_alt.plot(distances, clean_alts, color="#38B2AC", linewidth=2.0, label="Altitude (m)")
                self.ax_alt.fill_between(distances, clean_alts, min(valid_alts) - 20, color="#38B2AC", alpha=0.25)
                self.ax_alt.set_ylabel("Altitude (m)", color="#38B2AC")
                self.ax_alt.set_ylim(bottom=max(0, min(valid_alts) - 40))

            valid_hrs = [h for h in hrs if h is not None]
            if valid_hrs:
                clean_hrs = [h if h is not None else min(valid_hrs) for h in hrs]
                self.ax_hr.plot(distances, clean_hrs, color="#FC8181", linewidth=1.5, linestyle="--", label="FC (bpm)")
                self.ax_hr.set_ylabel("FC (bpm)", color="#FC8181")
                self.ax_hr.set_ylim(bottom=max(40, min(valid_hrs) - 10), top=max(valid_hrs) + 15)

            self.ax_alt.set_xlabel("Distance (km)", color="#CBD5E0")
            self.ax_alt.tick_params(colors="#CBD5E0")
            self.ax_hr.tick_params(colors="#CBD5E0")
            self.ax_alt.grid(True, linestyle=":", alpha=0.3, color="#718096")
            for spine in self.ax_alt.spines.values():
                spine.set_color("#2D3748")
            for spine in self.ax_hr.spines.values():
                spine.set_color("#2D3748")

            self.fig.tight_layout()
            layout.addWidget(self.canvas)
        else:
            no_rec_box = QGroupBox("Données de Tracé")
            nb_layout = QVBoxLayout(no_rec_box)
            nb_layout.addWidget(QLabel("<span style='color:#A0AEC0;'>Séance saisie manuellement ou sans points GPS/Cardio détaillés seconde par seconde.</span>"))
            layout.addWidget(no_rec_box)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_close = QPushButton("Fermer")
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)