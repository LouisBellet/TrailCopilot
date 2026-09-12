import os
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QFileDialog, QHeaderView,
    QMessageBox, QDateEdit, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox
)
from core.fit_parser import parse_fit_file, calculate_banister_trimp
from core.training_db import (
    save_activity, get_all_activities, get_activity_details,
    get_user_profile
)
from core.workload_engine import WorkloadEngine
from core.device_sync import scan_connected_watches
from core.excel_importer import import_workouts_from_excel
from ui.workload_chart import WorkloadGaugeChart
from ui.workout_detail_dialog import WorkoutDetailDialog

BORG_LABELS = {
    6: "6 - Aucun effort", 7: "7 - Extrêmement léger", 8: "8",
    9: "9 - Très léger", 10: "10", 11: "11 - Léger", 12: "12",
    13: "13 - Un peu dur (Z2/Z3)", 14: "14", 15: "15 - Dur / Lourd (Z4)",
    16: "16", 17: "17 - Très dur (Seuil)", 18: "18",
    19: "19 - Extrêmement dur", 20: "20 - Maximal absolu"
}

class USBWatcherThread(QThread):
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

        self.usb_thread = USBWatcherThread(self)
        self.usb_thread.watch_synced.connect(self.on_usb_synced)
        self.usb_thread.start()

    def _init_ui(self):
        # Moitié supérieure : 3 graphiques scientifiques
        self.acwr_chart = WorkloadGaugeChart()
        self.layout.addWidget(self.acwr_chart, stretch=1)

        btn_bar = QHBoxLayout()
        self.btn_import_excel = QPushButton("📊 Importer Excel (.xlsx)")
        self.btn_import_excel.setStyleSheet("background-color: #319795; font-weight: bold;")
        self.btn_import_excel.clicked.connect(self.import_excel_file)
        btn_bar.addWidget(self.btn_import_excel)

        self.btn_import_file = QPushButton("📁 Importer .FIT...")
        self.btn_import_file.clicked.connect(self.import_fit_files)
        btn_bar.addWidget(self.btn_import_file)

        self.btn_manual_usb = QPushButton("🔄 Scanner USB Montre")
        self.btn_manual_usb.clicked.connect(self.trigger_manual_usb_scan)
        btn_bar.addWidget(self.btn_manual_usb)

        self.lbl_usb_status = QLabel("<span style='color:#718096;'>Auto-sync USB active</span>")
        btn_bar.addWidget(self.lbl_usb_status)
        btn_bar.addStretch()
        self.layout.addLayout(btn_bar)

        # Moitié inférieure : tableau avec ligne de saisie directe Borg 6-20
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Date", "Sport", "Titre / Lieu", "Durée (min)", "Distance (km)", "D+ (m)", "D- (m)", "FC Moy", "Borg RPE (6-20)", "Action"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.layout.addWidget(self.table, stretch=1)

    def trigger_manual_usb_scan(self):
        res = scan_connected_watches()
        if res["brand"]:
            if res["imported"] > 0:
                QMessageBox.information(self, "USB Détecté", f"Montre <b>{res['brand']}</b> synchronisée : {res['imported']} sortie(s) importée(s).")
                self.refresh_data()
                self.activity_imported.emit()
            else:
                QMessageBox.information(self, "USB Détecté", f"Montre <b>{res['brand']}</b> déjà à jour.")
        else:
            QMessageBox.warning(self, "Aucune Montre", "Aucun volume Garmin ou Coros détecté.")

    def on_usb_synced(self, brand: str, count: int):
        self.lbl_usb_status.setText(f"<span style='color:#38A169;'>Synchro auto : {brand} (+{count})</span>")
        self.refresh_data()
        self.activity_imported.emit()

    def import_fit_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Sélectionner des fichiers FIT", "", "FIT Files (*.fit *.FIT)")
        if file_paths:
            imported = sum(1 for p in file_paths if save_activity(parse_fit_file(p)))
            self.refresh_data()
            self.activity_imported.emit()
            QMessageBox.information(self, "Importation", f"{imported} fichier(s) FIT importé(s) avec succès.")

    def import_excel_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Importer Excel", "", "Excel Files (*.xlsx)")
        if file_path:
            res = import_workouts_from_excel(file_path)
            if not res.get("error"):
                QMessageBox.information(self, "Import Excel", f"{res['imported']} sortie(s) importée(s).")
                self.refresh_data()
                self.activity_imported.emit()

    def refresh_data(self):
        readiness = WorkloadEngine.get_athlete_readiness()
        self.acwr_chart.plot_all_indicators(readiness)

        activities = get_all_activities()
        self.table.setRowCount(len(activities) + 1)
        self._setup_input_row()

        for idx, a in enumerate(activities, start=1):
            self.table.setCellWidget(idx, 0, None)
            self.table.setItem(idx, 0, QTableWidgetItem(str(a["start_time"][:10])))
            self.table.setItem(idx, 1, QTableWidgetItem(str(a["sport"])))
            self.table.setItem(idx, 2, QTableWidgetItem(str(a["name"])))
            self.table.setItem(idx, 3, QTableWidgetItem(f"{a['duration_min']} min"))
            self.table.setItem(idx, 4, QTableWidgetItem(f"{a['distance_km']} km"))
            self.table.setItem(idx, 5, QTableWidgetItem(f"+{int(a['d_plus'])} m"))
            self.table.setItem(idx, 6, QTableWidgetItem(f"-{int(a['d_minus'])} m"))
            self.table.setItem(idx, 7, QTableWidgetItem(f"{a['avg_hr']} bpm" if a['avg_hr'] else "-"))
            
            raw_trimp = a.get("trimp", 0)
            self.table.setItem(idx, 8, QTableWidgetItem(f"TRIMP {raw_trimp}"))

            btn_det = QPushButton("🔍 Détails")
            btn_det.setStyleSheet("background-color: #2D3748; padding: 4px 8px; font-size: 11px;")
            act_id = a["id"]
            btn_det.clicked.connect(lambda _, aid=act_id: self.open_activity_details(aid))
            self.table.setCellWidget(idx, 9, btn_det)

        self.table.setColumnWidth(0, 105)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 220)
        self.table.setColumnWidth(3, 85)
        self.table.setColumnWidth(4, 95)
        self.table.setColumnWidth(5, 75)
        self.table.setColumnWidth(6, 75)
        self.table.setColumnWidth(7, 85)
        self.table.setColumnWidth(8, 110)
        self.table.setColumnWidth(9, 90)

    def _setup_input_row(self):
        self.in_date = QDateEdit()
        self.in_date.setDate(datetime.now().date())
        self.in_date.setCalendarPopup(True)
        self.table.setCellWidget(0, 0, self.in_date)

        self.in_sport = QComboBox()
        self.in_sport.addItems(["Trail", "Randonnée", "Ski de rando", "Course", "Vélo", "Renforcement", "Yoga / Récup"])
        self.table.setCellWidget(0, 1, self.in_sport)

        self.in_title = QLineEdit()
        self.in_title.setPlaceholderText("Lieu / Sortie...")
        self.table.setCellWidget(0, 2, self.in_title)

        self.in_dur = QSpinBox()
        self.in_dur.setRange(5, 1440)
        self.in_dur.setValue(60)
        self.table.setCellWidget(0, 3, self.in_dur)

        self.in_dist = QDoubleSpinBox()
        self.in_dist.setRange(0.0, 300.0)
        self.in_dist.setValue(10.0)
        self.table.setCellWidget(0, 4, self.in_dist)

        self.in_dp = QSpinBox()
        self.in_dp.setRange(0, 8000)
        self.in_dp.setValue(400)
        self.table.setCellWidget(0, 5, self.in_dp)

        self.in_dm = QSpinBox()
        self.in_dm.setRange(0, 8000)
        self.in_dm.setValue(400)
        self.table.setCellWidget(0, 6, self.in_dm)

        self.in_hr = QSpinBox()
        self.in_hr.setRange(0, 220)
        self.in_hr.setValue(0)
        self.in_hr.setSpecialValueText("-")
        self.table.setCellWidget(0, 7, self.in_hr)

        # Échelle de Borg (6 à 20)
        self.in_borg = QSpinBox()
        self.in_borg.setRange(6, 20)
        self.in_borg.setValue(13)
        self.table.setCellWidget(0, 8, self.in_borg)

        btn_save = QPushButton("💾 Enregistrer")
        btn_save.setStyleSheet("background-color: #38A169; font-weight: bold; padding: 4px 8px;")
        btn_save.clicked.connect(self.save_inline_workout)
        self.table.setCellWidget(0, 9, btn_save)

    def save_inline_workout(self):
        title = self.in_title.text().strip()
        sport = self.in_sport.currentText()
        if not title:
            title = f"Sortie {sport}"

        dur = float(self.in_dur.value())
        dist = float(self.in_dist.value())
        dp = float(self.in_dp.value())
        dm = float(self.in_dm.value())
        hr = int(self.in_hr.value())
        borg = int(self.in_borg.value())
        date_str = f"{self.in_date.date().toString('yyyy-MM-dd')} 10:00:00"

        prof = get_user_profile()
        hr_rest = prof.get("hr_rest", 50)
        hr_max = prof.get("hr_max", 185)

        if hr > hr_rest:
            trimp = calculate_banister_trimp(dur, hr, hr_rest, hr_max)
        else:
            est_hr = borg * 10
            trimp = calculate_banister_trimp(dur, est_hr, hr_rest, hr_max)

        synth_filename = f"inline_{self.in_date.date().toString('yyyyMMdd')}_{int(datetime.now().timestamp())}.fit"
        act_data = {
            "filename": synth_filename, "name": title, "sport": sport,
            "start_time": date_str, "distance_km": dist, "d_plus": dp, "d_minus": dm,
            "duration_min": dur, "avg_hr": hr or (borg * 10),
            "max_hr": (hr or (borg * 10)) + 15, "trimp": trimp, "records": []
        }

        if save_activity(act_data):
            self.in_title.clear()
            self.refresh_data()
            self.activity_imported.emit()
            QMessageBox.information(self, "Séance Ajoutée", f"Activité enregistrée avec une charge TRIMP de {trimp} (Borg {borg}).")

    def open_activity_details(self, activity_id: int):
        data = get_activity_details(activity_id)
        if data:
            dlg = WorkoutDetailDialog(data, self)
            dlg.exec()

    def closeEvent(self, event):
        if hasattr(self, 'usb_thread') and self.usb_thread.isRunning():
            self.usb_thread.stop()
        super().closeEvent(event)