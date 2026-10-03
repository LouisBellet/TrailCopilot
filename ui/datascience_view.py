from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QScrollArea, QFrame, QGridLayout
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from core.data_manager import DataManager
from core.datascience_engine import DataScienceEngine

class DataScienceView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_loaded = False
        self.analytics = {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        header = QFrame()
        header.setStyleSheet("background:#1F242D; border:1px solid #2D3748; border-radius:6px; padding:8px;")
        h_box = QHBoxLayout(header)
        h_box.setContentsMargins(8, 6, 8, 6)

        lbl_desc = QLabel(
            "🧪 <b>Laboratoire Data Science — Course & Trail Haute Fréquence</b><br>"
            "<span style='color:#A0AEC0; font-size:11px;'>"
            "Couplage vitesse/cardio, indice de polarisation Seiler (80/20), typologie des séances et distributions statistiques. "
            "La <b>dernière séance</b> est toujours mise en évidence.</span>"
        )
        lbl_desc.setTextFormat(Qt.RichText)
        h_box.addWidget(lbl_desc)
        main_layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        self.grid = QGridLayout(container)
        self.grid.setSpacing(14)
        self.grid.setContentsMargins(4, 4, 4, 4)

        self.charts = []
        titles = [
            "1. Évolution du Rendement Aérobie (Vitesse / FC)",
            "2. Cartographie & Clustering des Séances (Distance vs Vitesse)",
            "3. Relation Vitesse en fonction de la FC (km/h vs bpm)",
            "4. Indice de Polarisation des Intensités (Modèle Seiler 80/20)",
            "5. Histogramme de Distribution : Vitesse (km/h)",
            "6. Histogramme de Distribution : Distance (km)",
            "7. Histogramme de Distribution : Fréquence Cardiaque (bpm)",
            "8. Histogramme de Distribution : Effort Perçu (Borg RPE)"
        ]

        for idx, t in enumerate(titles):
            box = QGroupBox(t)
            box.setStyleSheet("QGroupBox { font-weight: bold; font-size: 12px; color: #E2E8F0; }")
            v = QVBoxLayout(box)
            v.setContentsMargins(6, 6, 6, 6)

            fig = Figure(figsize=(7.2, 4.2), facecolor="#1F242D")
            canvas = FigureCanvas(fig)
            canvas.setMinimumHeight(380)
            ax = fig.add_subplot(111)

            annot = ax.annotate(
                "", xy=(0, 0), xytext=(12, 12), textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.5", fc="#1F242D", ec="#38B2AC", lw=1.2),
                color="#FFFFFF", fontsize=8, fontweight="bold", zorder=20
            )
            annot.set_visible(False)

            v.addWidget(canvas)
            row = idx // 2
            col = idx % 2
            self.grid.addWidget(box, row, col)

            self.charts.append({
                "box": box, "fig": fig, "canvas": canvas,
                "ax": ax, "annot": annot, "idx": idx
            })
            canvas.mpl_connect("motion_notify_event", lambda ev, i=idx: self._on_hover(ev, i))

        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        self._draw_all_empty("Chargement des analyses...")

    def ensure_loaded(self):
        if not self.is_loaded or DataManager.is_tab_dirty(3):
            self.refresh_analytics()
            self.is_loaded = True
            DataManager.mark_tab_clean(3)

    def _draw_all_empty(self, msg: str):
        for c in self.charts:
            ax = c["ax"]
            ax.clear()
            ax.set_facecolor("#16191E")
            ax.text(0.5, 0.5, msg, color="#718096", ha="center", va="center", transform=ax.transAxes, fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
            for s in ax.spines.values():
                s.set_color("#2D3748")
            c["canvas"].draw()

    def refresh_analytics(self):
        activities = DataManager.get_activities()
        self.analytics = DataScienceEngine.get_focused_analytics(activities)

        if self.analytics.get("empty"):
            reason = self.analytics.get("reason")
            msg = (
                "Aucune séance de Course ou Trail enregistrée.\n(Les activités Vélo, Ski, Natation sont exclues de cette analyse)"
                if reason == "no_running_found"
                else "Saisissez ou importez des séances pour alimenter l'analyse."
            )
            self._draw_all_empty(msg)
            return

        dates = self.analytics["dates"]
        efs = self.analytics["ef_list"]
        speeds = self.analytics["speeds"]
        dists = self.analytics["dists"]
        fcs = self.analytics["fcs"]
        rpes = self.analytics["rpes"]
        z_lows = self.analytics["z_lows"]
        z_mods = self.analytics["z_mods"]
        z_highs = self.analytics["z_highs"]
        clusters = self.analytics["clusters"]
        cluster_names = self.analytics["cluster_names"]
        last_idx = self.analytics["last_run_idx"]

        n_points = len(dates)
        x = np.arange(n_points)
        step = max(1, int(np.ceil(n_points / 9))) if n_points > 10 else 1

        # 1. Évolution Rendement (Vitesse / FC)
        c1 = self.charts[0]
        ax1 = c1["ax"]
        ax1.clear()
        ax1.set_facecolor("#16191E")
        ax1.plot(x, efs, color="#4FD1C5", linewidth=1.5, zorder=3)
        if last_idx > 0:
            ax1.scatter(x[:-1], efs[:-1], color="#4FD1C5", marker="+", s=36, linewidths=1.2, label="Séances antérieures", zorder=4)
        if n_points >= 2:
            p_trend = np.polyfit(x, efs, 1)
            ax1.plot(x, np.polyval(p_trend, x), color="#F6AD55", linestyle=":", linewidth=1.8, label="Tendance")
        ax1.scatter([x[last_idx]], [efs[last_idx]], color="#FF1744", marker="D", s=75, edgecolor="#FFFFFF", linewidth=1.8, label="Dernière", zorder=10)
        self._apply_date_axis(ax1, x, dates, step)
        ax1.set_ylabel("(km/h / FC) × 100", color="#CBD5E0", fontsize=8.5)
        self._format_axis(ax1)

        # 2. Clustering (Distance vs Vitesse)
        c2 = self.charts[1]
        ax2 = c2["ax"]
        ax2.clear()
        ax2.set_facecolor("#16191E")
        palette = ["#4FD1C5", "#63B3ED", "#9F7AEA", "#ED8936"]
        unique_c = sorted(list(set(clusters)))
        for cl in unique_c:
            mask = [i for i, c in enumerate(clusters) if c == cl and i != last_idx]
            if mask:
                ax2.scatter([dists[i] for i in mask], [speeds[i] for i in mask], color=palette[cl % len(palette)], marker="+", s=38, linewidths=1.3, label=cluster_names.get(cl, f"Groupe {cl+1}"), zorder=4)
        ax2.scatter([dists[last_idx]], [speeds[last_idx]], color="#FF1744", marker="*", s=160, edgecolor="#FFFFFF", linewidth=1.2, label="Dernière séance", zorder=10)
        ax2.set_xlabel("Distance (km)", color="#CBD5E0", fontsize=8.5)
        ax2.set_ylabel("Vitesse Moyenne (km/h)", color="#CBD5E0", fontsize=8.5)
        self._format_axis(ax2)

        # 3. Vitesse vs FC
        c3 = self.charts[2]
        ax3 = c3["ax"]
        ax3.clear()
        ax3.set_facecolor("#16191E")
        if last_idx > 0:
            ax3.scatter(fcs[:-1], speeds[:-1], color="#38B2AC", marker="+", s=38, linewidths=1.3, label="Séances antérieures", zorder=4)
        if len(fcs) >= 3 and len(set(fcs)) > 1:
            slope, inter = np.polyfit(fcs, speeds, 1)
            fc_grid = np.linspace(min(fcs), max(fcs), 20)
            ax3.plot(fc_grid, slope * fc_grid + inter, color="#F6AD55", linestyle=":", linewidth=1.8, label=f"Pente : +{slope*10:.2f} km/h / 10 bpm")
        ax3.scatter([fcs[last_idx]], [speeds[last_idx]], color="#FF1744", marker="D", s=80, edgecolor="#FFFFFF", linewidth=1.8, label="Dernière", zorder=10)
        ax3.set_xlabel("FC Moyenne (bpm)", color="#CBD5E0", fontsize=8.5)
        ax3.set_ylabel("Vitesse (km/h)", color="#CBD5E0", fontsize=8.5)
        self._format_axis(ax3)

        # 4. INDICE DE POLARISATION (Modèle Seiler 80/20)
        c4 = self.charts[3]
        ax4 = c4["ax"]
        ax4.clear()
        ax4.set_facecolor("#16191E")
        w_bar = 0.55
        ax4.bar(x, z_lows, width=w_bar, color="#38A169", alpha=0.85, label="Basse intensité (Z1-Z2)")
        ax4.bar(x, z_mods, width=w_bar, bottom=z_lows, color="#DD6B20", alpha=0.85, label="Seuil (Z3)")
        bottom_high = np.array(z_lows) + np.array(z_mods)
        ax4.bar(x, z_highs, width=w_bar, bottom=bottom_high, color="#E53E3E", alpha=0.85, label="Haute intensité (Z4-Z5)")
        ax4.axhline(80.0, color="#E2E8F0", linestyle="--", linewidth=1.2, label="Cible Polarisée 80%")

        # Mise en évidence de la dernière séance
        ax4.scatter([x[last_idx]], [103.0], color="#FF1744", marker="v", s=80, label="Dernière", zorder=10)
        self._apply_date_axis(ax4, x, dates, step)
        ax4.set_ylim(0, 110)
        ax4.set_ylabel("% Répartition du Temps", color="#CBD5E0", fontsize=8.5)
        self._format_axis(ax4)

        # 5. Histogramme Vitesse
        self._render_histogram(self.charts[4]["ax"], speeds, speeds[last_idx], "#3182CE", "km/h", f"{speeds[last_idx]} km/h")

        # 6. Histogramme Distance
        self._render_histogram(self.charts[5]["ax"], dists, dists[last_idx], "#38A169", "km", f"{dists[last_idx]} km")

        # 7. Histogramme Fréquence Cardiaque
        self._render_histogram(self.charts[6]["ax"], fcs, fcs[last_idx], "#805AD5", "bpm", f"{fcs[last_idx]} bpm")

        # 8. Histogramme Borg RPE
        self._render_histogram(self.charts[7]["ax"], rpes, rpes[last_idx], "#DD6B20", "Borg", f"RPE {rpes[last_idx]}/20")

        for c in self.charts:
            c["fig"].tight_layout()
            c["canvas"].draw()

    def _render_histogram(self, ax, data_list, last_val, color_bar, unit, title_val):
        ax.clear()
        ax.set_facecolor("#16191E")
        bins = min(12, max(4, int(np.sqrt(len(data_list)))))
        counts, _, _ = ax.hist(data_list, bins=bins, color=color_bar, alpha=0.75, edgecolor="#1F242D", rwidth=0.88, label="Distribution")
        ax.axvline(last_val, color="#FF1744", linestyle="--", linewidth=2.0, zorder=6, label=f"Dernière : {title_val}")
        max_y = max(counts) if len(counts) > 0 else 1
        ax.annotate(f"Dernière : {title_val}", xy=(last_val, max_y * 0.88), xytext=(8, 0), textcoords="offset points", fontsize=7.5, fontweight="bold", color="#FF8A80", bbox=dict(boxstyle="round,pad=0.25", fc="#1F242D", ec="#FF1744", lw=1.2))
        ax.set_xlabel(unit, color="#CBD5E0", fontsize=8.5)
        ax.set_ylabel("Nombre de séances", color="#CBD5E0", fontsize=8.5)
        self._format_axis(ax)

    def _apply_date_axis(self, ax, x, dates, step):
        ticks_pos = x[::step]
        ticks_labels = [dates[i] for i in ticks_pos]
        ax.set_xticks(ticks_pos)
        ax.set_xticklabels(ticks_labels, rotation=30, ha='right', color="#CBD5E0", fontsize=8.5)

    def _format_axis(self, ax):
        ax.tick_params(colors="#A0AEC0", labelsize=8)
        ax.grid(True, linestyle=":", alpha=0.2, color="#718096")
        for s in ax.spines.values():
            s.set_color("#2D3748")
        ax.legend(loc="upper left", facecolor="#1F242D", edgecolor="#2D3748", fontsize=7, labelcolor="#E2E8F0")

    def _on_hover(self, event, chart_idx):
        c = self.charts[chart_idx]
        annot = c["annot"]
        runs = self.analytics.get("runs", [])
        if not runs or event.xdata is None or event.ydata is None:
            return

        if chart_idx in (0, 3):  # Temporel
            idx = int(round(event.xdata))
            if 0 <= idx < len(runs):
                r = runs[idx]
                if chart_idx == 0:
                    annot.xy = (idx, r["ef"])
                    annot.set_text(f"Date : {r['date']}\nRapport : {r['ef']}\nVitesse : {r['speed']} km/h\nFC : {r['fc']} bpm")
                else:
                    annot.xy = (idx, 50)
                    annot.set_text(f"Date : {r['date']}\nZ1-Z2 (Basse) : {r['z_low']}%\nZ3 (Seuil) : {r['z_mod']}%\nZ4-Z5 (Haute) : {r['z_high']}%")
                annot.set_visible(True)
                c["canvas"].draw_idle()
                return

        elif chart_idx == 1:
            annot.xy = (event.xdata, event.ydata)
            annot.set_text(f"Distance : {event.xdata:.1f} km\nVitesse : {event.ydata:.1f} km/h")
            annot.set_visible(True)
            c["canvas"].draw_idle()
            return

        elif chart_idx == 2:
            annot.xy = (event.xdata, event.ydata)
            annot.set_text(f"FC : {int(event.xdata)} bpm\nVitesse : {event.ydata:.1f} km/h")
            annot.set_visible(True)
            c["canvas"].draw_idle()
            return

        if annot.get_visible():
            annot.set_visible(False)
            c["canvas"].draw_idle()