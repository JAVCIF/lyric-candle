"""Ctrl+M / Ctrl+F marking, the single Ctrl+M target, zoomed edits and linked following."""
from __future__ import annotations

from ..i18n import tr
from ..model import retime_cue, time_text


class MarkingMixin:
    """Mixin for MainWindow: Ctrl+M / Ctrl+F marking, the single Ctrl+M target, zoomed edits and linked following."""

    def mark_target(self):
        """The only source of the row Ctrl+M will change; the ▶ marker and mark_next both use it.

        Zoom: the selected row. During a Ctrl+M sequence: the next phrase (mark_index).
        After the last phrase was started and closed: none until a row is chosen.
        Otherwise: the selected row, however it was selected."""
        if self.zoom.isChecked():
            index = self.selected_index()
        elif self.last_marked >= 0:
            index = self.mark_index
        elif self._sequence_done:
            index = None
        else:
            index = self.selected_index()
        return index if index is not None and 0 <= index < len(self.project.cues) else None

    def reset_marking(self):
        """Forget any Ctrl+M sequence and pinned row (new/opened/recovered/imported project)."""
        self.mark_index, self.last_marked = 0, -1
        self._sequence_done = False
        self._pinned_uid = None

    def update_mark_target(self):
        """▶ in the # column of the Ctrl+M target; cheap, so it runs every tick."""
        target = self.mark_target()
        if target == self._shown_target:
            return
        for row in (self._shown_target, target):
            if row is not None and 0 <= row < self.table.rowCount() and self.table.item(row, 0):
                was = self.table.blockSignals(True)
                self.table.item(row, 0).setText(('▶ ' if row == target else '') + str(row+1))
                self.table.item(row, 0).setToolTip(tr('Ctrl+M marcará esta frase.') if row == target else '')
                self.table.blockSignals(was)
        self._shown_target = target

    def cue_selected(self):
        if self.loading or self._following_selection:
            return
        self.mark_index = max(0, self.selected_index())
        self.last_marked = -1
        self._sequence_done = False
        picked = self.selected_cue()
        self._pinned_uid = picked.uid if picked is not None and not picked.timed else None
        self.waveform.selected = self.selected_index()
        self.refresh_panels()
        self.update_labels()
        self.waveform.update()
        cue = self.selected_cue()
        if self.link_selection.isChecked() and cue and cue.timed:
            self.seek(cue.start)

    def cue_clicked(self, row, column):
        cue = self.selected_cue()
        if (self.link_selection.isChecked() and cue and cue.timed and row == self.selected_index()
                and not self.loading and not self._following_selection and abs(self.position-cue.start) > .001):
            self.cue_selected()

    def link_toggled(self, enabled):
        self.settings.setValue('link_selection', enabled)
        if enabled:
            self.follow_time_selection(self.position)

    def follow_time_selection(self, value):
        if self.zoom.isChecked() or not self.link_selection.isChecked() or self.loading or self._following_selection:
            return
        selected = self.selected_cue()
        if selected is not None and selected.uid == self._pinned_uid and not selected.timed:
            return  # A provisional phrase chosen by hand stays the target while it plays elsewhere.
        if 0 <= self.last_marked and self.mark_index < len(self.project.cues):
            # Ctrl+M sequence: keep showing the phrase the next mark will start.
            index = self.mark_index
        else:
            if selected and selected.timed and selected.start <= value < selected.end:
                return
            # Provisional times are placeholders: following them would select phrases that are
            # not being sung yet (and Ctrl+M would then mark the wrong one).
            candidates = [(cue.start, i) for i, cue in enumerate(self.project.cues)
                          if cue.timed and cue.start <= value < cue.end]
            if not candidates:
                return
            index = max(candidates)[1]
        if index == self.selected_index():
            return
        if selected and self.pending_text():
            self.statusBar().showMessage(tr('Aplica los cambios de texto para reanudar el seguimiento automático de frases.'), 6000)
            return
        if self.last_marked < 0:
            self.mark_index = index  # Kept in step with the row on screen (mark_target uses the row).
            self._sequence_done = False
        self._following_selection = True
        try:
            self.table.selectRow(index)
            self.table.scrollToItem(self.table.item(index, 0))
            self.waveform.selected = index
            self.refresh_panels()
            self.update_labels()
        finally:
            self._following_selection = False

    def marking_state(self):
        """Ctrl+M sequence, selection and pinned row, by phrase identity (uid), not position."""
        uids = [cue.uid for cue in self.project.cues]

        def uid(i):
            return uids[i] if 0 <= i < len(uids) else None
        return {'next': uid(self.mark_index), 'past_end': self.mark_index >= len(uids), 'last': uid(self.last_marked),
                'done': self._sequence_done, 'pinned': self._pinned_uid, 'selected': uid(self.selected_index())}

    def restore_marking(self, state):
        """Put the Ctrl+M sequence and selection back as they were when a snapshot was taken."""
        if not state:
            self.reset_marking()
            return
        uids = [cue.uid for cue in self.project.cues]

        def index(u):
            return uids.index(u) if u in uids else -1
        self.last_marked = index(state['last'])
        nxt = index(state['next'])
        self.mark_index = nxt if nxt >= 0 else (len(uids) if state['past_end'] else 0)
        self._sequence_done = state['done']
        self._pinned_uid = state['pinned'] if state['pinned'] in uids else None
        row = index(state['selected'])
        if row >= 0 and row != self.selected_index():
            self.loading = True
            try:
                self.table.selectRow(row)
            finally:
                self.loading = False
            self.waveform.selected = row
            self.refresh_panels()
            self.update_labels()
        self.update_mark_target()

    def remap_marking(self, old_uids):
        """After rows were removed or inserted, keep a running sequence on the same phrases."""
        uids = [cue.uid for cue in self.project.cues]
        if self.last_marked >= 0:
            last = old_uids[self.last_marked] if self.last_marked < len(old_uids) else None
            self.last_marked = uids.index(last) if last in uids else -1  # Its phrase is gone: end the sequence.
        nxt = old_uids[self.mark_index] if self.mark_index < len(old_uids) else None
        if nxt in uids:
            self.mark_index = uids.index(nxt)
        else:  # The target itself was removed: the phrase after it takes its turn.
            following = next((u for u in old_uids[self.mark_index+1:] if u in uids), None)
            self.mark_index = uids.index(following) if following else len(uids)
        if self._pinned_uid not in uids:
            self._pinned_uid = None

    def set_zoom(self, value):
        self.waveform.zoom = value
        self._pinned_uid = None
        self._sequence_done = False
        if value:
            # Local boundary editing must not inherit a previous Ctrl+M sequence.
            self.mark_index = max(0, self.selected_index())
            self.last_marked = -1
        self.mark_start_button.setText(tr('Marcar inicio  [Ctrl+M]') if value else tr('Marcar inicio y avanzar  [Ctrl+M]'))
        self.waveform.update()

    def mark_next(self):
        if self.zoom.isChecked():
            self.mark_selected_edge('start')
            return
        if not self.project.cues:
            return
        index = self.mark_target()
        if index is None:
            self.statusBar().showMessage(tr('Todas las frases están iniciadas. Marca el final o selecciona una fila para volver a marcar.'), 6000)
            return
        t = self.current_time()
        if t >= self.project.duration - .05:
            self.statusBar().showMessage(tr('Retrocede: la frase necesita al menos 0.05 s.'), 5000)
            return
        if self.last_marked >= 0 and t <= self.project.cues[self.last_marked].start:
            self.statusBar().showMessage(tr('La siguiente marca debe estar después de la anterior.'), 5000)
            return
        self.record()
        if self.last_marked >= 0:
            previous = self.project.cues[self.last_marked]
            previous_duration = previous.duration
            previous.end = t
            previous.timed = True
            retime_cue(previous, previous_duration)
        cue = self.project.cues[index]
        # Keep the provisional duration until the next mark closes it. Shrinking it here and
        # stretching it later would pass syllables/keyframes through clamp_cue's minimums.
        previous_duration = cue.duration
        cue.start = t
        cue.end = min(self.project.duration, t + previous_duration)
        cue.timed = True
        retime_cue(cue, previous_duration)
        self.changed(tables=True)
        self.loading = True
        self.table.selectRow(min(index+1, len(self.project.cues)-1))
        self.loading = False
        self.last_marked = index
        self.mark_index = index + 1
        self._pinned_uid = None
        self.waveform.selected = self.selected_index()
        self.refresh_panels()
        self.update_labels()
        if self.mark_index >= len(self.project.cues):
            self.statusBar().showMessage(tr('Última frase iniciada. Usa «Marcar final» al terminar.'), 6000)
        else:
            self.statusBar().showMessage(tr('Frase {0}: inicio en {1}.').format(index+1, time_text(t)), 4000)

    def mark_end(self):
        if self.zoom.isChecked():
            self.mark_selected_edge('end')
            return
        index = self.last_marked if self.last_marked >= 0 else self.selected_index()
        if not 0 <= index < len(self.project.cues):
            return
        cue = self.project.cues[index]
        t = self.current_time()
        if t <= cue.start:
            self.statusBar().showMessage(tr('El final debe estar después del inicio.'), 5000)
            return
        self.record()
        previous_duration = cue.duration
        cue.end = t
        cue.timed = True
        retime_cue(cue, previous_duration)
        self.changed(tables=True, panels=True)
        # Closing the last started phrase ends the pass: an extra Ctrl+M must not re-mark it.
        self._sequence_done = self._sequence_done or (
            self.last_marked >= 0 and self.mark_index >= len(self.project.cues))
        self.last_marked = -1
        self.statusBar().showMessage(tr('Frase {0}: final en {1}.').format(index+1, time_text(t)), 4000)

    def mark_selected_edge(self, edge):
        """In phrase zoom, edit only the selected cue's boundary on the real clock."""
        cue = self.selected_cue()
        if cue is None:
            return
        self.mark_index = self.selected_index()
        self.last_marked = -1
        value = self.current_time()
        if getattr(cue, edge) != value or not cue.timed:  # Marking the placeholder time confirms it.
            before = (cue.start, cue.end, cue.timed)
            self.cue_time(edge, value, group=False)
            if (cue.start, cue.end, cue.timed) != before:
                caption = tr('Frase {0}: inicio en {1}.') if edge == 'start' else tr('Frase {0}: final en {1}.')
                self.statusBar().showMessage(caption.format(self.selected_index()+1, time_text(value)), 4000)
