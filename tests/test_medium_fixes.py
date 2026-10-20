"""Alpha 0.2.3: NBSP editing, marks inside the repaint window, phrase order, snap with
keyframes and grouped undo for repeated steps."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'windows' if os.name == 'nt' else 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')  # Tests compare Spanish texts.
import unittest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from lyric_candle.app import MainWindow
from lyric_candle.model import (Project, Cue, Span, Keyframe, add_span, propose_spans,
                                snap_spans_to_audio, animation_to_elapsed)
APP = QApplication.instance() or QApplication([])


class ModelFixTests(unittest.TestCase):
    def test_new_mark_is_estimated_inside_repaint_window(self):
        cue = Cue(end=4, original='abcdefghij', paint_end=2.0)
        span = add_span(cue, 'original', 8, 10)
        self.assertLessEqual(span.finish, 2.0); self.assertGreaterEqual(span.start, 0)
        expected = (span.start, span.finish)
        propose_spans(cue, 'original')
        self.assertEqual((cue.original_spans[0].start, cue.original_spans[0].finish), expected)

    def test_snap_uses_real_time_when_keyframes_drive_emphasis(self):
        cue = Cue(end=4, original='Luz', keyframes=[Keyframe(1, .4), Keyframe(3, .4)],
                  original_spans=[Span(0, 3, 2.0, 2.3)])
        self.assertAlmostEqual(animation_to_elapsed(cue, 2.0), 3 + .1/.6)
        peaks = [0.0]*400; peaks[325] = 1.0  # Attack at real 3.25 s.
        self.assertEqual(snap_spans_to_audio(cue, 'original', peaks, 4), 1)
        span = cue.original_spans[0]
        self.assertAlmostEqual(animation_to_elapsed(cue, span.start), 3.25, places=6)
        self.assertAlmostEqual(span.finish-span.start, .3)

    def test_snap_without_curve_is_unchanged(self):
        cue = Cue(end=4, original='Luz', keyframes=[Keyframe(1, .4), Keyframe(3, .4)],
                  keyframe_scope='paint', original_spans=[Span(0, 3, 2.0, 2.3)])
        peaks = [0.0]*400; peaks[210] = 1.0
        snap_spans_to_audio(cue, 'original', peaks, 4)
        self.assertAlmostEqual(cue.original_spans[0].start, 2.1)


class EditorFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = MainWindow(demo=False, recover=False); cls.w.show(); APP.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.w.dirty = False; cls.w.close(); APP.processEvents()

    def setUp(self):
        w = self.w; w.pause(); w.link_selection.setChecked(False)
        w.project = Project(duration=12, cues=[Cue(start=i*3, end=i*3+3, original=f'Frase {i}',
                                                   translation=f'Line {i}') for i in range(3)])
        w.history.clear(); w.future.clear(); w.mark_index = 0; w.last_marked = -1; w.dirty = False
        w.reset_text_editors(); w.refresh_all(); w.table.selectRow(0); w.seek(0); APP.processEvents()

    def test_editing_text_keeps_non_breaking_spaces(self):
        w = self.w; w.project.cues[0].original = 'Bonjour !'; w.refresh_all()
        w.original_edit.setPlainText('Salut !')
        w.apply_text()
        self.assertEqual(w.project.cues[0].original, 'Salut !')

    def test_new_phrase_is_inserted_in_time_order(self):
        w = self.w; w.seek(4); w.add_cue()
        self.assertEqual([c.start for c in w.project.cues], [0, 3, 4, 6])
        self.assertEqual(w.selected_index(), 2); self.assertEqual(w.mark_index, 2)
        w.seek(20); w.add_cue()
        self.assertEqual(w.selected_index(), 4)

    def test_repeated_steps_share_one_undo_entry(self):
        w = self.w; w.tabs.setCurrentIndex(2); APP.processEvents()
        box = w.style_controls['size']; start = w.project.style.size
        for _ in range(6):
            QTest.mouseClick(box.plus_button, Qt.MouseButton.LeftButton); APP.processEvents()
        self.assertEqual(len(w.history), 1)
        w._history_time -= 2  # A pause longer than a second starts a new step.
        QTest.mouseClick(box.plus_button, Qt.MouseButton.LeftButton); APP.processEvents()
        w.set_style('margin', 60)  # Another control: its own step.
        self.assertEqual(len(w.history), 3)
        w.undo(); w.undo(); self.assertEqual(w.project.style.size, start+6)
        w.undo(); self.assertEqual(w.project.style.size, start)
        w.redo(); w.set_style('size', start+10)  # After undo/redo a change never merges.
        self.assertEqual(len(w.history), 2)


if __name__ == '__main__':
    unittest.main()
