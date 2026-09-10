from datetime import datetime
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QDoubleSpinBox, QSpinBox, QMessageBox, QScrollArea,
    QGridLayout, QFrame
)
from core.training_db import get_user_profile, update_user_profile
from core.coach_engine import CoachEngine

class HealthProfileView(QWidget):
    profile_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        self.layout = QVBoxLayout(container)
        self.layout.setSpacing(14)

        self._init_profile_section()
        self._init_summary_section()
        self._init_coach_section()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self.load_profile()
        self.refresh_coach_view()

    def _init_profile_section(self):
        grp_profile = QGroupBox("Mes Constantes Corporelles & Physiologiques (Persistantes)")
        grid = QGridLayout(grp_profile)
        grid.setSpacing(10)

        grid.addWidget(QLabel("Taille :"), 0, 0)
        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(120.0, 230.0)
        self.spin_height.setSuffix(" cm")
        grid.addWidget(self.spin_height, 0, 1)

        grid.addWidget(QLabel("Poids :"), 0, 2)
        self.spin_weight = QDoubleSpinBox()
        self.spin_weight.setRange(35.0, 160.0)
        self.spin_weight.setSuffix(" kg")
        grid.addWidget(self.spin_weight, 0, 3)

        grid.addWidget(QLabel("Âge :"), 0, 4)
        self.spin_age = QSpinBox()
        self.spin_age.setRange(14, 100)
        self.spin_age.setSuffix(" ans")
        grid.addWidget(self.spin_age, 0, 5)

        grid.addWidget(QLabel("FC Repos :"), 1, 0)
        self.spin_rhr = QSpinBox()
        self.spin_rhr.setRange(30, 100)
        self.spin_rhr.setSuffix(" bpm")
        grid.addWidget(self.spin_rhr, 1, 1)

        grid.addWidget(QLabel("FC Max :"), 1, 2)
        self.spin_hrmax = QSpinBox()
        self.spin_hrmax.setRange(140, 225)
        self.spin_hrmax.setSuffix(" bpm")
        grid.addWidget(self.spin_hrmax, 1, 3)

        grid.addWidget(QLabel("VMA :"), 1, 4)
        self.spin_vma = QDoubleSpinBox()
        self.spin_vma.setRange(8.0, 26.0)
        self.spin_vma.setSuffix(" km/h")
        grid.addWidget(self.spin_vma, 1, 5)

        self.btn_save_profile = QPushButton("💾 Enregistrer mon profil")
        self.btn_save_profile.setStyleSheet("background-color: #319795; font-weight: bold; padding: 6px 14px;")
        self.btn_save_profile.clicked.connect(self.save_profile_data)
        grid.addWidget(self.btn_save_profile, 1, 6)

        self.layout.addWidget(grp_profile)

    def _init_summary_section(self):
        self.grp_summary = QGroupBox("Bilan de Charge — 7 Derniers Jours Glissants")
        s_layout = QHBoxLayout(self.grp_summary)

        self.lbl_sum_dist = QLabel("<b>Distance :</b> -- km")
        self.lbl_sum_dplus = QLabel("<b>D+ :</b> +-- m")
        self.lbl_sum_dminus = QLabel("<b>D- :</b> --- m")
        self.lbl_sum_dur = QLabel("<b>Volume :</b> --")
        self.lbl_sum_trimp = QLabel("<b>Charge TRIMP :</b> --")
        self.lbl_sum_sess = QLabel("<b>Séances :</b> --")

        for lbl in (self.lbl_sum_sess, self.lbl_sum_dur, self.lbl_sum_dist, self.lbl_sum_dplus, self.lbl_sum_dminus, self.lbl_sum_trimp):
            lbl.setStyleSheet("font-size: 13px; color: #E2E8F0;")
            s_layout.addWidget(lbl)

        self.layout.addWidget(self.grp_summary)

    def _init_coach_section(self):
        self.grp_coach = QGroupBox("Conseiller Tactique Quotidien — Vos 3 Options pour Aujourd'hui")
        c_layout = QVBoxLayout(self.grp_coach)

        self.banner_status = QLabel()
        self.banner_status.setStyleSheet("padding: 8px 12px; border-radius: 5px; font-weight: bold; font-size: 13px; color: white;")
        c_layout.addWidget(self.banner_status)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_boxes = []
        for i in range(3):
            box = QGroupBox(f"Option {i+1}")
            box_layout = QVBoxLayout(box)
            box_layout.setSpacing(6)

            lbl_title = QLabel()
            lbl_title.setWordWrap(True)
            lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #4FD1C5;")

            lbl_tag = QLabel()
            lbl_tag.setStyleSheet("color: #F6AD55; font-weight: bold; font-size: 11px;")

            lbl_dur = QLabel()
            lbl_dur.setStyleSheet("color: #CBD5E0; font-size: 12px;")

            lbl_target = QLabel()
            lbl_target.setStyleSheet("color: #68D391; font-weight: bold; font-size: 12px;")

            lbl_desc = QLabel()
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet("color: #A0AEC0; font-size: 12px; line-height: 1.3;")

            box_layout.addWidget(lbl_tag)
            box_layout.addWidget(lbl_title)
            box_layout.addWidget(lbl_dur)
            box_layout.addWidget(lbl_target)
            box_layout.addWidget(lbl_desc)
            box_layout.addStretch()

            cards_layout.addWidget(box)
            self.card_boxes.append({
                "box": box, "title": lbl_title, "tag": lbl_tag,
                "dur": lbl_dur, "target": lbl_target, "desc": lbl_desc
            })

        c_layout.addLayout(cards_layout)
        self.layout.addWidget(self.grp_coach)

    def load_profile(self):
        p = get_user_profile()
        self.spin_height.setValue(float(p.get("height_cm", 178.0)))
        self.spin_weight.setValue(float(p.get("weight_kg", 70.0)))
        self.spin_age.setValue(int(p.get("age", 30)))
        self.spin_rhr.setValue(int(p.get("hr_rest", 50)))
        self.spin_hrmax.setValue(int(p.get("hr_max", 185)))
        self.spin_vma.setValue(float(p.get("vma", 15.0)))

    def save_profile_data(self):
        update_user_profile(
            self.spin_height.value(),
            self.spin_weight.value(),
            self.spin_age.value(),
            self.spin_rhr.value(),
            self.spin_hrmax.value(),
            self.spin_vma.value(),
            165
        )
        QMessageBox.information(self, "Profil Enregistré", "Paramètres physiologiques sauvegardés. Le conseiller a recalculé vos allures cibles.")
        self.refresh_coach_view()
        self.profile_updated.emit()

    def refresh_coach_view(self):
        summary = CoachEngine.get_7day_summary()
        self.lbl_sum_sess.setText(f"<b>Séances 7j :</b> {summary['sessions_count']}")
        self.lbl_sum_dur.setText(f"<b>Volume 7j :</b> {summary['duration_str']}")
        self.lbl_sum_dist.setText(f"<b>Distance 7j :</b> {summary['distance_km']} km")
        self.lbl_sum_dplus.setText(f"<b>D+ 7j :</b> +{summary['d_plus']} m")
        self.lbl_sum_dminus.setText(f"<b>D- 7j :</b> -{summary['d_minus']} m")
        self.lbl_sum_trimp.setText(f"<b>Charge TRIMP :</b> {summary['total_trimp']}")

        advice = CoachEngine.generate_daily_advice()
        self.banner_status.setText(f"[{advice['badge']}] — {advice['status_text']}")
        self.banner_status.setStyleSheet(f"background-color: {advice['status_color']}; padding: 8px 12px; border-radius: 5px; font-weight: bold; color: white;")

        for i, opt in enumerate(advice["options"]):
            card = self.card_boxes[i]
            card["box"].setTitle(f"Option {i+1}")
            card["tag"].setText(opt["tag"].upper())
            card["title"].setText(opt["title"])
            card["dur"].setText(f"⏱ <b>Durée :</b> {opt['duration']}")
            card["target"].setText(f"🎯 <b>Cible :</b> {opt['target']}")
            card["desc"].setText(opt["desc"])