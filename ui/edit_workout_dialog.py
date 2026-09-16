from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QPushButton, QDateEdit,
    QGroupBox, QMessageBox
)
from core.fit_parser import calculate_banister_trimp
from core.training_db import update_activity, delete_activity, get_user_profile

class EditWorkoutDialog(QDialog):
    def __init__(self, activity_data: dict, parent=None):
        super().__init__(parent)
        self.act = activity_data
        self.profile = get_user_profile()
        self.was_deleted = False

        self.setWindowTitle(f"Modifier la séance — {self.act.get('name', 'Activité')}")
        self.resize(520, 480)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Date & Sport
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("<b>Date :</b>"))
        self.date_edit = QDateEdit()
        raw_date = str(self.act.get("start_time", ""))[:10]
        try:
            d_obj = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except Exception:
            d_obj = datetime.now().date()
        self.date_edit.setDate(d_obj)
        self.date_edit.setCalendarPopup(True)
        h1.addWidget(self.date_edit)

        h1.addWidget(QLabel("<b>Sport :</b>"))
        self.combo_sport = QComboBox()
        self.combo_sport.addItems(["Trail", "Randonnée", "Ski de rando", "Course", "Vélo", "Renforcement", "Yoga / Récup", "Autre"])
        curr_sport = self.act.get("sport", "Trail")
        idx = self.combo_sport.findText(curr_sport)
        if idx >= 0:
            self.combo_sport.setCurrentIndex(idx)
        h1.addWidget(self.combo_sport)
        layout.addLayout(h1)

        # Titre
        layout.addWidget(QLabel("<b>Titre / Lieu :</b>"))
        self.txt_title = QLineEdit(self.act.get("name", ""))
        layout.addWidget(self.txt_title)

        # Métriques Volume
        grp_vol = QGroupBox("Métrique de la séance")
        v_grid = QVBoxLayout(grp_vol)

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Durée :"))
        self.spin_dur = QSpinBox()
        self.spin_dur.setRange(1, 1440)
        self.spin_dur.setValue(int(self.act.get("duration_min", 60)))
        self.spin_dur.setSuffix(" min")
        self.spin_dur.valueChanged.connect(self._recalc_preview)
        r1.addWidget(self.spin_dur)

        r1.addWidget(QLabel("Distance :"))
        self.spin_dist = QDoubleSpinBox()
        self.spin_dist.setRange(0.0, 500.0)
        self.spin_dist.setValue(float(self.act.get("distance_km", 0.0)))
        self.spin_dist.setSuffix(" km")
        r1.addWidget(self.spin_dist)
        v_grid.addLayout(r1)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("D+ :"))
        self.spin_dp = QSpinBox()
        self.spin_dp.setRange(0, 9000)
        self.spin_dp.setValue(int(self.act.get("d_plus", 0)))
        self.spin_dp.setSuffix(" m")
        r2.addWidget(self.spin_dp)

        r2.addWidget(QLabel("D- :"))
        self.spin_dm = QSpinBox()
        self.spin_dm.setRange(0, 9000)
        self.spin_dm.setValue(int(self.act.get("d_minus", 0)))
        self.spin_dm.setSuffix(" m")
        r2.addWidget(self.spin_dm)
        v_grid.addLayout(r2)
        layout.addWidget(grp_vol)

        # Intensité (FC & Borg)
        grp_int = QGroupBox("Intensité & Charge")
        i_grid = QVBoxLayout(grp_int)

        r3 = QHBoxLayout()
        r3.addWidget(QLabel("FC Moyenne :"))
        self.spin_hr = QSpinBox()
        self.spin_hr.setRange(0, 220)
        self.spin_hr.setValue(int(self.act.get("avg_hr") or 0))
        self.spin_hr.setSpecialValueText("- (Non mesurée)")
        self.spin_hr.setSuffix(" bpm")
        self.spin_hr.valueChanged.connect(self._recalc_preview)
        r3.addWidget(self.spin_hr)

        r3.addWidget(QLabel("Borg RPE (6-20) :"))
        self.spin_borg = QSpinBox()
        self.spin_borg.setRange(6, 20)
        self.spin_borg.setValue(int(self.act.get("rpe") or 13))
        self.spin_borg.valueChanged.connect(self._recalc_preview)
        r3.addWidget(self.spin_borg)
        i_grid.addLayout(r3)

        self.lbl_preview = QLabel()
        self.lbl_preview.setStyleSheet("color: #4FD1C5; font-weight: bold; padding: 4px;")
        i_grid.addWidget(self.lbl_preview)
        layout.addWidget(grp_int)

        self._recalc_preview()

        # Boutons
        btn_box = QHBoxLayout()

        self.btn_delete = QPushButton("🗑️ Supprimer cette séance")
        self.btn_delete.setStyleSheet("background-color: #E53E3E; font-weight: bold; padding: 6px 12px;")
        self.btn_delete.clicked.connect(self._delete_workout)
        btn_box.addWidget(self.btn_delete)

        btn_box.addStretch()

        self.btn_cancel = QPushButton("Annuler")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("💾 Enregistrer les modifications")
        self.btn_save.setStyleSheet("background-color: #38A169; font-weight: bold; padding: 6px 14px;")
        self.btn_save.clicked.connect(self._save_changes)
        btn_box.addWidget(self.btn_save)

        layout.addLayout(btn_box)

    def _recalc_preview(self):
        dur = float(self.spin_dur.value())
        hr = int(self.spin_hr.value())
        borg = int(self.spin_borg.value())
        hr_rest = self.profile.get("hr_rest", 50)
        hr_max = self.profile.get("hr_max", 185)

        if hr > hr_rest:
            trimp = calculate_banister_trimp(dur, hr, hr_rest, hr_max)
            mode = f"Cardio réel ({hr} bpm)"
        else:
            est_hr = borg * 10
            trimp = calculate_banister_trimp(dur, est_hr, hr_rest, hr_max)
            mode = f"Échelle de Borg ({borg}/20)"

        self.lbl_preview.setText(f"Charge recalculée : <b>{trimp} TRIMP</b> (Méthode : {mode})")

    def _save_changes(self):
        dur = float(self.spin_dur.value())
        hr = int(self.spin_hr.value())
        borg = int(self.spin_borg.value())
        hr_rest = self.profile.get("hr_rest", 50)
        hr_max = self.profile.get("hr_max", 185)

        if hr > hr_rest:
            trimp = calculate_banister_trimp(dur, hr, hr_rest, hr_max)
        else:
            est_hr = borg * 10
            trimp = calculate_banister_trimp(dur, est_hr, hr_rest, hr_max)

        date_str = f"{self.date_edit.date().toString('yyyy-MM-dd')} 10:00:00"
        title = self.txt_title.text().strip() or f"Sortie {self.combo_sport.currentText()}"

        updated_data = {
            "start_time": date_str,
            "name": title,
            "sport": self.combo_sport.currentText(),
            "distance_km": float(self.spin_dist.value()),
            "d_plus": float(self.spin_dp.value()),
            "d_minus": float(self.spin_dm.value()),
            "duration_min": dur,
            "avg_hr": hr or (borg * 10),
            "max_hr": (hr or (borg * 10)) + 15,
            "trimp": trimp,
            "rpe": borg
        }

        if update_activity(self.act["id"], updated_data):
            QMessageBox.information(self, "Modifications enregistrées", f"La séance a été mise à jour (Nouvelle charge : {trimp} TRIMP).")
            self.accept()
        else:
            QMessageBox.critical(self, "Erreur", "Impossible de mettre à jour la séance en base.")

    def _delete_workout(self):
        rep = QMessageBox.question(
            self, "Confirmer la suppression",
            f"Voulez-vous vraiment supprimer la séance <b>{self.act.get('name')}</b> du {self.act.get('start_time')[:10]} ?<br>Cette action est irréversible.",
            QMessageBox.Yes | QMessageBox.No
        )
        if rep == QMessageBox.Yes:
            if delete_activity(self.act["id"]):
                self.was_deleted = True
                QMessageBox.information(self, "Séance supprimée", "L'activité a été retirée de la base de données.")
                self.accept()
            else:
                QMessageBox.critical(self, "Erreur", "Impossible de supprimer la séance.")