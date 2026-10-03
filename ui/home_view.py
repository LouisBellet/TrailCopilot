from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox,
    QFrame, QGridLayout
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from core.data_manager import DataManager

class HomeView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(12)

        self.daily_days = []
        self.daily_dists = []
        self.daily_durs = []

        self.weekly_labels = []
        self.weekly_dists = []
        self.weekly_durs_h = []
        self.weekly_durs_min = []

        self._init_stat_cards()
        self._init_charts()
        self.refresh_dashboard()

    def _init_stat_cards(self):
        grp_kpi = QGroupBox("Indicateurs Physiques Actualisés & Trajectoire")
        grid = QGridLayout(grp_kpi)
        grid.setSpacing(10)

        self.card_acwr = self._create_kpi_card("RATIO ACWR ACTUEL", "--", "#38A169")
        self.card_budget = self._create_kpi_card("BUDGET TRIMP CIBLE (J)", "--", "#4FD1C5")
        self.card_acute = self._create_kpi_card("CHARGE AIGUË (7J)", "--", "#E2E8F0")
        self.card_chronic = self._create_kpi_card("CHARGE CHRONIQUE (28J)", "--", "#E2E8F0")
        self.card_vol = self._create_kpi_card("VOLUME 7J", "-- km", "#F6AD55")
        self.card_dplus = self._create_kpi_card("DÉNIVELÉ 7J", "+-- m / --- m", "#68D391")

        grid.addWidget(self.card_acwr["frame"], 0, 0)
        grid.addWidget(self.card_budget["frame"], 0, 1)
        grid.addWidget(self.card_acute["frame"], 0, 2)
        grid.addWidget(self.card_chronic["frame"], 0, 3)
        grid.addWidget(self.card_vol["frame"], 0, 4)
        grid.addWidget(self.card_dplus["frame"], 0, 5)

        self.lbl_status_banner = QLabel("Initialisation...")
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
        grp_charts = QGroupBox("Suivi de l'Activité Physique : Quotidien (14j) & Hebdomadaire (8 sem.)")
        v = QVBoxLayout(grp_charts)

        self.fig = Figure(figsize=(11, 3.6), facecolor="#1F242D")
        self.canvas = FigureCanvas(self.fig)
        self.canvas.mpl_connect("motion_notify_event", self._on_hover)

        v.addWidget(self.canvas)
        self.layout.addWidget(grp_charts)

    def _create_annot(self, ax):
        annot = ax.annotate(
            "", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="#1F242D", ec="#38B2AC", lw=1.3),
            color="#FFFFFF", fontsize=8, fontweight="bold", zorder=20
        )
        annot.set_visible(False)
        return annot

    def refresh_dashboard(self):
        readiness = DataManager.get_readiness()
        summary = DataManager.get_summary_7d()

        acwr = readiness.get("acwr", 1.0)
        target_budget = readiness.get("target_budget", 60.0)
        acute = readiness.get("acute_load", 0.0)
        chronic = readiness.get("chronic_load", 0.0)
        color = readiness.get("color", "#38A169")
        status = readiness.get("status", "Normal")

        self.card_acwr["val"].setText(f"{acwr}")
        self.card_acwr["val"].setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color};")
        self.card_budget["val"].setText(f"{target_budget} TRIMP")
        self.card_acute["val"].setText(f"{acute}")
        self.card_chronic["val"].setText(f"{chronic}")
        self.card_vol["val"].setText(f"{summary['distance_km']} km ({summary['duration_str']})")
        self.card_dplus["val"].setText(f"+{summary['d_plus']}m / -{summary['d_minus']}m")

        self.lbl_status_banner.setText(f"État du jour : {status} (Objectif Sweet Spot : ACWR ~ 1.05)")
        self.lbl_status_banner.setStyleSheet(
            f"background-color: {color}; color: white; padding: 8px 12px; border-radius: 4px; font-weight: bold; font-size: 12px;"
        )

        self.daily_days = readiness.get("recent_days_labels", [])
        self.daily_dists = readiness.get("recent_distances", [])
        self.daily_durs = readiness.get("recent_durations", [])

        self.weekly_labels = readiness.get("weekly_labels", [])
        self.weekly_dists = readiness.get("weekly_distances", [])
        self.weekly_durs_h = readiness.get("weekly_durations_h", [])
        self.weekly_durs_min = readiness.get("weekly_durations_min", [])

        self.fig.clear()

        # =====================================================================
        # 1. GRAPHIQUE QUOTIDIEN (HISTOGRAMME DOUBLE AXE)
        # =====================================================================
        self.ax_daily = self.fig.add_subplot(121)
        self.ax_daily.set_facecolor("#16191E")
        self.ax_daily_r = self.ax_daily.twinx()

        if self.daily_days:
            x_d = np.arange(len(self.daily_days))
            w = 0.35

            # Distance en barres cyan à gauche
            self.ax_daily.bar(x_d - w/2, self.daily_dists, width=w, color="#4FD1C5", alpha=0.85, label="Distance (km)")
            self.ax_daily.set_ylabel("Distance (km)", color="#4FD1C5", fontsize=8)
            self.ax_daily.tick_params(axis='y', colors="#4FD1C5", labelsize=7.5)
            max_dist = max(self.daily_dists) if self.daily_dists else 10
            self.ax_daily.set_ylim(0, max(12, max_dist * 1.25))

            # Durée en barres orange à droite
            self.ax_daily_r.bar(x_d + w/2, self.daily_durs, width=w, color="#F6AD55", alpha=0.85, label="Temps (min)")
            self.ax_daily_r.set_ylabel("Temps (min)", color="#F6AD55", fontsize=8)
            self.ax_daily_r.tick_params(axis='y', colors="#F6AD55", labelsize=7.5)
            max_dur = max(self.daily_durs) if self.daily_durs else 60
            self.ax_daily_r.set_ylim(0, max(60, max_dur * 1.25))

            self.ax_daily.set_title("Activité Quotidienne — 14 Derniers Jours (Histogramme)", color="#CBD5E0", fontsize=9, fontweight="bold")
            self.ax_daily.set_xticks(x_d)
            self.ax_daily.set_xticklabels(self.daily_days, rotation=45, ha='right', color="#A0AEC0", fontsize=7)
            self.ax_daily.tick_params(axis='x', colors="#A0AEC0", labelsize=7)
            self.ax_daily.grid(True, linestyle=":", alpha=0.2, color="#718096")

            # Légende combinée
            lines_1, labels_1 = self.ax_daily.get_legend_handles_labels()
            lines_2, labels_2 = self.ax_daily_r.get_legend_handles_labels()
            self.ax_daily.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper left", facecolor="#1F242D", edgecolor="#2D3748", fontsize=7, labelcolor="#E2E8F0")

        # =====================================================================
        # 2. GRAPHIQUE HEBDOMADAIRE (LIGNE BRISÉE DOUBLE AXE)
        # =====================================================================
        self.ax_weekly = self.fig.add_subplot(122)
        self.ax_weekly.set_facecolor("#16191E")
        self.ax_weekly_r = self.ax_weekly.twinx()

        if self.weekly_labels:
            x_w = np.arange(len(self.weekly_labels))

            # Distance hebdo : ligne brisée cyan
            self.ax_weekly.plot(x_w, self.weekly_dists, color="#4FD1C5", linewidth=2.0, marker="o", markersize=4, label="Distance (km)")
            self.ax_weekly.set_ylabel("Distance Hebdo (km)", color="#4FD1C5", fontsize=8)
            self.ax_weekly.tick_params(axis='y', colors="#4FD1C5", labelsize=7.5)
            max_w_dist = max(self.weekly_dists) if self.weekly_dists else 20
            self.ax_weekly.set_ylim(0, max(25, max_w_dist * 1.25))

            # Temps hebdo : ligne brisée orange en pointillés
            self.ax_weekly_r.plot(x_w, self.weekly_durs_h, color="#F6AD55", linewidth=2.0, linestyle="--", marker="s", markersize=4, label="Temps (h)")
            self.ax_weekly_r.set_ylabel("Temps Hebdo (heures)", color="#F6AD55", fontsize=8)
            self.ax_weekly_r.tick_params(axis='y', colors="#F6AD55", labelsize=7.5)
            max_w_dur_h = max(self.weekly_durs_h) if self.weekly_durs_h else 3.0
            self.ax_weekly_r.set_ylim(0, max(3.5, max_w_dur_h * 1.25))

            self.ax_weekly.set_title("Activité Hebdomadaire — 8 Semaines (Ligne Brisée)", color="#CBD5E0", fontsize=9, fontweight="bold")
            self.ax_weekly.set_xticks(x_w)
            self.ax_weekly.set_xticklabels(self.weekly_labels, rotation=30, ha='right', color="#A0AEC0", fontsize=7)
            self.ax_weekly.tick_params(axis='x', colors="#A0AEC0", labelsize=7)
            self.ax_weekly.grid(True, linestyle=":", alpha=0.2, color="#718096")

            # Légende combinée
            w_lines_1, w_labels_1 = self.ax_weekly.get_legend_handles_labels()
            w_lines_2, w_labels_2 = self.ax_weekly_r.get_legend_handles_labels()
            self.ax_weekly.legend(w_lines_1 + w_lines_2, w_labels_1 + w_labels_2, loc="upper left", facecolor="#1F242D", edgecolor="#2D3748", fontsize=7, labelcolor="#E2E8F0")

        for ax in (self.ax_daily, self.ax_daily_r, self.ax_weekly, self.ax_weekly_r):
            for s in ax.spines.values():
                s.set_color("#2D3748")

        self.annot_daily = self._create_annot(self.ax_daily)
        self.annot_weekly = self._create_annot(self.ax_weekly)

        self.fig.tight_layout()
        self.canvas.draw()

    def _on_hover(self, event):
        if event.xdata is None:
            return

        # Survol du Graphique 1 (Quotidien)
        if event.inaxes in (self.ax_daily, getattr(self, "ax_daily_r", None)):
            if not self.daily_days:
                return
            idx = int(round(event.xdata))
            if 0 <= idx < len(self.daily_days):
                d = self.daily_dists[idx]
                t = self.daily_durs[idx]
                x_off = -90 if idx > len(self.daily_days) * 0.65 else 10
                self.annot_daily.xy = (idx, d)
                self.annot_daily.set_text(f"Date : {self.daily_days[idx]}\nDistance : {d} km\nDurée : {int(t)} min")
                self.annot_daily.set_position((x_off, 12))
                self.annot_daily.set_visible(True)
                self.annot_weekly.set_visible(False)
                self.canvas.draw_idle()
                return

        # Survol du Graphique 2 (Hebdomadaire)
        elif event.inaxes in (self.ax_weekly, getattr(self, "ax_weekly_r", None)):
            if not self.weekly_labels:
                return
            idx = int(round(event.xdata))
            if 0 <= idx < len(self.weekly_labels):
                d = self.weekly_dists[idx]
                h = self.weekly_durs_h[idx]
                tot_min = int(self.weekly_durations_min[idx]) if hasattr(self, "weekly_durations_min") and idx < len(self.weekly_durations_min) else int(h * 60)
                h_int = int(tot_min // 60)
                m_int = int(tot_min % 60)
                x_off = -90 if idx > len(self.weekly_labels) * 0.65 else 10
                self.annot_weekly.xy = (idx, d)
                self.annot_weekly.set_text(f"{self.weekly_labels[idx]}\nDistance : {d} km\nTemps : {h_int}h{m_int:02d} ({h}h)")
                self.annot_weekly.set_position((x_off, 12))
                self.annot_weekly.set_visible(True)
                self.annot_daily.set_visible(False)
                self.canvas.draw_idle()
                return

        if self.annot_daily.get_visible() or self.annot_weekly.get_visible():
            self.annot_daily.set_visible(False)
            self.annot_weekly.set_visible(False)
            self.canvas.draw_idle()