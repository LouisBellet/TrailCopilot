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
from core.data_manager import DataManager
from ui.map_view import MapView
from ui.elevation_chart import ElevationChart
from ui.home_view import HomeView
from ui.training_view import TrainingView
from ui.health_profile_view import HealthProfileView

MASSIFS = {
    "Pyrénées — Gavarnie & Vignemale": {"center": [42.7290, -0.0450], "bbox": [-0.30, 42.60, 0.15, 42.85], "bera": "HAUTE-BIGORRE"},
    "Pyrénées — Néouvielle & Lacs": {"center": [42.8350, 0.1420], "bbox": [0.02, 42.72, 0.28, 42.92], "bera": "HAUTE-BIGORRE"},
    "Pyrénées — Vallée d'Ossau & Ayous": {"center": [42.8420, -0.4350], "bbox": [-0.60, 42.72, -0.30, 42.95], "bera": "ASPE-OSSAU"},
    "Pyrénées — Cauterets & Gaube": {"center": [42.8550, -0.1150], "bbox": [-0.25, 42.72, 0.00, 42.94], "bera": "HAUTE-BIGORRE"},
    "Pyrénées — Luchonnais & Vénasque": {"center": [42.7200, 0.5850], "bbox": [0.40, 42.60, 0.75, 42.85], "bera": "LUCHONNAIS"},
    "Pyrénées — Carlit & Bouillouses": {"center": [42.5700, 1.9900], "bbox": [1.80, 42.48, 2.15, 42.68], "bera": "CERDAGNE-CANIGOU"},
    "Pyrénées — Massif du Canigou": {"center": [42.5180, 2.4560], "bbox": [2.30, 42.40, 2.60, 42.62], "bera": "CERDAGNE-CANIGOU"},
    "Alpes — Mont-Blanc": {"center": [45.8600, 6.7400], "bbox": [6.60, 45.75, 7.15, 46.10], "bera": "MONT-BLANC"}
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

        athlete = DataManager.get_readiness()
        readiness = athlete.get("readiness", 1.0)

        evaluated_routes = []
        for r in raw_routes:
            analysis = FeasibilityEngine.evaluate(r, weather, snow_pct, bera, self.activity, user_readiness=readiness)
            r["eval"] = analysis
            evaluated_routes.append(r)

        self.finished.emit(evaluated_routes, weather, snow_pct, bera)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mountain Scout — Décision Tactique & Charge Scientifique")
        self.resize(1460, 930)
        self.routes = []
        self.active_index = -1
        self.worker = None

        self._setup_tabs()

    def _setup_tabs(self):
        self.tab_widget = QTabWidget()

        self.tab_home = HomeView()
        self.tab_widget.addTab(self.tab_home, "🏠 Accueil & Synthèse")

        self.tab_training = TrainingView()
        self.tab_widget.addTab(self.tab_training, "📈 Entraînement")

        self.tab_coach = HealthProfileView()
        self.tab_widget.addTab(self.tab_coach, "🎯 Conseiller & Profil")

        self.tab_explore = QWidget()
        self._setup_explore_ui(self.tab_explore)
        self.tab_widget.addTab(self.tab_explore, "🧭 Exploration Tactique")

        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.tab_training.activity_imported.connect(self.on_data_updated)
        self.tab_coach.profile_updated.connect(self.on_data_updated)

        self.setCentralWidget(self.tab_widget)

    def on_tab_changed(self, index: int):
        if index == 0:
            if DataManager.is_tab_dirty(0):
                self.tab_home.refresh_dashboard()
                DataManager.mark_tab_clean(0)
        elif index == 1:
            self.tab_training.ensure_loaded()
        elif index == 2:
            self.tab_coach.ensure_loaded()
        elif index == 3:
            if not self.routes and (self.worker is None or not self.worker.isRunning()):
                self.launch_analysis()

    def on_data_updated(self):
        DataManager.invalidate_cache()
        curr = self.tab_widget.currentIndex()
        if curr == 0:
            self.tab_home.refresh_dashboard()
            DataManager.mark_tab_clean(0)
        elif curr == 1:
            self.tab_training.refresh_data()
            DataManager.mark_tab_clean(1)
        elif curr == 2:
            self.tab_coach.refresh_coach_view()
            DataManager.mark_tab_clean(2)

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

        self.btn_scan = QPushButton("Actualiser le secteur (C2C Direct)")
        self.btn_scan.clicked.connect(self.launch_analysis)
        left_layout.addWidget(self.btn_scan)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        left_layout.addWidget(self.progress)

        left_layout.addWidget(QLabel("<b>Itinéraires Camptocamp :</b>"))
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

        center_layout.addWidget(QLabel("<b>Profil Altimétrique & Segments Critiques :</b>"))
        self.elevation_chart = ElevationChart()
        center_layout.addWidget(self.elevation_chart, stretch=1)

        btn_box = QHBoxLayout()
        self.btn_open_web = QPushButton("🌐 Ouvrir sur Camptocamp")
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
        splitter.setSizes([300, 480, 680])

        main_layout.addWidget(splitter)
        self.browser.setHtml("<h3 style='color:#A0AEC0;'>Sélectionnez un massif et cliquez sur 'Actualiser le secteur' pour interroger l'API Camptocamp en direct.</h3>")

    def launch_analysis(self):
        if self.worker is not None and self.worker.isRunning():
            return

        self.btn_scan.setEnabled(False)
        self.progress.setVisible(True)
        self.list_routes.clear()
        self.browser.setHtml("<h3 style='color:#4FD1C5;'>Interrogation directe de l'API Camptocamp en cours...</h3>")

        massif_key = self.combo_massif.currentText()
        act_key = "trail" if self.combo_activity.currentIndex() == 0 else "skitouring"

        self.worker = AnalysisWorker(massif_key, act_key)
        self.worker.finished.connect(self.on_analysis_finished)
        self.worker.start()

    def on_analysis_finished(self, routes, weather, snow_pct, bera):
        self.btn_scan.setEnabled(True)
        self.progress.setVisible(False)
        self.routes = routes
        self.list_routes.clear()

        if not routes:
            self.browser.setHtml("<h3 style='color:#E53E3E;'>Aucun itinéraire trouvé sur Camptocamp pour ce secteur.</h3>")
            return

        for r in routes:
            ev = r.get("eval", {})
            score = ev.get("score", 70)
            status = ev.get("status", "Non évalué")
            track_tag = "🗺️ [TRACÉ GPS]" if r.get("has_track") else "📍 [TOPO SEUL]"
            item = QListWidgetItem(f"{track_tag} {r['title']}\nIndice : {score}/100 — {status}")
            if not r.get("has_track"):
                item.setForeground(Qt.gray)
            self.list_routes.addItem(item)

        self.list_routes.setCurrentRow(0)

    def on_route_selected(self, index):
        if index < 0 or index >= len(self.routes):
            return

        self.active_index = index
        r = self.routes[index]
        has_track = r.get("has_track", False)

        # Le bouton d'export GPX n'est actif que si une vraie trace existe
        self.btn_export.setEnabled(has_track)
        self.btn_open_web.setEnabled(True)

        ev = r.get("eval", {})
        slope = ev.get("slope_metrics", {})
        coords = r.get("coords", [])
        elevations = r.get("elevations", [])
        crit_segs = ev.get("critical_segments", [])

        # Rendu du profil altimétrique
        self.elevation_chart.plot_profile(
            coords, elevations, r["title"],
            critical_segments=crit_segs,
            has_track=has_track
        )

        d_plus = r.get("elevation_gain", 800)
        dist_km = (len(coords) * 50.0) / 1000.0 if has_track else (d_plus / 100.0 * 0.7)
        sim = WorkloadEngine.simulate_route_impact(d_plus, dist_km)

        # Bannière d'état de la trace
        if has_track:
            track_banner = """
            <div style='background:#1D2B24; border-left:4px solid #38A169; padding:6px 12px; margin-bottom:8px; border-radius:4px;'>
                <span style='color:#68D391; font-size:12px;'>🗺️ <b>Tracé GPS complet disponible</b> — Profil altimétrique et analyse de pente actifs.</span>
            </div>
            """
        else:
            track_banner = """
            <div style='background:#3D321D; border-left:4px solid #ECC94B; padding:6px 12px; margin-bottom:8px; border-radius:4px;'>
                <span style='color:#F6E05E; font-size:12px;'>📍 <b>Trace GPS non disponible sur C2C</b> — Fiche descriptive basée sur les données d'altitude. Export GPX désactivé.</span>
            </div>
            """

        # Encart des tronçons critiques
        if crit_segs:
            crit_html_list = "".join([
                f"<li style='color:#FF5252;'><b>Du km {s['start_km']} au km {s['end_km']} :</b> {s['reason']}</li>"
                for s in crit_segs
            ])
            crit_section = f"""
            <div style='background:#3A1D1D; border-left:4px solid #FF1744; padding:8px 12px; margin:8px 0; border-radius:4px;'>
                <h4 style='margin:0 0 4px 0; color:#FF8A80;'>⚠️ Tronçons Délicats Détectés (Météo / Pente) :</h4>
                <ul style='margin:0; padding-left:18px;'>{crit_html_list}</ul>
            </div>
            """
        else:
            crit_section = ""

        alerts_html = "".join([f"<li style='color:#F6AD55;'><b>{a}</b></li>" for a in ev.get("alerts", [])])
        if not alerts_html:
            alerts_html = "<li style='color:#68D391;'>Facteurs environnementaux favorables.</li>"

        source_url = r.get("source_url", "https://www.camptocamp.org")

        html = f"""
        <h2 style='color:#4FD1C5; margin-top:0;'>{r['title']}</h2>
        <p><b>Cotation :</b> {r['rating']} | <b>Source :</b> <a href="{source_url}" style="color:#63B3ED;">Fiche Camptocamp</a></p>
        
        {track_banner}

        <div style='background:{ev.get('color', '#38A169')}; padding:8px 12px; border-radius:5px; color:#FFFFFF; font-weight:bold;'>
            Score de faisabilité : {ev.get('score', 80)} / 100 ({ev.get('status', 'OK')})
        </div>

        {crit_section}

        <h3>Simulation de Charge (What-If) :</h3>
        <div style='background:#242933; border-left:4px solid {sim['advice_color']}; padding:10px; border-radius:4px;'>
            <p style='margin:0;'><b>Durée estimée :</b> ~{sim['duration_str']} | <b>Charge (TRIMP) :</b> +{sim['projected_trimp']}</p>
            <p style='margin:4px 0 0 0;'><b>Évolution ACWR :</b> {sim['current_acwr']} ➔ <b>{sim['new_acwr']}</b></p>
            <p style='margin:4px 0 0 0; color:{sim['advice_color']};'><b>Verdict :</b> {sim['advice']}</p>
        </div>

        <h3>Dénivelé & Altitude :</h3>
        <table style='width:100%; border-collapse:collapse; color:#E2E8F0;'>
            <tr><td>⬆️ <b>Dénivelé positif (D+) :</b></td><td>+{r.get('elevation_gain', 0)} m</td></tr>
            <tr><td>⬇️ <b>Dénivelé négatif (D-) :</b></td><td>-{r.get('elevation_loss', 0)} m</td></tr>
            <tr><td>🔺 <b>Altitude max :</b></td><td>{r.get('elevation_max', 0)} m</td></tr>
            <tr><td>🔻 <b>Altitude min :</b></td><td>{r.get('elevation_min', 0)} m</td></tr>
        </table>

        <h3>Points d'attention :</h3>
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

    def closeEvent(self, event):
        if hasattr(self, 'tab_training') and hasattr(self.tab_training, 'usb_thread'):
            self.tab_training.usb_thread.stop()
        if self.worker is not None and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(2000)
        event.accept()