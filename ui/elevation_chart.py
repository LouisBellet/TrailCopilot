import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from core.dem_engine import DEMEngine

class ElevationChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Création de la figure Matplotlib avec palette sombre
        self.fig = Figure(figsize=(5, 2.2), facecolor="#1F242D")
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#16191E")
        self.layout.addWidget(self.canvas)

        self._draw_empty()

    def _draw_empty(self):
        self.ax.clear()
        self.ax.text(0.5, 0.5, "Sélectionnez un itinéraire pour afficher le profil", 
                     color="#718096", ha="center", va="center", transform=self.ax.transAxes, fontsize=10)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        for spine in self.ax.spines.values():
            spine.set_color("#2D3748")
        self.canvas.draw()

    def plot_profile(self, coords: list, elevations: list, title: str = ""):
        """Trace le profil altimétrique : Distance cumulée (km) vs Altitude (m)."""
        if not coords or not elevations or len(coords) != len(elevations):
            self._draw_empty()
            return

        # 1. Calcul des distances cumulées en kilomètres
        distances_km = [0.0]
        total_dist = 0.0
        for i in range(len(coords) - 1):
            d = DEMEngine.haversine_distance(coords[i], coords[i+1])
            total_dist += d
            distances_km.append(total_dist / 1000.0)

        self.ax.clear()
        self.ax.set_facecolor("#16191E")

        # 2. Dessin de la courbe et remplissage dégradé
        x = np.array(distances_km)
        y = np.array(elevations)

        self.ax.plot(x, y, color="#38B2AC", linewidth=2.2, label="Altitude")
        self.ax.fill_between(x, y, min(y) - 50, color="#38B2AC", alpha=0.25)

        # 3. Lignes et repères visuels min/max
        min_ele, max_ele = int(min(y)), int(max(y))
        min_idx, max_idx = int(np.argmin(y)), int(np.argmax(y))

        self.ax.scatter([x[min_idx], x[max_idx]], [min_ele, max_ele], color="#ED8936", s=30, zorder=5)
        self.ax.annotate(f"Min: {min_ele}m", (x[min_idx], min_ele), textcoords="offset points", 
                         xytext=(0, -14), ha='center', color="#CBD5E0", fontsize=8, weight='bold')
        self.ax.annotate(f"Max: {max_ele}m", (x[max_idx], max_ele), textcoords="offset points", 
                         xytext=(0, 6), ha='center', color="#CBD5E0", fontsize=8, weight='bold')

        # 4. Styling des axes et de la grille
        self.ax.set_xlabel("Distance (km)", color="#A0AEC0", fontsize=9)
        self.ax.set_ylabel("Altitude (m)", color="#A0AEC0", fontsize=9)
        self.ax.tick_params(colors="#A0AEC0", labelsize=8)
        self.ax.grid(True, linestyle="--", alpha=0.2, color="#718096")
        self.ax.set_ylim(bottom=max(0, min_ele - 100), top=max_ele + 120)

        for spine in self.ax.spines.values():
            spine.set_color("#2D3748")

        self.fig.tight_layout()
        self.canvas.draw()