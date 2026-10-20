"""Alpha 0.2.3: Ctrl+M timing, unapplied text and linked selection while marking."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')  # Tests compare Spanish texts.
import unittest
from PySide6.QtWidgets import QApplication
from lyric_candle.app import MainWindow
from lyric_candle.model import Project, Cue, Keyframe, add_span, propose_spans
APP = QApplication.instance() or QApplication([])


def syllable_cue(start, end):
    cue = Cue(start=start, end=end, original='a b c d e f g h i j k l', translation='uno dos',
              keyframes=[Keyframe(1, .4), Keyframe(2, .4)])
    for i in range(12):
        add_span(cue, 'original', 2*i, 2*i+1)
    propose_spans(cue, 'original')
    return cue


class MarkingAndTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = MainWindow(demo=False, recover=False)
        cls.prior = cls.w.link_selection.isChecked()
        cls.w.show(); APP.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.w.link_selection.setChecked(cls.prior)
        cls.w.dirty = False; cls.w.close(); APP.processEvents()

    def setUp(self):
        w = self.w; w.pause(); w.link_selection.setChecked(False); w.loop.setChecked(False)
        w.project = Project(duration=40, cues=[syllable_cue(i*4, i*4+4) for i in range(5)])
        w.history.clear(); w.future.clear(); w.mark_index = 0; w.last_marked = -1; w.dirty = False
        w.reset_text_editors(); w.refresh_all(); w.table.selectRow(0); w.seek(0); APP.processEvents()

    def lengths(self, cue):
        return [round(s.finish-s.start, 6) for s in cue.original_spans]

    def test_mark_after_provisional_end_keeps_relative_timing(self):
        w = self.w; cue = w.project.cues[0]
        before, kf = self.lengths(cue), [(k.time, k.progress) for k in cue.keyframes]
        w.seek(20.5); w.mark_next()
        self.assertEqual((cue.start, cue.end), (20.5, 24.5))
        self.assertEqual(self.lengths(cue), before)
        w.seek(24.5); w.mark_next()
        self.assertEqual(self.lengths(cue), before)
        self.assertEqual([(k.time, k.progress) for k in cue.keyframes], kf)
        self.assertEqual(w.project.problems(), [])

    def test_mark_near_project_end_stays_inside_project(self):
        w = self.w; w.table.selectRow(4); w.seek(38); w.mark_next()
        cue = w.project.cues[4]
        self.assertEqual(cue.end, 40)
        self.assertFalse(any('termina después' in p for p in w.project.problems()))

    def test_typed_text_survives_refreshes(self):
        w = self.w; w.table.selectRow(2); APP.processEvents()
        w.original_edit.setPlainText('Texto corregido')
        w.move_edge('end', w.project.cues[2].end + .5)
        w.set_style('size', 50)
        w.undo()
        w.seek(10); w.mark_end()
        self.assertEqual(w.project.cues[2].end, 10)
        self.assertEqual(w.original_edit.toPlainText(), 'Texto corregido')
        w.seek(9); w.mark_next()  # Ctrl+M moves to phrase 3; phrase 2 keeps a draft.
        self.assertEqual(w.selected_index(), 3)
        w.table.selectRow(2); APP.processEvents()
        self.assertEqual(w.original_edit.toPlainText(), 'Texto corregido')
        self.assertEqual(w.translation_edit.toPlainText(), 'uno dos')
        w.confirm_clear_spans = lambda cue, track: True  # Skip the modal question.
        try:
            w.apply_text()
        finally:
            del w.confirm_clear_spans
        self.assertEqual(w.project.cues[2].original, 'Texto corregido')

    def test_switching_rows_keeps_a_draft(self):
        w = self.w; w.table.selectRow(1); APP.processEvents()
        w.translation_edit.setPlainText('borrador')
        w.table.selectRow(3); APP.processEvents()
        self.assertEqual(w.translation_edit.toPlainText(), 'uno dos')
        self.assertEqual(w.project.cues[1].translation, 'uno dos')
        w.table.selectRow(1); APP.processEvents()
        self.assertEqual(w.translation_edit.toPlainText(), 'borrador')
        w.apply_text()
        self.assertEqual(w.project.cues[1].translation, 'borrador')

    def test_non_breaking_space_is_not_an_unapplied_change(self):
        w = self.w; w.project.cues[0].original = 'a b c d e f g h i j k l'
        w.refresh_all(); w.table.selectRow(0)
        self.assertEqual(w.pending_text(), {})
        w.apply_text()  # Must not ask to delete the marks or replace the NBSP.
        self.assertEqual(w.project.cues[0].original, 'a b c d e f g h i j k l')
        self.assertEqual(len(w.project.cues[0].original_spans), 12)
        w.link_selection.setChecked(True); w.set_position(5)
        self.assertEqual(w.selected_index(), 1)

    def test_linked_selection_shows_next_phrase_while_marking(self):
        w = self.w; w.link_selection.setChecked(True)
        w.seek(1); w.mark_next()
        self.assertEqual(w.selected_index(), 1)
        w.set_position(1.5); w.set_position(2)  # Playback ticks inside phrase 0.
        self.assertEqual(w.selected_index(), 1)
        self.assertEqual(w.original_edit.toPlainText(), w.project.cues[1].original)
        w.set_position(3); w.mark_next()
        self.assertEqual(w.project.cues[1].start, 3); self.assertEqual(w.selected_index(), 2)
        w.set_position(4); w.mark_end()
        w.set_position(1.5)  # Sequence closed: follow the active phrase again.
        self.assertEqual(w.selected_index(), 0)


if __name__ == '__main__':
    unittest.main()
