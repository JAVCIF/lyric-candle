"""0.2.5: zoomed boundary edits must stay on the selected cue."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'windows' if os.name == 'nt' else 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')
from dataclasses import asdict
import unittest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from lyric_candle.app import MainWindow
from lyric_candle.model import Project, Cue, Keyframe, add_span

APP = QApplication.instance() or QApplication([])


class ZoomMarkingTests(unittest.TestCase):
    def setUp(self):
        self.w = MainWindow(demo=False, recover=False)
        self.w.link_selection.setChecked(False)
        self.w.project = Project(duration=15, cues=[Cue(start=i*4, end=i*4+3,
            original=f'Frase {i}', translation=f'Line {i}') for i in range(3)])
        for cue in self.w.project.cues:
            add_span(cue, 'original', 0, 3)
            cue.keyframes = [Keyframe(1, .4), Keyframe(2, .4)]
        self.w.reset_text_editors(); self.w.refresh_all(); self.w.table.selectRow(0)
        self.w.show(); APP.processEvents()
        self.w.history.clear(); self.w.future.clear(); self.w.dirty = False

    def tearDown(self):
        self.w.dirty = False; self.w.close(); APP.processEvents()

    def snapshots(self):
        return [asdict(cue) for cue in self.w.project.cues]

    def test_time_followed_row_uses_zoom_selection_not_first_mark_index(self):
        w = self.w; before = self.snapshots()
        w.link_selection.setChecked(True); w.set_position(5)
        self.assertEqual(w.selected_index(), 1)
        self.assertEqual(w.mark_index, 0)  # The original failure: following isn't a marking sequence.
        w.zoom.setChecked(True); w.seek(4.5)
        QTest.mouseClick(w.mark_start_button, Qt.MouseButton.LeftButton)
        self.assertEqual(w.project.cues[1].start, 4.5)
        self.assertEqual(w.project.cues[1].end, 7)
        self.assertEqual(asdict(w.project.cues[0]), before[0])
        self.assertEqual(asdict(w.project.cues[2]), before[2])
        self.assertEqual(w.selected_index(), 1)

    def test_zoom_waveform_seek_into_previous_phrase_keeps_edit_target(self):
        w = self.w; before = self.snapshots()
        w.table.selectRow(1); w.zoom.setChecked(True); w.link_selection.setChecked(True)
        wave = w.waveform
        point = QPoint(round(wave.time_x(2.8)), 60)  # Visible margin belongs to cue 0.
        QTest.mouseClick(wave, Qt.MouseButton.LeftButton, pos=point)
        self.assertEqual(w.selected_index(), 1)
        w.mark_next()
        self.assertAlmostEqual(w.project.cues[1].start, 2.8, delta=.02)
        self.assertEqual(w.project.cues[1].end, 7)
        self.assertEqual(asdict(w.project.cues[0]), before[0])

    def test_zoom_end_ignores_a_stale_sequential_mark_on_the_first_phrase(self):
        w = self.w; w.table.selectRow(2); w.zoom.setChecked(True)
        w.last_marked = 0; w.mark_index = 1
        before = self.snapshots(); w.seek(11.8)
        QTest.mouseClick(w.mark_end_button, Qt.MouseButton.LeftButton)
        self.assertEqual(w.project.cues[2].end, 11.8)
        self.assertEqual(w.project.cues[2].start, 8)
        self.assertEqual(self.snapshots()[:2], before[:2])
        self.assertEqual(w.selected_index(), 2)
        self.assertEqual(w.last_marked, -1)

    def test_start_and_end_work_on_all_rows_without_advancing(self):
        w = self.w; w.zoom.setChecked(True)
        for linked in (False, True):
            w.link_selection.setChecked(linked)
            for row in range(3):
                with self.subTest(linked=linked, row=row):
                    w.table.selectRow(row); before = self.snapshots()
                    cue = w.selected_cue(); end = cue.end
                    w.seek(cue.start+.1); w.mark_next()
                    self.assertEqual(cue.end, end)
                    w.seek(end-.1); w.mark_end()
                    self.assertAlmostEqual(cue.end, end-.1)
                    self.assertEqual(w.selected_index(), row)
                    for other in range(3):
                        if other != row:self.assertEqual(asdict(w.project.cues[other]), before[other])

    def test_zoom_preserves_selection_during_playback_and_manual_row_changes_work(self):
        w = self.w; w.table.selectRow(2); w.zoom.setChecked(True); w.link_selection.setChecked(True)
        w.set_position(1); self.assertEqual(w.selected_index(), 2)
        w.table.selectRow(1); self.assertEqual(w.selected_index(), 1)
        w.set_position(9); self.assertEqual(w.selected_index(), 1)
        w.zoom.setChecked(False); w.set_position(9)
        self.assertEqual(w.selected_index(), 2)

    def test_local_edit_retimes_marks_and_undo_redo_only_the_selected_cue(self):
        w = self.w; w.table.selectRow(1); w.zoom.setChecked(True)
        before = self.snapshots(); w.seek(4.5); w.mark_next()
        changed = self.snapshots()
        self.assertAlmostEqual(w.project.cues[1].keyframes[0].time, 2.5/3)
        self.assertEqual(w.project.problems(), [])
        w.undo(); self.assertEqual(self.snapshots(), before)
        w.redo(); self.assertEqual(self.snapshots(), changed)

    def test_invalid_or_unchanged_local_boundary_does_not_create_history(self):
        w = self.w; w.table.selectRow(1); w.zoom.setChecked(True)
        before = self.snapshots()
        for time, method in ((7.5, w.mark_next), (3.5, w.mark_end), (4, w.mark_next), (7, w.mark_end)):
            w.seek(time); method()
            self.assertEqual(self.snapshots(), before)
        self.assertEqual(w.history, [])

    def test_unzoomed_marking_still_advances_and_closes_the_previous_phrase(self):
        w = self.w; w.seek(.5); w.mark_next()
        self.assertEqual(w.selected_index(), 1)
        w.seek(4.5); w.mark_next()
        self.assertEqual((w.project.cues[0].start, w.project.cues[0].end), (.5, 4.5))
        self.assertEqual(w.project.cues[1].start, 4.5)
        self.assertEqual(w.selected_index(), 2)


if __name__ == '__main__':
    unittest.main()
