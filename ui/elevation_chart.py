from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import math

def haversine_dist(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

class ElevationChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.fig = Figure(figsize=(5, 2.5), facecolor="#1F242D")
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.layout.addWidget(self.canvas)
        self._draw_empty("Sélectionnez un itinéraire pour voir le profil")

    def _draw_empty(self, message: str):
        self.ax.clear()
        self.ax.set_facecolor("#16191E")
        self.ax.text(
            0.5, 0.5, message,
            color="#A0AEC0", ha="center", va="center",
            transform=self.ax.transAxes, fontsize=8.5, wrap=True
        )
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        for s in self.ax.spines.values():
            s.set_color("#2D3748")
        self.canvas.draw()

    def plot_profile(self, coords: list, elevations: list, title: str, critical_segments: list = None, has_track: bool = True):
        if not has_track or not coords or not elevations or len(coords) < 2:
            self._draw_empty("⚠️ Trace altimétrique non renseignée sur Camptocamp\n(Topo descriptif seul)")
            return

        distances_km = [0.0]
        for i in range(1, len(coords)):
            d = haversine_dist(coords[i-1][0], coords[i-1][1], coords[i][0], coords[i][1]) / 1000.0
            distances_km.append(distances_km[-1] + d)

        self.ax.clear()
        self.ax.set_facecolor("#16191E")

        self.ax.plot(distances_km, elevations, color="#38B2AC", linewidth=2.2, label="Altitude (m)")
        min_ele = min(elevations)
        max_ele = max(elevations)
        self.ax.fill_between(distances_km, elevations, min_ele - 50, color="#38B2AC", alpha=0.25)

        if critical_segments:
            for seg in critical_segments:
                s_km = seg.get("start_km", 0.0)
                e_km = seg.get("end_km", 0.0)
                s_idx = seg.get("start_idx", 0)
                e_idx = seg.get("end_idx", len(coords) - 1)

                self.ax.axvspan(s_km, e_km, color="#E53E3E", alpha=0.32, zorder=2)

                sub_dists = distances_km[s_idx : e_idx + 1]
                sub_eles = elevations[s_idx : e_idx + 1]
                if sub_dists and sub_eles:
                    self.ax.plot(sub_dists, sub_eles, color="#FF1744", linewidth=3.0, linestyle="--", zorder=4)
                    mid_km = (s_km + e_km) / 2.0
                    peak_sub = max(sub_eles)
                    self.ax.annotate(
                        "⚠️ Passage délicat",
                        xy=(mid_km, peak_sub),
                        xytext=(0, 12),
                        textcoords="offset points",
                        ha="center",
                        fontsize=7.5,
                        fontweight="bold",
                        color="#FF8A80",
                        bbox=dict(boxstyle="round,pad=0.25", fc="#1F242D", ec="#FF1744", lw=1.2)
                    )

        self.ax.set_ylim(bottom=max(0, min_ele - 60), top=max_ele + 100)
        self.ax.set_xlabel("Distance (km)", color="#CBD5E0", fontsize=8)
        self.ax.set_ylabel("Altitude (m)", color="#CBD5E0", fontsize=8)
        self.ax.tick_params(colors="#A0AEC0", labelsize=7.5)
        self.ax.grid(True, linestyle=":", alpha=0.25, color="#718096")

        for s in self.ax.spines.values():
            s.set_color("#2D3748")

        self.fig.tight_layout()
        self.canvas.draw()