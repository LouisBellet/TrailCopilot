from datetime import datetime
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QDoubleSpinBox, QSpinBox, QDateEdit, QMessageBox, QSplitter
)
from core.training_db import (
    get_user_profile, update_user_profile,
    save_daily_health, get_all_daily_health, get_health_baselines
)
from core.workload_engine import WorkloadEngine

class HealthProfileView(QWidget):
    profile_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self._init_ui()
        self.load_profile()
        self.refresh_health_table()

    def _init_ui(self):
        splitter = QSplitter(Qt.Vertical)

        top_container = QWidget()
        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)

        grp_profile = QGroupBox("Profil Corporel & Constantes Physiologiques")
        p_layout = QVBoxLayout(grp_profile)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Taille :"))
        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(120.0, 230.0)
        self.spin_height.setSuffix(" cm")
        row1.addWidget(self.spin_height)

        row1.addWidget(QLabel("Poids :"))
        self.spin_weight = QDoubleSpinBox()
        self.spin_weight.setRange(35.0, 160.0)
        self.spin_weight.setSuffix(" kg")
        row1.addWidget(self.spin_weight)

        row1.addWidget(QLabel("Âge :"))
        self.spin_age = QSpinBox()
        self.spin_age.setRange(14, 100)
        self.spin_age.setSuffix(" ans")
        row1.addWidget(self.spin_age)
        p_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("FC Repos :"))
        self.spin_prof_rhr = QSpinBox()
        self.spin_prof_rhr.setRange(30, 90)
        self.spin_prof_rhr.setSuffix(" bpm")
        row2.addWidget(self.spin_prof_rhr)

        row2.addWidget(QLabel("FC Max :"))
        self.spin_prof_hrmax = QSpinBox()
        self.spin_prof_hrmax.setRange(140, 225)
        self.spin_prof_hrmax.setSuffix(" bpm")
        row2.addWidget(self.spin_prof_hrmax)

        row2.addWidget(QLabel("VMA :"))
        self.spin_vma = QDoubleSpinBox()
        self.spin_vma.setRange(8.0, 26.0)
        self.spin_vma.setSuffix(" km/h")
        row2.addWidget(self.spin_vma)
        p_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Seuil Lactique :"))
        self.spin_threshold = QSpinBox()
        self.spin_threshold.setRange(120, 210)
        self.spin_threshold.setSuffix(" bpm")
        row3.addWidget(self.spin_threshold)

        self.btn_save_profile = QPushButton("💾 Sauvegarder mon profil")
        self.btn_save_profile.setStyleSheet("background-color: #319795; font-weight: bold;")
        self.btn_save_profile.clicked.connect(self.save_profile_data)
        row3.addWidget(self.btn_save_profile)
        p_layout.addLayout(row3)

        top_layout.addWidget(grp_profile, stretch=3)

        grp_daily = QGroupBox("Saisie Bilan Matinal")
        d_layout = QVBoxLayout(grp_daily)

        d_row1 = QHBoxLayout()
        d_row1.addWidget(QLabel("Date :"))
        self.date_health = QDateEdit()
        self.date_health.setDate(datetime.now().date())
        self.date_health.setCalendarPopup(True)
        d_row1.addWidget(self.date_health)
        d_layout.addLayout(d_row1)

        d_row2 = QHBoxLayout()
        d_row2.addWidget(QLabel("RHR Matin :"))
        self.spin_day_rhr = QSpinBox()
        self.spin_day_rhr.setRange(30, 100)
        self.spin_day_rhr.setValue(48)
        self.spin_day_rhr.setSuffix(" bpm")
        d_row2.addWidget(self.spin_day_rhr)

        d_row2.addWidget(QLabel("VFC (rMSSD) :"))
        self.spin_day_vfc = QDoubleSpinBox()
        self.spin_day_vfc.setRange(10.0, 220.0)
        self.spin_day_vfc.setValue(65.0)
        self.spin_day_vfc.setSuffix(" ms")
        d_row2.addWidget(self.spin_day_vfc)
        d_layout.addLayout(d_row2)

        d_row3 = QHBoxLayout()
        d_row3.addWidget(QLabel("Sommeil :"))
        self.spin_day_sleep = QDoubleSpinBox()
        self.spin_day_sleep.setRange(2.0, 14.0)
        self.spin_day_sleep.setSingleStep(0.5)
        self.spin_day_sleep.setValue(7.5)
        self.spin_day_sleep.setSuffix(" h")
        d_row3.addWidget(self.spin_day_sleep)

        self.btn_save_health = QPushButton("📝 Valider Bilan")
        self.btn_save_health.setStyleSheet("background-color: #38A169; font-weight: bold;")
        self.btn_save_health.clicked.connect(self.save_daily_data)
        d_row3.addWidget(self.btn_save_health)
        d_layout.addLayout(d_row3)

        top_layout.addWidget(grp_daily, stretch=2)
        splitter.addWidget(top_container)

        grp_table = QGroupBox("Historique du Bilan Matinal & Récupération")
        t_layout = QVBoxLayout(grp_table)
        self.table_health = QTableWidget()
        self.table_health.setColumnCount(5)
        self.table_health.setHorizontalHeaderLabels([
            "Date", "FC Repos Matin", "VFC (rMSSD)", "Sommeil", "Score Récupération"
        ])
        self.table_health.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t_layout.addWidget(self.table_health)
        splitter.addWidget(grp_table)

        splitter.setSizes([260, 420])
        self.layout.addWidget(splitter)

    def load_profile(self):
        p = get_user_profile()
        self.spin_height.setValue(float(p.get("height_cm", 178.0)))
        self.spin_weight.setValue(float(p.get("weight_kg", 70.0)))
        self.spin_age.setValue(int(p.get("age", 30)))
        self.spin_prof_rhr.setValue(int(p.get("hr_rest", 50)))
        self.spin_prof_hrmax.setValue(int(p.get("hr_max", 185)))
        self.spin_vma.setValue(float(p.get("vma", 15.0)))
        self.spin_threshold.setValue(int(p.get("lactate_threshold_hr", 165)))

    def save_profile_data(self):
        update_user_profile(
            self.spin_height.value(),
            self.spin_weight.value(),
            self.spin_age.value(),
            self.spin_prof_rhr.value(),
            self.spin_prof_hrmax.value(),
            self.spin_vma.value(),
            self.spin_threshold.value()
        )
        QMessageBox.information(self, "Profil Enregistré", "Vos constantes corporelles ont été sauvegardées et calibreront les prochaines séances.")
        self.profile_updated.emit()

    def save_daily_data(self):
        date_str = self.date_health.date().toString("yyyy-MM-dd")
        rhr = self.spin_day_rhr.value()
        vfc = self.spin_day_vfc.value()
        sleep = self.spin_day_sleep.value()

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
        save_daily_health(date_str, rhr, vfc, sleep, score)
        self.refresh_health_table()
        self.profile_updated.emit()
        QMessageBox.information(self, "Bilan Validé", f"Score de récupération du {date_str} calculé : {score}%")

    def refresh_health_table(self):
        records = get_all_daily_health()
        self.table_health.setRowCount(len(records))
        for i, r in enumerate(records):
            self.table_health.setItem(i, 0, QTableWidgetItem(str(r["date"])))
            self.table_health.setItem(i, 1, QTableWidgetItem(f"{r['resting_hr']} bpm"))
            self.table_health.setItem(i, 2, QTableWidgetItem(f"{r['hrv_rmssd']} ms"))
            self.table_health.setItem(i, 3, QTableWidgetItem(f"{r['sleep_hours']} h"))
            
            sc = r["recovery_score"]
            sc_item = QTableWidgetItem(f"{sc}%")
            if sc >= 75:
                sc_item.setForeground(Qt.green)
            elif sc >= 50:
                sc_item.setForeground(Qt.yellow)
            else:
                sc_item.setForeground(Qt.red)
            self.table_health.setItem(i, 4, sc_item)