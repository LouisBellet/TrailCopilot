from PySide6.QtWidgets import QWidget, QHBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

class WorkloadGaugeChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)

        self.fig = Figure(figsize=(12, 3.2), facecolor="#1F242D")
        self.canvas = FigureCanvas(self.fig)
        self.layout.addWidget(self.canvas)

        self.ax1 = self.fig.add_subplot(131)
        self.ax2 = self.fig.add_subplot(132)
        self.ax3 = self.fig.add_subplot(133)

        self.days = []
        self.acwr_vals = []
        self.acute_vals = []
        self.chronic_vals = []
        self.daily_vals = []
        self.risk_vals = []

        self.annot1 = self._create_annot(self.ax1)
        self.annot2 = self._create_annot(self.ax2)
        self.annot3 = self._create_annot(self.ax3)

        self.canvas.mpl_connect("motion_notify_event", self._on_hover)
        self._draw_empty()

    def _create_annot(self, ax):
        annot = ax.annotate(
            "", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="#1F242D", ec="#38B2AC", lw=1.5),
            color="#FFFFFF", fontsize=8, fontweight="bold", zorder=10
        )
        annot.set_visible(False)
        return annot

    def _draw_empty(self):
        for ax in (self.ax1, self.ax2, self.ax3):
            ax.clear()
            ax.set_facecolor("#16191E")
            ax.set_xticks([])
            ax.set_yticks([])
            for s in ax.spines.values():
                s.set_color("#2D3748")
        self.ax1.text(0.5, 0.5, "Importez des activités pour charger l'analyse", color="#718096", ha="center", va="center", transform=self.ax1.transAxes, fontsize=8)
        self.canvas.draw()

    def plot_all_indicators(self, data: dict):
        self.days = data.get("timeline_days", [])
        self.acwr_vals = data.get("timeline_acwr", [])
        self.acute_vals = data.get("timeline_acute", [])
        self.chronic_vals = data.get("timeline_chronic", [])
        self.daily_vals = data.get("timeline_daily_load", [])
        self.risk_vals = data.get("timeline_risk", [])
        cur_acwr = data.get("acwr", 1.0)
        cur_risk = data.get("injury_risk_pct", 3.3)

        if not self.acwr_vals or len(self.acwr_vals) < 2:
            self._draw_empty()
            return

        x = np.arange(len(self.days))

        # 1. ACWR & Risque Blanch & Gabbett (2015)
        self.ax1.clear()
        self.ax1.set_facecolor("#16191E")
        self.ax1.set_title(f"ACWR & Risque Blessure ({cur_acwr} | {cur_risk}%)", color="#CBD5E0", fontsize=9, fontweight="bold")
        self.ax1.axhspan(0.0, 0.8, color="#3182CE", alpha=0.15, label="Sous-charge (<0.8)")
        self.ax1.axhspan(0.8, 1.3, color="#38A169", alpha=0.25, label="Sweet Spot (0.8-1.3)")
        self.ax1.axhspan(1.3, 1.5, color="#DD6B20", alpha=0.22, label="Vigilance (1.3-1.5)")
        self.ax1.axhspan(1.5, 3.0, color="#E53E3E", alpha=0.25, label="Zone Danger (>1.5)")

        self.ax1.plot(x, self.acwr_vals, color="#E2E8F0", linewidth=1.8, marker="o", markersize=2.5, label="ACWR")
        self.ax1_r = self.ax1.twinx()
        self.ax1_r.plot(x, self.risk_vals, color="#FC8181", linestyle=":", linewidth=1.5, label="Risque %")
        self.ax1_r.set_ylabel("Risque %", color="#FC8181", fontsize=8)
        self.ax1_r.tick_params(colors="#FC8181", labelsize=7)

        v_min, v_max = min(self.acwr_vals), max(self.acwr_vals)
        c_y = (v_min + v_max) / 2.0
        h_span = max((v_max - v_min) / 2.0 * 1.4, 0.4)
        self.ax1.set_ylim(max(0.0, c_y - h_span), c_y + h_span)

        # TOUS LES JOURS EN ABSCISSE
        self.ax1.set_xticks(x)
        self.ax1.set_xticklabels(self.days, rotation=90, ha='center', color="#A0AEC0", fontsize=6)
        self.ax1.tick_params(colors="#A0AEC0", labelsize=7)
        self.ax1.grid(True, linestyle=":", alpha=0.2, color="#718096")

        # 2. Charge Aiguë (7j) vs Chronique (28j)
        self.ax2.clear()
        self.ax2.set_facecolor("#16191E")
        self.ax2.set_title("Dynamique : Aiguë (7j) vs Chronique (28j)", color="#CBD5E0", fontsize=9, fontweight="bold")
        self.ax2.plot(x, self.acute_vals, color="#E53E3E", linewidth=1.8, label="Aiguë (Fatigue)")
        self.ax2.plot(x, self.chronic_vals, color="#3182CE", linewidth=1.8, linestyle="--", label="Chronique (Fitness)")
        self.ax2.fill_between(x, self.acute_vals, self.chronic_vals, where=(np.array(self.acute_vals) >= np.array(self.chronic_vals)), color="#E53E3E", alpha=0.15)
        self.ax2.fill_between(x, self.acute_vals, self.chronic_vals, where=(np.array(self.acute_vals) < np.array(self.chronic_vals)), color="#38A169", alpha=0.15)

        # TOUS LES JOURS EN ABSCISSE
        self.ax2.set_xticks(x)
        self.ax2.set_xticklabels(self.days, rotation=90, ha='center', color="#A0AEC0", fontsize=6)
        self.ax2.tick_params(colors="#A0AEC0", labelsize=7)
        self.ax2.grid(True, linestyle=":", alpha=0.2, color="#718096")
        self.ax2.legend(loc="upper left", facecolor="#1F242D", edgecolor="#2D3748", fontsize=7, labelcolor="#E2E8F0")

        # 3. Charge Quotidienne Réalisée
        self.ax3.clear()
        self.ax3.set_facecolor("#16191E")
        self.ax3.set_title("Charge Quotidienne (TRIMP/AU)", color="#CBD5E0", fontsize=9, fontweight="bold")
        self.ax3.bar(x, self.daily_vals, color="#38B2AC", width=0.6, alpha=0.85, label="Charge/Jour")

        # TOUS LES JOURS EN ABSCISSE
        self.ax3.set_xticks(x)
        self.ax3.set_xticklabels(self.days, rotation=90, ha='center', color="#A0AEC0", fontsize=6)
        self.ax3.tick_params(colors="#A0AEC0", labelsize=7)
        self.ax3.grid(True, linestyle=":", alpha=0.2, color="#718096")
        self.ax3.legend(loc="upper left", facecolor="#1F242D", edgecolor="#2D3748", fontsize=7, labelcolor="#E2E8F0")

        for ax in (self.ax1, self.ax2, self.ax3, self.ax1_r):
            for s in ax.spines.values():
                s.set_color("#2D3748")

        self.annot1 = self._create_annot(self.ax1)
        self.annot2 = self._create_annot(self.ax2)
        self.annot3 = self._create_annot(self.ax3)

        self.fig.tight_layout()
        self.canvas.draw()

    def _on_hover(self, event):
        if not self.days or event.xdata is None:
            return

        idx = int(round(event.xdata))
        if not (0 <= idx < len(self.days)):
            return

        x_off = -85 if idx > len(self.days) * 0.65 else 10

        # Survol Axe 1 (ACWR)
        if event.inaxes in (self.ax1, getattr(self, "ax1_r", None)):
            val_acwr = self.acwr_vals[idx]
            val_risk = self.risk_vals[idx]
            self.annot1.xy = (idx, val_acwr)
            self.annot1.set_text(f"Date : {self.days[idx]}\nACWR : {val_acwr}\nRisque : {val_risk}%")
            self.annot1.set_position((x_off, 12))
            self.annot1.set_visible(True)
            self.annot2.set_visible(False)
            self.annot3.set_visible(False)
            self.canvas.draw_idle()

        # Survol Axe 2 (Aiguë vs Chronique)
        elif event.inaxes == self.ax2:
            val_acute = self.acute_vals[idx]
            val_chronic = self.chronic_vals[idx]
            self.annot2.xy = (idx, val_acute)
            self.annot2.set_text(f"Date : {self.days[idx]}\nAiguë (7j) : {val_acute}\nChronique (28j) : {val_chronic}")
            self.annot2.set_position((x_off, 12))
            self.annot2.set_visible(True)
            self.annot1.set_visible(False)
            self.annot3.set_visible(False)
            self.canvas.draw_idle()

        # Survol Axe 3 (Charge journalière)
        elif event.inaxes == self.ax3:
            val_daily = self.daily_vals[idx]
            self.annot3.xy = (idx, val_daily)
            self.annot3.set_text(f"Date : {self.days[idx]}\nCharge : {val_daily} TRIMP")
            self.annot3.set_position((x_off, 12))
            self.annot3.set_visible(True)
            self.annot1.set_visible(False)
            self.annot2.set_visible(False)
            self.canvas.draw_idle()
        else:
            if self.annot1.get_visible() or self.annot2.get_visible() or self.annot3.get_visible():
                self.annot1.set_visible(False)
                self.annot2.set_visible(False)
                self.annot3.set_visible(False)
                self.canvas.draw_idle()