"""Syllables tab: marks, estimates, audio snapping and the expanded editor."""
from __future__ import annotations

import math
import unicodedata

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..model import (
    add_span,
    animation_to_elapsed,
    parse_time,
    propose_spans,
    snap_spans_to_audio,
    split_spans,
    time_text,
)
from ..widgets import Preview


class SyllableMixin:
    """Mixin for MainWindow: syllables tab: marks, estimates, audio snapping and the expanded editor."""

    def make_span_panel(self):
        scroll, layout = self.scroll_panel()
        self.track = QComboBox()
        self.track.addItem(tr('Original'), 'original')
        self.track.addItem(tr('Traducción'), 'translation')
        self.track.currentIndexChanged.connect(self.refresh_spans)
        layout.addWidget(self.track)
        button = QPushButton(tr('Ampliar editor de sílabas'))
        button.clicked.connect(self.expand_span_editor)
        layout.addWidget(button)
        layout.addWidget(self.help_label(tr('Selecciona letras en el texto y pulsa «Marcar selección». Las marcas son rangos del texto; no agregan espacios visibles.')))
        self.span_text = QPlainTextEdit()
        self.span_text.setReadOnly(True)
        self.span_text.setMaximumHeight(78)
        layout.addWidget(self.span_text)
        row = QHBoxLayout()
        btn = QPushButton(tr('Marcar selección'))
        btn.clicked.connect(self.mark_selection)
        row.addWidget(btn)
        btn = QPushButton(tr('Repetir en frases'))
        btn.clicked.connect(self.repeat_selection)
        row.addWidget(btn)
        layout.addLayout(row)
        self.split_edit = QLineEdit()
        self.split_edit.setPlaceholderText(tr('Alternativa: vuel|ve a bri|llar'))
        layout.addWidget(self.split_edit)
        btn = QPushButton(tr('Crear marcas separadas con |'))
        btn.clicked.connect(self.apply_split)
        layout.addWidget(btn)
        layout.addWidget(self.help_label(tr('Tiempos de animación relativos al inicio de la frase. Si usas keyframes para énfasis, la curva reprograma cuándo se alcanzan. Color, subida y escala vacíos heredan el estilo global. ✓ activa el énfasis.')))
        self.span_table = QTableWidget(0, 7)
        self.span_table.setHorizontalHeaderLabels(['✓', tr('Parte'), tr('+Inicio'), tr('+Fin'), tr('Color'), tr('Subir'), tr('Escala')])
        self.span_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.span_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.span_table.verticalHeader().hide()
        for col, width in enumerate([30, 95, 67, 67, 85, 57, 57]):
            self.span_table.setColumnWidth(col, width)
        self.span_table.setMinimumHeight(200)
        # Double click is handled in span_double_click: it edits times/lift/scale, plays a
        # part, or opens the color dialog without also opening the cell editor.
        self.span_table.setEditTriggers(QAbstractItemView.EditTrigger.EditKeyPressed
                                        | QAbstractItemView.EditTrigger.AnyKeyPressed)
        self.span_table.itemChanged.connect(self.span_cell_changed)
        self.span_table.cellDoubleClicked.connect(self.span_double_click)
        layout.addWidget(self.span_table)
        row = QHBoxLayout()
        for caption, fn in [(tr('Estimar tiempos'), self.auto_spans), (tr('Eliminar marcas'), self.remove_spans)]:
            btn = QPushButton(caption)
            btn.clicked.connect(fn)
            row.addWidget(btn)
        layout.addLayout(row)
        btn = QPushButton(tr('Ajustar marcas a ataques del audio (±0.18 s)'))
        btn.clicked.connect(self.snap_audio)
        layout.addWidget(btn)
        row = QHBoxLayout()
        btn = QPushButton(tr('Color a selección'))
        btn.clicked.connect(self.bulk_color)
        row.addWidget(btn)
        btn = QPushButton(tr('Heredar global'))
        btn.clicked.connect(self.inherit_spans)
        row.addWidget(btn)
        layout.addLayout(row)
        layout.addWidget(self.help_label(tr('Estimar reparte por texto. Ajustar al audio busca ataques cercanos: puede seguir instrumentos. No detecta voz ni separa sílabas. Doble clic en una parte: reproducir su momento.')))
        layout.addStretch()
        return scroll

    def refresh_spans(self):
        was_loading = self.loading
        self.loading = True
        try:
            cue = self.selected_cue()
            track = self.track.currentData() or 'original'
            text = getattr(cue, track) if cue else ''
            self.span_text.setPlainText(text)
            self.split_edit.setText(text)
            spans = cue.spans(track) if cue else []
            self.span_table.setRowCount(len(spans))
            for row, span in enumerate(spans):
                item = QTableWidgetItem('')
                item.setFlags((item.flags() | Qt.ItemFlag.ItemIsUserCheckable) & ~Qt.ItemFlag.ItemIsEditable)
                item.setCheckState(Qt.CheckState.Checked if span.enabled else Qt.CheckState.Unchecked)
                self.span_table.setItem(row, 0, item)
                values = [text[span.begin:span.end], f'{span.start:.3f}', f'{span.finish:.3f}', span.color,
                          '' if span.lift is None else str(span.lift), '' if span.scale is None else str(span.scale)]
                for col, value in enumerate(values, 1):
                    item = QTableWidgetItem(value)
                    if col == 1:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if col == 4 and value:
                        item.setForeground(QColor(value))
                    self.span_table.setItem(row, col, item)
        finally:
            self.loading = was_loading

    def selected_text_range(self):
        cue = self.selected_cue()
        cursor = self.span_text.textCursor()
        if not cue or not cursor.hasSelection():
            raise ValueError(tr('Selecciona primero la sílaba o parte del texto en el recuadro superior.'))
        text = getattr(cue, self.track.currentData())
        # QTextCursor offsets are UTF-16 units, Python offsets are Unicode code points.
        raw = text.encode('utf-16-le')
        begin = len(raw[:cursor.selectionStart()*2].decode('utf-16-le'))
        end = len(raw[:cursor.selectionEnd()*2].decode('utf-16-le'))
        if (begin < len(text) and unicodedata.combining(text[begin])) or (end < len(text) and unicodedata.combining(text[end])):
            raise ValueError(tr('Incluye el carácter completo junto con su acento.'))
        return begin, end, text[begin:end]

    def mark_selection(self):
        cue = self.selected_cue()
        if not cue:
            return
        try:
            begin, end, _ = self.selected_text_range()
            track = self.track.currentData()
            if any(begin < s.end and end > s.begin for s in cue.spans(track)):
                raise ValueError(tr('La selección se cruza con una marca existente; elimínala primero.'))
            self.record()
            add_span(cue, track, begin, end)
            self.changed(panels=True)
        except ValueError as exc:
            self.statusBar().showMessage(str(exc), 8000)

    def repeat_selection(self):
        try:
            _, _, fragment = self.selected_text_range()
        except ValueError as exc:
            self.statusBar().showMessage(str(exc), 8000)
            return
        if not fragment.strip():
            return
        track = self.track.currentData()
        matches = []
        for cue in self.project.cues:
            text = getattr(cue, track)
            offset = 0
            while True:
                begin = text.find(fragment, offset)
                if begin < 0:
                    break
                end = begin + len(fragment)
                if not any(begin < s.end and end > s.begin for s in cue.spans(track)):
                    matches.append((cue, begin, end))
                offset = end
        if matches:
            self.record()
            for cue, begin, end in matches:
                add_span(cue, track, begin, end)
            self.changed(panels=True)
        self.statusBar().showMessage(tr('{0} marca(s) creada(s). Revisa sus tiempos estimados.').format(len(matches)), 8000)

    def apply_split(self):
        cue = self.selected_cue()
        if not cue:
            return
        marked = self.split_edit.text()
        track = self.track.currentData()
        if marked.replace('|', '') != getattr(cue, track):
            self.statusBar().showMessage(tr('Conserva exactamente el texto y los espacios; agrega únicamente |.'), 8000)
            return
        self.record()
        split_spans(cue, track, marked)
        self.changed(panels=True)
        self.statusBar().showMessage(tr('Marcas creadas con tiempos estimados; corrígelos escuchando.'), 6000)

    def span_cell_changed(self, item):
        if self.loading:
            return
        cue = self.selected_cue()
        if not cue:
            return
        row, col = item.row(), item.column()
        spans = cue.spans(self.track.currentData())
        if row >= len(spans) or col == 1:
            return
        span = spans[row]
        try:
            value = item.text().strip()
            if col in (2, 3):
                parsed = parse_time(value)
                if col == 2 and not 0 <= parsed < span.finish or col == 3 and not span.start < parsed <= cue.duration:
                    raise ValueError(tr('El intervalo debe quedar dentro de la frase y tener duración positiva.'))
            elif col == 4:
                if value and not QColor(value).isValid():
                    raise ValueError(tr('Color inválido. Usa #RRGGBB o deja vacío para heredar.'))
                parsed = QColor(value).name() if value else ''
            elif col in (5, 6):
                parsed = float(value) if value else None
                if parsed is not None and (not math.isfinite(parsed) or (col == 5 and not -100 <= parsed <= 160) or (col == 6 and not .5 <= parsed <= 3)):
                    raise ValueError(tr('Subida: -100 a 160 px. Escala: 0.5 a 3.'))
            else:
                parsed = item.checkState() == Qt.CheckState.Checked
            self.record()
            setattr(span, {0:'enabled', 2:'start', 3:'finish', 4:'color', 5:'lift', 6:'scale'}[col], parsed)
            self.changed()
        except ValueError as exc:
            self.statusBar().showMessage(str(exc), 8000)
        self.refresh_spans()

    def span_double_click(self, row, col):
        cue = self.selected_cue()
        if not cue:
            return
        span = cue.spans(self.track.currentData())[row]
        if col == 1:
            elapsed = animation_to_elapsed(cue, span.start) if cue.keyframe_scope in ('all', 'emphasis') else span.start
            self.seek(cue.start + elapsed)
            self.play()
        elif col == 4:
            self.bulk_color()
        elif col in (2, 3, 5, 6):
            self.span_table.editItem(self.span_table.item(row, col))

    def span_rows(self):
        return sorted({idx.row() for idx in self.span_table.selectionModel().selectedRows()})

    def auto_spans(self):
        cue = self.selected_cue()
        if cue:
            self.record()
            propose_spans(cue, self.track.currentData())
            self.changed(panels=True)
            self.statusBar().showMessage(tr('Reparto estimado aplicado. No se ha analizado la voz.'), 7000)

    def snap_audio(self):
        cue = self.selected_cue()
        if cue is None:
            return
        if not self.waveform.peaks:
            QMessageBox.information(self, tr('Audio pendiente'), tr('Carga un medio y espera a que aparezca su forma de onda. Esta función necesita FFmpeg.'))
            return
        self.record()
        count = snap_spans_to_audio(cue, self.track.currentData(), self.waveform.peaks, self.waveform.audio_duration)
        self.changed(panels=True)
        QMessageBox.information(self, tr('Ajuste orientativo'), tr('{0} marca(s) ajustada(s) a ataques cercanos del audio.\nLos instrumentos también generan ataques: revisa escuchando.').format(count))

    def expand_span_editor(self):
        panel = self.tabs.widget(1)
        self.tabs.removeTab(1)
        dialog = QDialog(self)
        dialog.setWindowTitle(tr('Sílabas · editor ampliado'))
        dialog.resize(1150, 760)
        layout = QVBoxLayout(dialog)
        split = QSplitter(Qt.Orientation.Horizontal)
        visual = QWidget()
        vl = QVBoxLayout(visual)
        preview = Preview()
        preview.setMinimumSize(420, 250)
        vl.addWidget(preview, 1)
        label = QLabel()
        vl.addWidget(label)
        play_toggle = QPushButton()
        play_toggle.setIconSize(QSize(18, 18))
        play_toggle.clicked.connect(self.toggle_play)
        vl.addWidget(play_toggle)
        for caption, fn in [(tr('Repetir frase'), self.play_cue),
                            (tr('Retroceder 0.1 s'), lambda: self.seek(self.position-.1)),
                            (tr('Avanzar 0.1 s'), lambda: self.seek(self.position+.1))]:
            button = QPushButton(caption)
            button.clicked.connect(fn)
            vl.addWidget(button)
        loop = QCheckBox(tr('Bucle de la frase seleccionada'))
        loop.setChecked(self.loop.isChecked())
        loop.toggled.connect(self.loop.setChecked)
        vl.addWidget(loop)
        split.addWidget(visual)
        split.addWidget(panel)
        split.setSizes([500, 650])
        layout.addWidget(split)
        close = QPushButton(tr('Volver al editor principal'))
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        timer = QTimer(dialog)
        def refresh():
            preview.project = self.project
            preview.font_override = self.preview.font_override
            preview.time = self.position
            preview.video = self.preview.video
            preview.update()
            label.setText(time_text(self.position))
            self.update_play_button(play_toggle)
        timer.timeout.connect(refresh)
        timer.start(33)
        refresh()
        try:
            dialog.exec()
        finally:
            timer.stop()
            self.tabs.insertTab(1, panel, tr('Sílabas'))
            self.tabs.setCurrentIndex(1)

    def remove_spans(self):
        cue, rows = self.selected_cue(), self.span_rows()
        if cue and rows:
            self.record()
            spans = cue.spans(self.track.currentData())
            for row in reversed(rows):
                del spans[row]
            self.changed(panels=True)

    def bulk_color(self):
        cue, rows = self.selected_cue(), self.span_rows()
        if not cue or not rows:
            self.statusBar().showMessage(tr('Selecciona una o varias filas de sílabas (Ctrl / Shift).'), 5000)
            return
        color = QColorDialog.getColor(QColor(self.project.style.effect_color), self, tr('Color de énfasis para la selección'))
        if color.isValid():
            self.record()
            for row in rows:
                cue.spans(self.track.currentData())[row].color = color.name()
            self.changed(panels=True)

    def inherit_spans(self):
        cue, rows = self.selected_cue(), self.span_rows()
        if cue and rows:
            self.record()
            for row in rows:
                span = cue.spans(self.track.currentData())[row]
                span.color, span.lift, span.scale = '', None, None
            self.changed(panels=True)
