import os
import re
from datetime import datetime
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QComboBox,
    QProgressBar, QTextBrowser, QSplitter, QFileDialog, QMessageBox,
    QTabWidget
)

from core.conditions_checker import get_recent_weather, get_avalanche_risk
from core.satellite_analyzer import analyze_snow_coverage
from core.scraper_c2c import search_routes
from core.feasibility_engine import FeasibilityEngine
from core.workload_engine import WorkloadEngine
from ui.map_view import MapView
from ui.elevation_chart import ElevationChart
from ui.training_view import TrainingView

MASSIFS = {
    "Pyrénées — Gavarnie & Vignemale": {"center": [42.7290, -0.0450], "bbox": [-0.15, 42.68, 0.05, 42.80], "bera": "HAUTE-BIGORRE"},
    "Pyrénées — Néouvielle & Lacs": {"center": [42.8350, 0.1420], "bbox": [0.08, 42.78, 0.22, 42.89], "bera": "HAUTE-BIGORRE"},
    "Pyrénées — Vallée d'Ossau & Ayous": {"center": [42.8420, -0.4350], "bbox": [-0.52, 42.79, -0.35, 42.91], "bera": "ASPE-OSSAU"},
    "Pyrénées — Cauterets & Gaube": {"center": [42.8550, -0.1150], "bbox": [-0.18, 42.78, -0.06, 42.89], "bera": "HAUTE-BIGORRE"},
    "Pyrénées — Luchonnais & Vénasque": {"center": [42.7200, 0.5850], "bbox": [0.50, 42.66, 0.65, 42.78], "bera": "LUCHONNAIS"},
    "Pyrénées — Carlit & Bouillouses": {"center": [42.5700, 1.9900], "bbox": [1.90, 42.52, 2.06, 42.62], "bera": "CERDAGNE-CANIGOU"},
    "Pyrénées — Massif du Canigou": {"center": [42.5180, 2.4560], "bbox": [2.40, 42.47, 2.52, 42.56], "bera": "CERDAGNE-CANIGOU"},
    "Alpes — Mont-Blanc": {"center": [45.8600, 6.7400], "bbox": [6.70, 45.80, 7.05, 46.05], "bera": "MONT-BLANC"}
}

