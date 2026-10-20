"""Keyframes tab: progress curve per phrase."""
from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from ..i18n import tr
from ..model import Keyframe, Project, animation_progress, keyframe_points, parse_time
from ..widgets import KeyframeCurve


class KeyframeMixin:
    """Mixin for MainWindow: keyframes tab: progress curve per phrase."""

    def make_keyframe_panel(self):
        scroll, layout = self.scroll_panel()
        self.keyframe_heading = QLabel(tr('Avance de la frase'))
        self.keyframe_heading.setStyleSheet('font-size:16px; color:#b8defc;')
        layout.addWidget(self.keyframe_heading)
        self.keyframe_enabled = QCheckBox(tr('Usar keyframes en esta frase'))
        self.keyframe_enabled.toggled.connect(self.keyframe_toggle)
        layout.addWidget(self.keyframe_enabled)
        self.keyframe_scope = self.combo([(tr('Repintado y énfasis'), 'all'), (tr('Solo repintado'), 'paint'),
                                          (tr('Solo énfasis'), 'emphasis')], self.keyframe_scope_changed)
        layout.addWidget(self.keyframe_scope)
        layout.addWidget(self.help_label(tr('Eje horizontal: segundos desde el inicio. Eje vertical: avance. Dos puntos con el mismo % sostienen la animación; un tramo más inclinado la acelera. Entrada y salida conservan sus tiempos.')))
        self.keyframe_curve = KeyframeCurve()
        self.keyframe_curve.add_requested.connect(self.keyframe_add)
        self.keyframe_curve.moved.connect(self.keyframe_move)
        self.keyframe_curve.seek_requested.connect(self.keyframe_seek)
        self.keyframe_curve.editing_started.connect(self.pause)
        layout.addWidget(self.keyframe_curve)
        row = QHBoxLayout()
        self.lock_time = QCheckBox(tr('Bloquear tiempo (X)'))
        self.lock_time.setToolTip(tr('Arrastrar un punto solo cambia su avance (%).'))
        self.lock_progress = QCheckBox(tr('Bloquear avance (Y)'))
        self.lock_progress.setToolTip(tr('Arrastrar un punto solo cambia su tiempo.'))
        for check, key, attr in ((self.lock_time, 'lock_keyframe_time', 'lock_time'),
                                 (self.lock_progress, 'lock_keyframe_progress', 'lock_progress')):
            check.setChecked(self.settings.value(key, False, type=bool))
            setattr(self.keyframe_curve, attr, check.isChecked())
            check.toggled.connect(lambda value, k=key, a=attr: (self.settings.setValue(k, value),
                                                                setattr(self.keyframe_curve, a, value)))
            row.addWidget(check)
        row.addStretch()
        layout.addLayout(row)
        self.keyframe_now = QLabel('')
        layout.addWidget(self.keyframe_now)
        row = QHBoxLayout()
        button = QPushButton(tr('+ En el cabezal'))
        button.clicked.connect(lambda: self.keyframe_at_head(False))
        row.addWidget(button)
        button = QPushButton(tr('Sostener hasta aquí'))
        button.clicked.connect(lambda: self.keyframe_at_head(True))
        row.addWidget(button)
        layout.addLayout(row)
        self.keyframe_table = QTableWidget(0, 2)
        self.keyframe_table.setHorizontalHeaderLabels([tr('+Tiempo (s)'), tr('Avance (%)')])
        self.keyframe_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.keyframe_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.keyframe_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.keyframe_table.setMinimumHeight(185)
        self.keyframe_table.itemChanged.connect(self.keyframe_cell_changed)
        self.keyframe_table.cellDoubleClicked.connect(lambda row, col: self.keyframe_seek_row(row) if col == 0 else None)
        layout.addWidget(self.keyframe_table)
        row = QHBoxLayout()
        button = QPushButton(tr('Eliminar puntos'))
        button.clicked.connect(self.keyframe_delete)
        row.addWidget(button)
        button = QPushButton(tr('Restablecer lineal'))
        button.clicked.connect(self.keyframe_reset)
        row.addWidget(button)
        layout.addLayout(row)
        layout.addWidget(self.help_label(tr('Los extremos 0% y 100% son automáticos: siguen «Repintar desde / Hasta» en Frase. Edita los puntos interiores en la tabla o arrástralos. Doble clic en el gráfico agrega un punto.')))
        layout.addWidget(self.help_label(tr('Ejemplo: +1.0 s → 40%; +2.5 s → 40%; final +3.0 s → 100%. Sostiene entre 1.0 y 2.5 s y completa el resto en 0.5 s. La curva se comparte entre original y traducción.')))
        layout.addStretch()
        return scroll

    def update_keyframe_position(self):
        cue = self.selected_cue()
        if not cue:
            self.keyframe_now.setText(tr('Selecciona una frase.'))
            return
        elapsed = self.position-cue.start
        self.keyframe_curve.elapsed = elapsed
        self.keyframe_now.setText(tr('Cabezal {0:+.3f} s · avance {1:.1f}%').format(elapsed, animation_progress(cue, elapsed)*100))
        self.keyframe_curve.update()

    def refresh_keyframes(self):
        was_loading = self.loading
        self.loading = True
        try:
            cue = self.selected_cue()
            self.keyframe_heading.setText(tr('Avance · frase {0}').format(self.selected_index()+1) if cue else tr('Selecciona una frase'))
            self.keyframe_enabled.setEnabled(cue is not None)
            self.keyframe_enabled.setChecked(cue.use_keyframes if cue else False)
            self.keyframe_scope.setEnabled(cue is not None)
            self.keyframe_scope.setCurrentIndex(self.keyframe_scope.findData(cue.keyframe_scope) if cue else 0)
            self.keyframe_curve.cue = cue
            self.keyframe_curve.drag_index = None
            self.keyframe_curve.drag_value = None
            points = keyframe_points(cue) if cue else []
            self.keyframe_table.setRowCount(len(points))
            for row, (time, progress) in enumerate(points):
                endpoint = row in (0, len(points)-1)
                self.keyframe_table.setVerticalHeaderItem(row, QTableWidgetItem(tr('Inicio') if row == 0 else tr('Final') if row == len(points)-1 else str(row)))
                for col, value in enumerate((f'{time:.3f}', f'{progress*100:.2f}')):
                    item = QTableWidgetItem(value)
                    if endpoint:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        item.setForeground(QColor('#8297b4'))
                        item.setToolTip(tr('Extremo automático del intervalo de repintado.'))
                    self.keyframe_table.setItem(row, col, item)
            self.keyframe_curve.update()
            self.update_keyframe_position()
        finally:
            self.loading = was_loading

    def keyframe_commit(self, points):
        cue = self.selected_cue()
        if not cue:
            return False
        points = sorted(points, key=lambda point: point.time)
        trial = copy.copy(cue)
        trial.keyframes = points
        issues = [text for code, text in Project(duration=max(self.project.duration, cue.end), cues=[trial]).problem_items()
                  if code == 'keyframes']
        if issues:
            self.statusBar().showMessage(tr('Los tiempos deben ser únicos e interiores al intervalo. El avance debe ir de 0 a 100%, sin retroceder.'), 10000)
            return False
        self.record()
        cue.keyframes = points
        self.changed(panels=True)
        return True

    def keyframe_add(self, time, progress):
        cue = self.selected_cue()
        if not cue:
            return False
        self.pause()
        point = Keyframe(round(time, 6), round(progress, 6))
        points = copy.deepcopy(cue.keyframes)
        existing = next((i for i, p in enumerate(points) if abs(p.time-point.time) < .001), None)
        if existing is None:
            points.append(point)
        else:
            point.time = points[existing].time
            points[existing] = point
        return self.keyframe_commit(points)

    def keyframe_at_head(self, hold=False):
        cue = self.selected_cue()
        if not cue:
            return
        elapsed = self.position-cue.start
        points = keyframe_points(cue)
        if not points[0][0] < elapsed < points[-1][0]:
            self.statusBar().showMessage(tr('Sitúa el cabezal dentro del intervalo de repintado de esta frase.'), 8000)
            return
        if hold:
            previous = [p for p in points if p[0] < elapsed-.000001]
            progress = previous[-1][1] if previous else 0.0
        else:
            progress = animation_progress(cue, elapsed)
        self.keyframe_add(elapsed, progress)

    def keyframe_move(self, index, time, progress):
        cue = self.selected_cue()
        if not cue or not 0 <= index < len(cue.keyframes):
            return
        self.pause()
        points = copy.deepcopy(cue.keyframes)
        points[index] = Keyframe(round(time, 6), round(progress, 6))
        if self.keyframe_commit(points):
            self.keyframe_seek(time)

    def keyframe_cell_changed(self, item):
        cue = self.selected_cue()
        if self.loading or not cue:
            return
        index = item.row()-1
        if not 0 <= index < len(cue.keyframes):
            return
        try:
            time = parse_time(self.keyframe_table.item(item.row(), 0).text())
            progress = float(self.keyframe_table.item(item.row(), 1).text().replace(',', '.'))/100
            self.keyframe_move(index, time, progress)
        except ValueError:
            self.statusBar().showMessage(tr('Tiempo inválido o porcentaje fuera de 0 a 100.'), 8000)
        self.refresh_keyframes()

    def keyframe_delete(self):
        cue = self.selected_cue()
        if not cue:
            return
        indexes = {idx.row()-1 for idx in self.keyframe_table.selectionModel().selectedRows()}
        points = [copy.deepcopy(p) for i, p in enumerate(cue.keyframes) if i not in indexes]
        if len(points) != len(cue.keyframes):
            self.keyframe_commit(points)

    def keyframe_reset(self):
        cue = self.selected_cue()
        if cue and cue.keyframes:
            self.keyframe_commit([])

    def keyframe_toggle(self, enabled):
        cue = self.selected_cue()
        if self.loading or not cue or cue.use_keyframes == enabled:
            return
        self.record()
        cue.use_keyframes = enabled
        self.changed(panels=True)

    def keyframe_scope_changed(self, scope):
        cue = self.selected_cue()
        if self.loading or not cue or cue.keyframe_scope == scope:
            return
        self.record()
        cue.keyframe_scope = scope
        self.changed(panels=True)

    def keyframe_seek(self, relative):
        cue = self.selected_cue()
        if cue:
            self.seek(cue.start+relative)

    def keyframe_seek_row(self, row):
        cue = self.selected_cue()
        if cue and 0 <= row < len(keyframe_points(cue)):
            self.keyframe_seek(keyframe_points(cue)[row][0])
