from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QFrame, QGridLayout
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from core.workload_engine import WorkloadEngine
from core.coach_engine import CoachEngine

class HomeView(QWidget):
    open_training_requested = Signal()
    open_coach_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(12)

        self.days = []
        self.dists = []
        self.durs = []

        self._init_stat_cards()
        self._init_charts()
        self.refresh_dashboard()

    def _init_stat_cards(self):
        grp_kpi = QGroupBox("Indicateurs Physiques Actualisés & Statut de Charge")
        grid = QGridLayout(grp_kpi)
        grid.setSpacing(10)

        self.card_acwr = self._create_kpi_card("RATIO ACWR", "--", "#38A169")
        self.card_risk = self._create_kpi_card("RISQUE BLESSURE", "-- %", "#38A169")
        self.card_acute = self._create_kpi_card("CHARGE AIGUË (7J)", "--", "#E2E8F0")
        self.card_chronic = self._create_kpi_card("CHARGE CHRONIQUE (28J)", "--", "#E2E8F0")
        self.card_vol = self._create_kpi_card("VOLUME 7J", "-- km", "#4FD1C5")
        self.card_dplus = self._create_kpi_card("DÉNIVELÉ 7J", "+-- m / --- m", "#F6AD55")

        grid.addWidget(self.card_acwr["frame"], 0, 0)
        grid.addWidget(self.card_risk["frame"], 0, 1)
        grid.addWidget(self.card_acute["frame"], 0, 2)
        grid.addWidget(self.card_chronic["frame"], 0, 3)
        grid.addWidget(self.card_vol["frame"], 0, 4)
        grid.addWidget(self.card_dplus["frame"], 0, 5)

        self.lbl_status_banner = QLabel("Initialisation de l'état physique...")
        self.lbl_status_banner.setStyleSheet(
            "background:#2D3748; color:white; padding:8px 12px; border-radius:4px; font-weight:bold; font-size:13px;"
        )
        grid.addWidget(self.lbl_status_banner, 1, 0, 1, 6)

        self.layout.addWidget(grp_kpi)

    def _create_kpi_card(self, title: str, default_val: str, color_hex: str) -> dict:
        frame = QFrame()
        frame.setStyleSheet("background-color: #1F242D; border: 1px solid #2D3748; border-radius: 6px; padding: 6px;")
        v = QVBoxLayout(frame)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 10px; font-weight: bold; color: #A0AEC0;")
        lbl_v = QLabel(default_val)
        lbl_v.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color_hex};")

        v.addWidget(lbl_t)
        v.addWidget(lbl_v)
        return {"frame": frame, "val": lbl_v, "title": lbl_t}

    def _init_charts(self):
        grp_charts = QGroupBox("Dynamique Quotidienne des 14 Derniers Jours (Distance & Temps)")
        v = QVBoxLayout(grp_charts)

        self.fig = Figure(figsize=(10, 3.4), facecolor="#1F242D")
        self.canvas = FigureCanvas(self.fig)
        self.ax_dist = self.fig.add_subplot(121)
        self.ax_dur = self.fig.add_subplot(122)

        self.annot_dist = self._create_annot(self.ax_dist)
        self.annot_dur = self._create_annot(self.ax_dur)

        self.canvas.mpl_connect("motion_notify_event", self._on_hover)

        v.addWidget(self.canvas)
        self.layout.addWidget(grp_charts)

    def _create_annot(self, ax):
        annot = ax.annotate(
            "", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="#1F242D", ec="#38B2AC", lw=1.5),
            color="#FFFFFF", fontsize=8, fontweight="bold", zorder=10
        )
        annot.set_visible(False)
        return annot

    def refresh_dashboard(self):
        readiness = WorkloadEngine.get_athlete_readiness()
        summary = CoachEngine.get_7day_summary()

        acwr = readiness.get("acwr", 1.0)
        risk = readiness.get("injury_risk_pct", 3.3)
        acute = readiness.get("acute_load", 0.0)
        chronic = readiness.get("chronic_load", 0.0)
        color = readiness.get("color", "#38A169")
        status = readiness.get("status", "Normal")

        self.card_acwr["val"].setText(f"{acwr}")
        self.card_acwr["val"].setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color};")

        risk_color = "#38A169" if risk < 5.0 else ("#DD6B20" if risk < 10.0 else "#E53E3E")
        self.card_risk["val"].setText(f"{risk} %")
        self.card_risk["val"].setStyleSheet(f"font-size: 18px; font-weight: bold; color: {risk_color};")

        self.card_acute["val"].setText(f"{acute}")
        self.card_chronic["val"].setText(f"{chronic}")
        self.card_vol["val"].setText(f"{summary['distance_km']} km ({summary['duration_str']})")
        self.card_dplus["val"].setText(f"+{summary['d_plus']}m / -{summary['d_minus']}m")

        self.lbl_status_banner.setText(f"Diagnostic : {status} (Modèle Blanch & Gabbett, 2015)")
        self.lbl_status_banner.setStyleSheet(
            f"background-color: {color}; color: white; padding: 8px 12px; border-radius: 4px; font-weight: bold; font-size: 12px;"
        )

        self.days = readiness.get("recent_days_labels", [])
        self.dists = readiness.get("recent_distances", [])
        self.durs = readiness.get("recent_durations", [])

        self.ax_dist.clear()
        self.ax_dur.clear()
        self.ax_dist.set_facecolor("#16191E")
        self.ax_dur.set_facecolor("#16191E")

        if self.days:
            x = np.arange(len(self.days))
            self.ax_dist.bar(x, self.dists, color="#4FD1C5", width=0.55, alpha=0.85)
            self.ax_dist.set_title("Distance Quotidienne (km)", color="#CBD5E0", fontsize=9, fontweight="bold")
            # TOUS LES JOURS EN ABSCISSE
            self.ax_dist.set_xticks(x)
            self.ax_dist.set_xticklabels(self.days, rotation=45, ha='right', color="#A0AEC0", fontsize=7)
            self.ax_dist.tick_params(colors="#A0AEC0", labelsize=7)
            self.ax_dist.grid(True, linestyle=":", alpha=0.2, color="#718096")

            self.ax_dur.bar(x, self.durs, color="#F6AD55", width=0.55, alpha=0.85)
            self.ax_dur.set_title("Temps d'Activité Quotidien (min)", color="#CBD5E0", fontsize=9, fontweight="bold")
            # TOUS LES JOURS EN ABSCISSE
            self.ax_dur.set_xticks(x)
            self.ax_dur.set_xticklabels(self.days, rotation=45, ha='right', color="#A0AEC0", fontsize=7)
            self.ax_dur.tick_params(colors="#A0AEC0", labelsize=7)
            self.ax_dur.grid(True, linestyle=":", alpha=0.2, color="#718096")

            for ax in (self.ax_dist, self.ax_dur):
                for s in ax.spines.values():
                    s.set_color("#2D3748")

        self.annot_dist = self._create_annot(self.ax_dist)
        self.annot_dur = self._create_annot(self.ax_dur)

        self.fig.tight_layout()
        self.canvas.draw()

    def _on_hover(self, event):
        if not self.days or event.xdata is None:
            return

        idx = int(round(event.xdata))
        if not (0 <= idx < len(self.days)):
            return

        x_off = -75 if idx > len(self.days) * 0.65 else 10

        if event.inaxes == self.ax_dist:
            val = self.dists[idx]
            self.annot_dist.xy = (idx, val)
            self.annot_dist.set_text(f"Date : {self.days[idx]}\nDistance : {val} km")
            self.annot_dist.set_position((x_off, 12))
            self.annot_dist.set_visible(True)
            self.annot_dur.set_visible(False)
            self.canvas.draw_idle()
        elif event.inaxes == self.ax_dur:
            val = self.durs[idx]
            self.annot_dur.xy = (idx, val)
            self.annot_dur.set_text(f"Date : {self.days[idx]}\nDurée : {val} min")
            self.annot_dur.set_position((x_off, 12))
            self.annot_dur.set_visible(True)
            self.annot_dist.set_visible(False)
            self.canvas.draw_idle()
        else:
            if self.annot_dist.get_visible() or self.annot_dur.get_visible():
                self.annot_dist.set_visible(False)
                self.annot_dur.set_visible(False)
                self.canvas.draw_idle()