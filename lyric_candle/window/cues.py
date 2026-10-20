"""Phrase table and Line tab: times, text editors and drafts, adding/removing phrases."""
from __future__ import annotations

import copy

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidgetItem,
)

from ..i18n import tr
from ..model import Cue, clamp_cue, parse_time, retime_cue, retime_keyframes, time_text


class CueEditorMixin:
    """Mixin for MainWindow: phrase table and Line tab: times, text editors and drafts, adding/removing phrases."""

    def make_cue_panel(self):
        scroll, layout = self.scroll_panel()
        self.cue_heading = QLabel(tr('Frase seleccionada'))
        self.cue_heading.setStyleSheet('font-size:16px; color:#b8defc;')
        layout.addWidget(self.cue_heading)
        form = QFormLayout()
        self.cue_start = self.spin()
        self.cue_end = self.spin(value=3)
        self.paint_start = self.spin()
        self.paint_end = self.spin(value=3)
        for caption, widget in [(tr('Inicio (s)'), self.cue_start), (tr('Final (s)'), self.cue_end),
                                (tr('Repintar desde (+s)'), self.paint_start), (tr('Hasta (+s)'), self.paint_end)]:
            form.addRow(caption, widget)
        self.cue_start.valueChanged.connect(lambda v: self.cue_time('start', v))
        self.cue_end.valueChanged.connect(lambda v: self.cue_time('end', v))
        self.paint_start.valueChanged.connect(lambda v: self.cue_time('paint_start', v))
        self.paint_end.valueChanged.connect(lambda v: self.cue_time('paint_end', v))
        layout.addLayout(form)
        layout.addWidget(self.help_label(tr('Inicio y final son absolutos. El intervalo de repintado se cuenta desde el inicio de la frase.')))
        button = QPushButton(tr('Repintar durante toda la frase'))
        button.clicked.connect(self.reset_paint_interval)
        layout.addWidget(button)
        layout.addWidget(QLabel(tr('Original')))
        self.original_edit = QPlainTextEdit()
        self.original_edit.setMaximumHeight(85)
        layout.addWidget(self.original_edit)
        layout.addWidget(QLabel(tr('Traducción')))
        self.translation_edit = QPlainTextEdit()
        self.translation_edit.setMaximumHeight(85)
        layout.addWidget(self.translation_edit)
        for _track, editor in self.text_editors():
            editor.textChanged.connect(self.text_edited)
        button = QPushButton(tr('Aplicar cambios de texto'))
        button.clicked.connect(self.apply_text)
        layout.addWidget(button)
        layout.addWidget(self.help_label(tr('También puedes editar el texto en la tabla. Cambiar un texto elimina sus marcas de sílabas para evitar animar caracteres equivocados.')))
        self.overflow_label = QLabel('')
        self.overflow_label.setWordWrap(True)
        self.overflow_label.setStyleSheet('color:#ffcb88;')
        layout.addWidget(self.overflow_label)
        layout.addStretch()
        return scroll

    def refresh_table(self):
        old_loading = self.loading
        self.loading = True
        old_row = self.table.currentRow()
        try:
            self.table.setRowCount(len(self.project.cues))
            for i, cue in enumerate(self.project.cues):
                values = [str(i+1), time_text(cue.start), time_text(cue.end), cue.original, cue.translation]
                for col, text in enumerate(values):
                    item = QTableWidgetItem(text)
                    if col == 0:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if col in (1, 2) and not cue.timed:
                        font = item.font()
                        font.setItalic(True)
                        item.setFont(font)
                        item.setForeground(QColor('#7f93ad'))
                        item.setToolTip(tr('Tiempo provisional: márcalo con Ctrl+M o edítalo para confirmarlo.'))
                    self.table.setItem(i, col, item)
            self._shown_target = None  # Items were rebuilt: draw ▶ again.
            if self.project.cues:
                self.table.selectRow(max(0, min(old_row, len(self.project.cues)-1)))
            self.waveform.selected = self.table.currentRow()
        finally:
            self.loading = old_loading
        self.update_mark_target()

    def text_editors(self):
        return (('original', self.original_edit), ('translation', self.translation_edit))

    def pending_text(self):
        """Tracks the user typed in the Frase tab and has not applied yet."""
        if self._text_uid is None:
            return {}
        return {track: self.editor_text(editor) for track, editor in self.text_editors()
                if self.editor_text(editor) != self._text_loaded[track]}

    def all_text_drafts(self):
        """Current box plus drafts of other rows; keep applied text and marks separate."""
        drafts = copy.deepcopy(self._text_drafts)
        pending = self.pending_text()
        if pending:
            drafts[self._text_uid] = pending
        cues = {cue.uid: cue for cue in self.project.cues}
        return {uid: tracks for uid, values in drafts.items() if uid in cues
                if (tracks := {track: text for track, text in values.items()
                               if text != getattr(cues[uid], track)})}

    def update_draft_indicator(self):
        count = len(self.all_text_drafts())
        self.draft_label.setText(tr('{0} frase(s) con texto sin aplicar').format(count) if count else '')

    def text_edited(self):
        if self.loading or self._text_uid is None:
            return
        self.dirty = True
        self.update_draft_indicator()

    def project_with_drafts(self):
        """Persistence snapshot; unapplied text does not enter the renderer or undo stack."""
        project = copy.deepcopy(self.project)
        project.text_drafts = self.all_text_drafts()
        return project

    @staticmethod
    def editor_text(editor):
        """Document text without Qt's plain-text normalization, so U+00A0 survives."""
        return editor.document().toRawText().replace('\u2029', '\n').replace('\u2028', '\n')

    @staticmethod
    def fill_text_editor(editor, text):
        with QSignalBlocker(editor):
            editor.setPlainText(text)

    def load_text_editors(self, cue):
        """Refresh the text boxes without discarding what the user is typing."""
        uid = cue.uid if cue else None
        pending = self.pending_text()
        if pending and uid == self._text_uid:
            # Same phrase: keep the typed boxes, refresh only the untouched ones.
            for track, editor in self.text_editors():
                if track not in pending:
                    self.fill_text_editor(editor, getattr(cue, track))
                    self._text_loaded[track] = self.editor_text(editor)
            return
        if pending:
            self._text_drafts.setdefault(self._text_uid, {}).update(pending)
            self.statusBar().showMessage(tr('La frase anterior conserva su texto sin aplicar. '
                                         'Vuelve a seleccionarla y pulsa «Aplicar cambios de texto».'), 8000)
        self._text_uid = uid
        draft = self._text_drafts.pop(uid, {}) if uid else {}
        for track, editor in self.text_editors():
            self.fill_text_editor(editor, getattr(cue, track) if cue else '')
            self._text_loaded[track] = self.editor_text(editor)
            if track in draft:
                self.fill_text_editor(editor, draft[track])

    def reset_text_editors(self, restore=False):
        """Load saved drafts on opening, or discard them when replacing the lyrics."""
        self._text_uid = None
        self._text_drafts = copy.deepcopy(self.project.text_drafts) if restore else {}
        self.project.text_drafts = {}  # Runtime drafts live in the editors, not in undo snapshots.

    def cue_time(self, key, value, group=True):
        cue = self.selected_cue()
        if self.loading or cue is None:
            return
        if key == 'start' and value >= cue.end or key == 'end' and value <= cue.start:
            self.statusBar().showMessage(tr('El final debe ser mayor que el inicio.'), 5000)
            self.refresh_panels()
            return
        if key == 'paint_start' and value >= (cue.duration if cue.paint_end is None else cue.paint_end):
            self.refresh_panels()
            return
        if key == 'paint_end' and not cue.paint_start < value <= cue.duration:
            self.refresh_panels()
            return
        # Spin-box steps share one undo step; each Ctrl+M/Ctrl+F in zoom is its own (group=False).
        self.record(('cue', cue.uid, key) if group else None)
        previous_duration = cue.duration
        old_paint_start = cue.paint_start
        old_paint_end = cue.duration if cue.paint_end is None else cue.paint_end
        setattr(cue, key, value)
        if key in ('start', 'end'):
            cue.timed = True
            retime_cue(cue, previous_duration)
        else:
            clamp_cue(cue)
            retime_keyframes(cue, old_paint_start, old_paint_end)
        self.changed(tables=True, panels=True)

    def reset_paint_interval(self):
        cue = self.selected_cue()
        if cue:
            self.record()
            old_start = cue.paint_start
            old_end = cue.duration if cue.paint_end is None else cue.paint_end
            cue.paint_start, cue.paint_end = 0, None
            retime_keyframes(cue, old_start, old_end)
            self.changed(panels=True)

    def cue_cell_changed(self, item):
        if self.loading:
            return
        i, col = item.row(), item.column()
        if not 0 <= i < len(self.project.cues) or col == 0:
            return
        cue = self.project.cues[i]
        try:
            if col in (1, 2):
                value = parse_time(item.text())
                if col == 1 and value >= cue.end or col == 2 and value <= cue.start:
                    raise ValueError(tr('El final debe ser mayor que el inicio.'))
                self.record()
                previous_duration = cue.duration
                setattr(cue, 'start' if col == 1 else 'end', value)
                cue.timed = True
                retime_cue(cue, previous_duration)
            else:
                track = 'original' if col == 3 else 'translation'
                if item.text() == getattr(cue, track):
                    return
                if not self.confirm_clear_spans(cue, track):
                    self.refresh_table()
                    return
                self.record()
                setattr(cue, track, item.text().replace('\n', ' '))
                cue.spans(track).clear()
            self.changed(tables=True, panels=True)
        except ValueError as exc:
            self.statusBar().showMessage(str(exc), 6000)
            self.refresh_table()

    def confirm_clear_spans(self, cue, track):
        if not cue.spans(track):
            return True
        return QMessageBox.question(self, tr('Cambiar texto'), tr('Este texto tiene marcas de sílabas. Cambiarlo eliminará sus marcas. ¿Continuar?'),
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def apply_text(self):
        cue = self.selected_cue()
        if not cue:
            return
        changes = {}
        # Only boxes the user edited count: Qt's plain text may differ from the stored text
        # (for example, non-breaking spaces), and that alone must not look like a change.
        pending = self.pending_text() if self._text_uid == cue.uid else {}
        for track, text in pending.items():
            value = text.replace('\n', ' ')
            if value != getattr(cue, track):
                if not self.confirm_clear_spans(cue, track):
                    return
                changes[track] = value
        self._text_uid = None  # Reload both boxes from the phrase after applying.
        if changes:
            self.record()
            for track, value in changes.items():
                setattr(cue, track, value)
                cue.spans(track).clear()
            self.changed(tables=True, panels=True)
        else:
            self.load_text_editors(cue)
        self.update_draft_indicator()

    def add_cue(self):
        self.record()
        start = min(self.position, max(0, self.project.duration - .1))
        # Insert in time order: Ctrl+M and linked navigation walk the list from top to bottom.
        row = next((i for i, c in enumerate(self.project.cues) if c.start > start), len(self.project.cues))
        self.project.cues.insert(row, Cue(start=start, end=min(self.project.duration, start+3), original=tr('Nueva frase'),
                                          timed=False))
        self.changed(tables=True)
        self.table.selectRow(row)
        self.refresh_panels()

    def duplicate_cue(self):
        cue = self.selected_cue()
        if not cue:
            return
        self.record()
        from uuid import uuid4
        duplicate = copy.deepcopy(cue)
        duplicate.uid = uuid4().hex
        duration = cue.duration
        duplicate.start = cue.end
        duplicate.end = duplicate.start + duration
        self.project.duration = max(self.project.duration, duplicate.end)
        row = self.selected_index()+1
        self.project.cues.insert(row, duplicate)
        self.changed(tables=True)
        self.table.selectRow(row)
        self.refresh_panels()

    def delete_cue(self):
        i = self.selected_index()
        if 0 <= i < len(self.project.cues):
            self.record()
            old_uids = [cue.uid for cue in self.project.cues]
            del self.project.cues[i]
            self.remap_marking(old_uids)
            self.changed(tables=True, panels=True)

    def offset_cues(self):
        from PySide6.QtWidgets import QInputDialog
        offset, ok = QInputDialog.getDouble(self, tr('Desplazar tiempos'), tr('Segundos para todas las frases (negativo adelanta):'), 0, -36000, 36000, 3)
        if not ok or offset == 0:
            return
        if any(c.start + offset < 0 for c in self.project.cues):
            QMessageBox.warning(self, tr('Desplazamiento inválido'), tr('Alguna frase quedaría antes de cero. Usa un desplazamiento menor.'))
            return
        self.record()
        for cue in self.project.cues:
            cue.start += offset
            cue.end += offset
        self.project.duration = max(self.project.duration, max((c.end for c in self.project.cues), default=0))
        self.changed(tables=True, panels=True)

    def move_edge(self, edge, value):
        cue = self.selected_cue()
        if not cue:
            return
        if edge == 'start' and value >= cue.end or edge == 'end' and value <= cue.start:
            return
        self.record()
        previous_duration = cue.duration
        setattr(cue, edge, round(value, 3))
        cue.timed = True
        retime_cue(cue, previous_duration)
        self.changed(tables=True, panels=True)
