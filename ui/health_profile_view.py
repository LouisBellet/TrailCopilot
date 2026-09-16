from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QDoubleSpinBox, QSpinBox, QMessageBox, QScrollArea,
    QGridLayout, QFrame
)
from core.training_db import get_user_profile, update_user_profile
from core.data_manager import DataManager

class HealthProfileView(QWidget):
    profile_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_loaded = False
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

    def ensure_loaded(self):
        if not self.is_loaded or DataManager.is_tab_dirty(2):
            self.load_profile()
            self.refresh_coach_view()
            self.is_loaded = True
            DataManager.mark_tab_clean(2)

    def _init_profile_section(self):
        grp_profile = QGroupBox("Constantes Corporelles & Physiologiques (Persistantes)")
        grid = QGridLayout(grp_profile)
        grid.setSpacing(8)

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
        self.btn_save_profile.setStyleSheet("background-color: #319795; font-weight: bold; padding: 6px 12px;")
        self.btn_save_profile.clicked.connect(self.save_profile_data)
        grid.addWidget(self.btn_save_profile, 1, 6)

        self.layout.addWidget(grp_profile)

    def _init_summary_section(self):
        self.grp_summary = QGroupBox("Bilan de Charge Cumulée — 7 Derniers Jours Glissants")
        s_layout = QHBoxLayout(self.grp_summary)

        self.lbl_sum_sess = QLabel("<b>Séances :</b> --")
        self.lbl_sum_dur = QLabel("<b>Volume :</b> --")
        self.lbl_sum_dist = QLabel("<b>Distance :</b> -- km")
        self.lbl_sum_dplus = QLabel("<b>D+ :</b> +-- m")
        self.lbl_sum_dminus = QLabel("<b>D- :</b> --- m")
        self.lbl_sum_trimp = QLabel("<b>Charge TRIMP :</b> --")

        for lbl in (self.lbl_sum_sess, self.lbl_sum_dur, self.lbl_sum_dist, self.lbl_sum_dplus, self.lbl_sum_dminus, self.lbl_sum_trimp):
            lbl.setStyleSheet("font-size: 12px; color: #E2E8F0;")
            s_layout.addWidget(lbl)

        self.layout.addWidget(self.grp_summary)

    def _init_coach_section(self):
        self.grp_coach = QGroupBox("Conseiller Tactique Prédictif — Projections à J+1")
        c_layout = QVBoxLayout(self.grp_coach)

        self.banner_status = QLabel()
        self.banner_status.setStyleSheet("padding: 8px 12px; border-radius: 4px; font-weight: bold; font-size: 12px; color: white;")
        c_layout.addWidget(self.banner_status)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        self.card_boxes = []
        for i in range(3):
            box = QGroupBox(f"Option {i+1}")
            box_layout = QVBoxLayout(box)
            box_layout.setSpacing(6)

            lbl_tag = QLabel()
            lbl_tag.setStyleSheet("color: #F6AD55; font-weight: bold; font-size: 11px;")

            lbl_title = QLabel()
            lbl_title.setWordWrap(True)
            lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #4FD1C5;")

            lbl_proj = QLabel()
            lbl_proj.setStyleSheet("background:#242933; color:#38B2AC; font-size:12px; font-weight:bold; padding:4px 6px; border-radius:3px;")

            lbl_timing = QLabel()
            lbl_timing.setStyleSheet("color: #63B3ED; font-size: 11px; font-weight: bold;")

            lbl_rec = QLabel()
            lbl_rec.setStyleSheet("color: #68D391; font-size: 11px; font-weight: bold;")

            lbl_prog = QLabel()
            lbl_prog.setWordWrap(True)
            lbl_prog.setStyleSheet("color: #CBD5E0; font-size: 11px; line-height: 1.3;")

            lbl_tact = QLabel()
            lbl_tact.setWordWrap(True)
            lbl_tact.setStyleSheet("color: #A0AEC0; font-style: italic; font-size: 11px;")

            box_layout.addWidget(lbl_tag)
            box_layout.addWidget(lbl_title)
            box_layout.addWidget(lbl_proj)
            box_layout.addWidget(lbl_timing)
            box_layout.addWidget(lbl_rec)
            box_layout.addWidget(QLabel("<b>Programme détaillé :</b>"))
            box_layout.addWidget(lbl_prog)
            box_layout.addWidget(lbl_tact)
            box_layout.addStretch()

            cards_layout.addWidget(box)
            self.card_boxes.append({
                "box": box, "tag": lbl_tag, "title": lbl_title,
                "proj": lbl_proj, "timing": lbl_timing, "rec": lbl_rec,
                "prog": lbl_prog, "tact": lbl_tact
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
            self.spin_height.value(), self.spin_weight.value(),
            self.spin_age.value(), self.spin_rhr.value(),
            self.spin_hrmax.value(), self.spin_vma.value(), 165
        )
        DataManager.invalidate_cache()
        QMessageBox.information(self, "Profil Enregistré", "Paramètres sauvegardés. Le budget TRIMP et les projections ont été recalculés.")
        self.refresh_coach_view()
        self.profile_updated.emit()

    def refresh_coach_view(self):
        summary = DataManager.get_summary_7d()
        self.lbl_sum_sess.setText(f"<b>Séances :</b> {summary['sessions_count']}")
        self.lbl_sum_dur.setText(f"<b>Volume :</b> {summary['duration_str']}")
        self.lbl_sum_dist.setText(f"<b>Distance :</b> {summary['distance_km']} km")
        self.lbl_sum_dplus.setText(f"<b>D+ :</b> +{summary['d_plus']} m")
        self.lbl_sum_dminus.setText(f"<b>D- :</b> -{summary['d_minus']} m")
        self.lbl_sum_trimp.setText(f"<b>Charge TRIMP :</b> {summary['total_trimp']}")

        advice = DataManager.get_coach_advice()
        self.banner_status.setText(f"[{advice['badge']}] — {advice['status_text']}")
        self.banner_status.setStyleSheet(
            f"background-color: {advice['status_color']}; padding: 8px 12px; border-radius: 4px; font-weight: bold; color: white;"
        )

        for i, opt in enumerate(advice["options"]):
            card = self.card_boxes[i]
            card["tag"].setText(opt["tag"].upper())
            card["title"].setText(opt["title"])
            card["proj"].setText(f"Impact : +{int(opt.get('trimp', 0))} TRIMP ➔ ACWR Demain : {opt.get('proj_acwr', '--')}")
            card["timing"].setText(f"⏰ {opt['timing']}")
            card["rec"].setText(f"⏳ Temps de récupération estimé : {opt['recovery_time']}")
            prog_text = "<br>• " + "<br>• ".join(opt["program"])
            card["prog"].setText(prog_text)
            card["tact"].setText(f"💡 <i>{opt['tactical_note']}</i>")