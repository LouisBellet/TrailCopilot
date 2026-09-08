import os
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QFileDialog, QHeaderView,
    QSplitter, QMessageBox, QGroupBox, QDoubleSpinBox, QSpinBox
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from core.fit_parser import parse_fit_file
from core.training_db import (
    save_activity, get_all_activities, get_activity_details,
    save_daily_health, get_health_baselines
)
from core.workload_engine import WorkloadEngine
from core.device_sync import scan_connected_watches
from ui.workload_chart import WorkloadGaugeChart


class USBWatcherThread(QThread):
    """Surveille le branchement USB avec interruption réactive instantanée."""
    watch_synced = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True

    def run(self):
        while self.running:
            result = scan_connected_watches()
            if result["brand"] and result["imported"] > 0:
                self.watch_synced.emit(result["brand"], result["imported"])
            
            for _ in range(40):
                if not self.running:
                    return
                self.msleep(100)

    def stop(self):
        self.running = False
        self.quit()
        self.wait(2000) 


class TrainingView(QWidget):
    activity_imported = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self._init_ui()
        self.refresh_data()

        # Démarrage de la surveillance USB automatique
        self.usb_thread = USBWatcherThread(self)
        self.usb_thread.watch_synced.connect(self.on_usb_synced)
        self.usb_thread.start()

    def _init_ui(self):
        # 1. Bilan matinal & VFC
        top_bar = QHBoxLayout()
        self.group_health = QGroupBox("Bilan Matinal & VFC (Aujourd'hui)")
        h_layout = QHBoxLayout(self.group_health)

        h_layout.addWidget(QLabel("FC Repos :"))
        self.spin_rhr = QSpinBox()
        self.spin_rhr.setRange(30, 100)
        self.spin_rhr.setValue(48)
        h_layout.addWidget(self.spin_rhr)

        h_layout.addWidget(QLabel("VFC (rMSSD ms) :"))
        self.spin_vfc = QDoubleSpinBox()
        self.spin_vfc.setRange(10.0, 200.0)
        self.spin_vfc.setValue(65.0)
        h_layout.addWidget(self.spin_vfc)

        h_layout.addWidget(QLabel("Sommeil (h) :"))
        self.spin_sleep = QDoubleSpinBox()
        self.spin_sleep.setRange(2.0, 14.0)
        self.spin_sleep.setSingleStep(0.5)
        self.spin_sleep.setValue(7.5)
        h_layout.addWidget(self.spin_sleep)

        self.btn_save_health = QPushButton("Enregistrer")
        self.btn_save_health.clicked.connect(self.save_morning_health)
        h_layout.addWidget(self.btn_save_health)

        self.lbl_recovery_badge = QLabel("<b>Récupération : 85%</b>")
        self.lbl_recovery_badge.setStyleSheet("color: #38A169; font-size: 13px; padding-left: 10px;")
        h_layout.addWidget(self.lbl_recovery_badge)

        top_bar.addWidget(self.group_health)
        self.layout.addLayout(top_bar)

        # 2. Graphique dynamique ACWR à zones bornées
        self.acwr_chart = WorkloadGaugeChart()
        self.layout.addWidget(self.acwr_chart)

        # 3. Barre d'outils d'importation
        btn_bar = QHBoxLayout()
        
        self.btn_manual_usb = QPushButton("🔄 Scanner USB (Garmin / Coros)")
        self.btn_manual_usb.setStyleSheet("background-color: #2B6CB0; font-weight: bold;")
        self.btn_manual_usb.clicked.connect(self.trigger_manual_usb_scan)
        btn_bar.addWidget(self.btn_manual_usb)

        self.btn_import_file = QPushButton("📁 Fichier .FIT...")
        self.btn_import_file.clicked.connect(self.import_single_fit)
        btn_bar.addWidget(self.btn_import_file)

        self.btn_import_dir = QPushButton("📂 Dossier .FIT...")
        self.btn_import_dir.clicked.connect(self.import_folder_fit)
        btn_bar.addWidget(self.btn_import_dir)

        self.lbl_usb_status = QLabel("<span style='color:#718096;'>Auto-sync USB active (veille)</span>")
        btn_bar.addWidget(self.lbl_usb_status)

        btn_bar.addStretch()
        self.layout.addLayout(btn_bar)

        # 4. Séparateur vertical : Historique des séances et courbes de la séance
        splitter = QSplitter(Qt.Vertical)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Date", "Nom de l'Activité", "Sport", "Distance", "D+", "D-", "FC Moy", "TRIMP"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemSelectionChanged.connect(self.on_activity_selected)
        splitter.addWidget(self.table)

        self.fig = Figure(figsize=(8, 3.2), facecolor="#1F242D")
        self.canvas = FigureCanvas(self.fig)
        self.ax_alt = self.fig.add_subplot(111)
        self.ax_hr = self.ax_alt.twinx()
        splitter.addWidget(self.canvas)

        splitter.setSizes([220, 320])
        self.layout.addWidget(splitter)

    def trigger_manual_usb_scan(self):
        """Déclenche une recherche manuelle immédiate des montres branchées."""
        result = scan_connected_watches()
        brand = result["brand"]
        imported = result["imported"]
        skipped = result["skipped"]

        if brand:
            if imported > 0:
                QMessageBox.information(
                    self, "Synchronisation Réussie",
                    f"Montre <b>{brand}</b> détectée !<br>{imported} nouvelle(s) activité(s) importée(s)."
                )
                self.refresh_data()
                self.activity_imported.emit()
            else:
                QMessageBox.information(
                    self, "Montre à jour",
                    f"Montre <b>{brand}</b> détectée.<br>Toutes les activités ({skipped}) sont déjà importées."
                )
        else:
            QMessageBox.warning(
                self, "Aucune montre détectée",
                "Aucun stockage Garmin ou Coros trouvé.<br>Assurez-vous que la montre est bien allumée et connectée en mode transfert de données (MTP / Stockage de masse)."
            )

    def on_usb_synced(self, brand: str, count: int):
        """Appelé automatiquement par le thread d'arrière-plan dès le branchement d'une montre."""
        self.lbl_usb_status.setText(f"<span style='color:#38A169;'>Dernière synchro : {brand} (+{count} sorties)</span>")
        QMessageBox.information(
            self, "Synchronisation Automatique",
            f"Montre <b>{brand}</b> branchée !<br><b>{count}</b> nouvelle(s) sortie(s) importée(s) automatiquement."
        )
        self.refresh_data()
        self.activity_imported.emit()

    def save_morning_health(self):
        rhr = self.spin_rhr.value()
        vfc = self.spin_vfc.value()
        sleep = self.spin_sleep.value()
        today_str = datetime.now().strftime("%Y-%m-%d")

        baselines = get_health_baselines()
        b_rhr = baselines["baseline_rhr"]
        b_vfc = baselines["baseline_rmssd"]

        score = 80
        if vfc < b_vfc * 0.85:
            score -= 25
        elif vfc >= b_vfc:
            score += 10

        if rhr >= b_rhr + 5:
            score -= 20
        elif rhr <= b_rhr:
            score += 5

        if sleep < 6.0:
            score -= 20
        elif sleep >= 7.5:
            score += 10

        score = max(10, min(100, score))
        save_daily_health(today_str, rhr, vfc, sleep, score)

        QMessageBox.information(self, "Santé mise à jour", f"Indice de récupération calculé : {score}/100")
        self.refresh_data()
        self.activity_imported.emit()

    def refresh_data(self):
        form = WorkloadEngine.get_athlete_readiness()
        self.acwr_chart.plot_acwr_timeline(
            form["timeline_days"], form["timeline_acwr"], form["acwr"]
        )

        rec_color = "#38A169" if form["recovery_score"] >= 75 else ("#DD6B20" if form["recovery_score"] >= 55 else "#E53E3E")
        self.lbl_recovery_badge.setText(f"<b>Récupération : {form['recovery_score']}%</b>")
        self.lbl_recovery_badge.setStyleSheet(f"color: {rec_color}; font-size: 13px; font-weight: bold; padding-left: 10px;")

        activities = get_all_activities()
        self.table.setRowCount(len(activities))

        for row, a in enumerate(activities):
            self.table.setItem(row, 0, QTableWidgetItem(str(a["start_time"][:10])))
            self.table.setItem(row, 1, QTableWidgetItem(str(a["name"])))
            self.table.setItem(row, 2, QTableWidgetItem(str(a["sport"])))
            self.table.setItem(row, 3, QTableWidgetItem(f"{a['distance_km']} km"))
            self.table.setItem(row, 4, QTableWidgetItem(f"+{int(a['d_plus'])} m"))
            self.table.setItem(row, 5, QTableWidgetItem(f"-{int(a['d_minus'])} m"))
            self.table.setItem(row, 6, QTableWidgetItem(f"{a['avg_hr']} bpm"))
            self.table.setItem(row, 7, QTableWidgetItem(str(a["trimp"])))
            self.table.item(row, 0).setData(Qt.UserRole, a["id"])

        if activities:
            self.table.selectRow(0)

    def import_single_fit(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier FIT", "", "FIT Files (*.fit *.FIT)")
        if file_path:
            try:
                data = parse_fit_file(file_path)
                save_activity(data)
                QMessageBox.information(self, "Import réussi", f"Activité enregistrée :\n{data['name']}")
                self.refresh_data()
                self.activity_imported.emit()
            except Exception as e:
                QMessageBox.critical(self, "Erreur d'import", f"Impossible de lire le fichier FIT :\n{e}")

    def import_folder_fit(self):
        folder = QFileDialog.getExistingDirectory(self, "Choisir un dossier de fichiers FIT")
        if folder:
            count = 0
            for fname in os.listdir(folder):
                if fname.lower().endswith(".fit"):
                    full_path = os.path.join(folder, fname)
                    try:
                        data = parse_fit_file(full_path)
                        save_activity(data)
                        count += 1
                    except Exception:
                        pass
            QMessageBox.information(self, "Import groupé", f"{count} fichier(s) FIT importé(s) avec succès !")
            self.refresh_data()
            self.activity_imported.emit()

    def on_activity_selected(self):
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return

        act_id = self.table.item(selected_rows[0].row(), 0).data(Qt.UserRole)
        act = get_activity_details(act_id)
        records = act.get("records", [])

        self.ax_alt.clear()
        self.ax_hr.clear()
        self.ax_alt.set_facecolor("#16191E")

        if not records:
            self.canvas.draw()
            return

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
            self.ax_alt.plot(distances, clean_alts, color="#38B2AC", linewidth=2, label="Altitude (m)")
            self.ax_alt.fill_between(distances, clean_alts, min(valid_alts) - 20, color="#38B2AC", alpha=0.25)
            self.ax_alt.set_ylabel("Altitude (m)", color="#38B2AC")
            self.ax_alt.set_ylim(bottom=max(0, min(valid_alts) - 50))

        valid_hrs = [h for h in hrs if h is not None]
        if valid_hrs:
            clean_hrs = [h if h is not None else min(valid_hrs) for h in hrs]
            self.ax_hr.plot(distances, clean_hrs, color="#FC8181", linewidth=1.5, linestyle="--", label="FC (bpm)")
            self.ax_hr.set_ylabel("Fréquence Cardiaque (bpm)", color="#FC8181")
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
        self.canvas.draw()

    def closeEvent(self, event):
        """Arrête le thread USB proprement lors de la fermeture de la vue."""
        if hasattr(self, 'usb_thread') and self.usb_thread.isRunning():
            self.usb_thread.stop()
        super().closeEvent(event)