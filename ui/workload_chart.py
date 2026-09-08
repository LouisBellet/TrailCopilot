from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

class WorkloadGaugeChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.fig = Figure(figsize=(7, 2.6), facecolor="#1F242D")
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.layout.addWidget(self.canvas)
        self._draw_empty()

    def _draw_empty(self):
        self.ax.clear()
        self.ax.set_facecolor("#16191E")
        self.ax.text(0.5, 0.5, "Importez des fichiers .FIT pour afficher la dynamique de charge", 
                     color="#718096", ha="center", va="center", transform=self.ax.transAxes, fontsize=9)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        for s in self.ax.spines.values():
            s.set_color("#2D3748")
        self.canvas.draw()

    def plot_acwr_timeline(self, days_labels: list, acwr_values: list, current_acwr: float):
        """Trace l'historique ACWR sur 28 jours au sein des couloirs de charge."""
        if not acwr_values or len(acwr_values) < 2:
            self._draw_empty()
            return

        self.ax.clear()
        self.ax.set_facecolor("#16191E")

        # 1. Couloirs de charge normés (Tim Gabbett framework)
        self.ax.axhspan(0.0, 0.8, color="#3182CE", alpha=0.18, label="Sous-charge (<0.8)")
        self.ax.axhspan(0.8, 1.3, color="#38A169", alpha=0.25, label="Zone Optimale (0.8 - 1.3)")
        self.ax.axhspan(1.3, 1.5, color="#DD6B20", alpha=0.22, label="Surcharge modérée (1.3 - 1.5)")
        self.ax.axhspan(1.5, 2.5, color="#E53E3E", alpha=0.25, label="Danger / Blessure (>1.5)")

        # 2. Ligne de charge
        x = np.arange(len(acwr_values))
        self.ax.plot(x, acwr_values, color="#E2E8F0", linewidth=2.2, marker="o", markersize=3.5, label="Votre ACWR")

        # 3. Point d'aujourd'hui
        pt_color = "#38A169" if 0.8 <= current_acwr <= 1.3 else ("#E53E3E" if current_acwr > 1.5 else "#DD6B20")
        self.ax.scatter([x[-1]], [current_acwr], color=pt_color, s=80, zorder=5, edgecolors="#FFFFFF")
        self.ax.annotate(f"Actuel: {current_acwr}", (x[-1], current_acwr),
                         textcoords="offset points", xytext=(-25, 10),
                         color=pt_color, fontweight='bold', fontsize=9)

        # 4. Formattage
        step = max(1, len(x) // 6)
        self.ax.set_xticks(x[::step])
        self.ax.set_xticklabels(days_labels[::step], rotation=15, ha='right', color="#A0AEC0", fontsize=8)
        self.ax.set_ylabel("Ratio ACWR", color="#CBD5E0", fontsize=8.5)
        self.ax.set_ylim(0.4, 2.3)
        self.ax.tick_params(colors="#A0AEC0", labelsize=8)
        self.ax.grid(True, linestyle=":", alpha=0.2, color="#718096")
        self.ax.legend(loc="upper left", facecolor="#1F242D", edgecolor="#2D3748", fontsize=7, labelcolor="#E2E8F0")

        for s in self.ax.spines.values():
            s.set_color("#2D3748")

        self.fig.tight_layout()
        self.canvas.draw()