class AnalysisWorker(QThread):
    finished = Signal(list, dict, float, dict)

    def __init__(self, massif_key: str, activity_key: str):
        super().__init__()
        self.massif = MASSIFS[massif_key]
        self.activity = activity_key

    def run(self):
        bbox = self.massif["bbox"]
        center = self.massif["center"]

        weather = get_recent_weather(center[0], center[1])
        snow_pct = analyze_snow_coverage(bbox)
        bera = get_avalanche_risk(self.massif["bera"])
        raw_routes = search_routes(bbox, activity=self.activity)

        athlete = WorkloadEngine.get_athlete_readiness()
        readiness = athlete["readiness"]

        evaluated_routes = []
        for r in raw_routes:
            analysis = FeasibilityEngine.evaluate(r, weather, snow_pct, bera, self.activity, user_readiness=readiness)
            r["eval"] = analysis
            evaluated_routes.append(r)

        self.finished.emit(evaluated_routes, weather, snow_pct, bera)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mountain Scout — Décision Tactique, Satellite & Physiologie")
        self.resize(1440, 920)
        self.routes = []
        self.active_index = -1

        self._setup_tabs()
        self.launch_analysis()

    def _setup_tabs(self):
        self.tab_widget = QTabWidget()

        self.tab_explore = QWidget()
        self._setup_explore_ui(self.tab_explore)
        self.tab_widget.addTab(self.tab_explore, "🧭 Exploration & Décision Tactique")

        self.tab_training = TrainingView()
        self.tab_training.activity_imported.connect(self.launch_analysis)
        self.tab_widget.addTab(self.tab_training, "📈 Mon Entraînement & VFC")

        self.setCentralWidget(self.tab_widget)

    def _setup_explore_ui(self, parent_widget):
        main_layout = QVBoxLayout(parent_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)

        left_layout.addWidget(QLabel("<b>Zone / Massif :</b>"))
        self.combo_massif = QComboBox()
        self.combo_massif.addItems(list(MASSIFS.keys()))
        left_layout.addWidget(self.combo_massif)

        left_layout.addWidget(QLabel("<b>Discipline :</b>"))
        self.combo_activity = QComboBox()
        self.combo_activity.addItems(["Trail / Randonnée", "Ski de Randonnée"])
        left_layout.addWidget(self.combo_activity)

        self.btn_scan = QPushButton("Actualiser le secteur")
        self.btn_scan.clicked.connect(self.launch_analysis)
        left_layout.addWidget(self.btn_scan)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        left_layout.addWidget(self.progress)

        left_layout.addWidget(QLabel("<b>Itinéraires Découverts :</b>"))
        self.list_routes = QListWidget()
        self.list_routes.currentRowChanged.connect(self.on_route_selected)
        left_layout.addWidget(self.list_routes)

        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(8, 8, 8, 8)

        self.browser = QTextBrowser()
        self.browser.document().setDefaultFont(QFont("Segoe UI", 10))
        self.browser.setOpenExternalLinks(False)
        self.browser.anchorClicked.connect(lambda url: QDesktopServices.openUrl(url))
        center_layout.addWidget(self.browser, stretch=2)

        center_layout.addWidget(QLabel("<b>Profil Altimétrique :</b>"))
        self.elevation_chart = ElevationChart()
        center_layout.addWidget(self.elevation_chart, stretch=1)

        btn_box = QHBoxLayout()
        self.btn_open_web = QPushButton("🌐 Fiche Web")
        self.btn_open_web.setEnabled(False)
        self.btn_open_web.clicked.connect(self.open_current_web_page)
        btn_box.addWidget(self.btn_open_web)

        self.btn_export = QPushButton("📥 EXPORTER LE GPX")
        self.btn_export.setEnabled(False)
        self.btn_export.setStyleSheet("background-color: #2E7D32; font-weight: bold;")
        self.btn_export.clicked.connect(self.export_current_gpx)
        btn_box.addWidget(self.btn_export)
        center_layout.addLayout(btn_box)

        self.map_view = MapView()

        splitter.addWidget(left_panel)
        splitter.addWidget(center_panel)
        splitter.addWidget(self.map_view)
        splitter.setSizes([300, 480, 640])

        main_layout.addWidget(splitter)

    def launch_analysis(self):
        # 1. Si une analyse est déjà en cours, on ne l'écrase pas en mémoire
        if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
            print("[Warning] Une analyse est déjà en cours d'exécution.")
            return

        self.btn_scan.setEnabled(False)
        self.progress.setVisible(True)
        self.list_routes.clear()

        massif_key = self.combo_massif.currentText()
        act_key = "trail" if self.combo_activity.currentIndex() == 0 else "skitouring"

        self.worker = AnalysisWorker(massif_key, act_key)
        self.worker.finished.connect(self.on_analysis_finished)
        self.worker.start()

    def closeEvent(self, event):
        """Arrêt ordonné de tous les processus avant destruction des fenêtres Qt."""
        # Arrêt du scanner USB
        if hasattr(self, 'tab_training') and hasattr(self.tab_training, 'usb_thread'):
            self.tab_training.usb_thread.stop()

        # Attente de l'analyseur si actif
        if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(2000)

        event.accept()

    def on_analysis_finished(self, routes, weather, snow_pct, bera):
        self.btn_scan.setEnabled(True)
        self.progress.setVisible(False)
        self.routes = routes
        self.list_routes.clear()

        if not routes:
            self.browser.setHtml("<h3 style='color:#E53E3E;'>Aucun itinéraire trouvé sur ce secteur.</h3>")
            return

        for r in routes:
            ev = r.get("eval", {})
            score = ev.get("score", 70)
            status = ev.get("status", "Non évalué")
            item = QListWidgetItem(f"{r['title']}\nIndice : {score}/100 — {status}")
            self.list_routes.addItem(item)

        self.list_routes.setCurrentRow(0)

    def on_route_selected(self, index):
        if index < 0 or index >= len(self.routes):
            return

        self.active_index = index
        self.btn_export.setEnabled(True)
        self.btn_open_web.setEnabled(True)

        r = self.routes[index]
        ev = r["eval"]
        slope = ev.get("slope_metrics", {})
        coords = r.get("coords", [])
        elevations = r.get("elevations", [])

        self.elevation_chart.plot_profile(coords, elevations, r["title"])

        # Calcul de la simulation pré-course 'What-If'
        d_plus = r.get("elevation_gain", 800)
        dist_km = (len(coords) * 50.0) / 1000.0  # Estimation approximative si non renseignée
        sim = WorkloadEngine.simulate_route_impact(d_plus, dist_km)

        alerts_html = "".join([f"<li style='color:#F6AD55;'><b>{a}</b></li>" for a in ev["alerts"]])
        if not alerts_html:
            alerts_html = "<li style='color:#68D391;'>Aucun facteur critique de blocage.</li>"

        source_url = r.get("source_url", "https://www.camptocamp.org")

        html = f"""
        <h2 style='color:#4FD1C5; margin-top:0;'>{r['title']}</h2>
        <p><b>Difficulté :</b> {r['rating']} | <b>Source :</b> <a href="{source_url}" style="color:#63B3ED;">Consulter le topo</a></p>
        
        <div style='background:{ev['color']}; padding:8px 12px; border-radius:5px; color:#FFFFFF; font-weight:bold;'>
            Score de faisabilité personnalisé : {ev['score']} / 100 ({ev['status']})
        </div>

        <h3>Simulation Pré-Course (What-If) :</h3>
        <div style='background:#242933; border-left:4px solid {sim['advice_color']}; padding:10px; border-radius:4px;'>
            <p style='margin:0;'><b>Durée estimée :</b> {sim['duration_str']} | <b>Charge projetée (TRIMP) :</b> +{sim['projected_trimp']}</p>
            <p style='margin:4px 0 0 0;'><b>Évolution ACWR :</b> {sim['current_acwr']} ➔ <b>{sim['new_acwr']}</b></p>
            <p style='margin:4px 0 0 0; color:{sim['advice_color']};'><b>Verdict :</b> {sim['advice']}</p>
        </div>

        <h3>Dénivelé & Pentes :</h3>
        <table style='width:100%; border-collapse:collapse; color:#E2E8F0;'>
            <tr><td>⬆️ <b>Dénivelé positif (D+) :</b></td><td>+{r.get('elevation_gain', 0)} m</td></tr>
            <tr><td>⬇️ <b>Dénivelé négatif (D-) :</b></td><td>-{r.get('elevation_loss', 0)} m</td></tr>
            <tr><td>🔺 <b>Altitude max :</b></td><td>{r.get('elevation_max', 0)} m</td></tr>
            <tr><td>🔻 <b>Altitude min :</b></td><td>{r.get('elevation_min', 0)} m</td></tr>
            <tr><td>📐 <b>Pente moyenne :</b></td><td>{slope.get('avg_slope_deg', 0)}° (Max: {slope.get('max_slope_deg', 0)}°)</td></tr>
        </table>

        <h3>Points d'attention (Terrain & Forme) :</h3>
        <ul>{alerts_html}</ul>

        <h3>Description :</h3>
        <p style='color:#CBD5E0; line-height:1.4;'>{r['summary']}</p>
        """
        self.browser.setHtml(html)

        center = MASSIFS[self.combo_massif.currentText()]["center"]
        self.map_view.render_routes_map(center, self.routes, active_route_id=r["id"])

    def open_current_web_page(self):
        if self.active_index >= 0:
            url = self.routes[self.active_index].get("source_url")
            if url:
                QDesktopServices.openUrl(QUrl(url))

    def export_current_gpx(self):
        if self.active_index < 0:
            return

        route = self.routes[self.active_index]
        clean_title = re.sub(r'[^a-zA-Z0-9_\- ]', '', route['title']).strip().replace(' ', '_').lower()
        file_path, _ = QFileDialog.getSaveFileName(self, "Exporter la trace GPX", f"{clean_title}.gpx", "Fichier GPX (*.gpx)")
        if not file_path:
            return

        coords = route.get("coords", [])
        elevations = route.get("elevations", [0] * len(coords))
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<gpx version="1.1" creator="MountainScout" xmlns="http://www.topografix.com/GPX/1/1">\n')
            f.write('  <metadata>\n')
            f.write(f'    <name>{route["title"]}</name>\n')
            f.write(f'    <time>{timestamp}</time>\n')
            f.write('  </metadata>\n')
            f.write('  <trk>\n')
            f.write(f'    <name>{route["title"]}</name>\n')
            f.write('    <trkseg>\n')
            for i, pt in enumerate(coords):
                ele = elevations[i] if i < len(elevations) else 0.0
                f.write(f'      <trkpt lat="{pt[0]}" lon="{pt[1]}"><ele>{ele:.1f}</ele></trkpt>\n')
            f.write('    </trkseg>\n  </trk>\n</gpx>')

        QMessageBox.information(self, "Export GPX réussi", f"Fichier GPX enregistré :\n{file_path}")