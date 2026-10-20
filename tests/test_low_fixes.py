"""Alpha 0.2.3: low-priority fixes (FFmpeg next to the EXE, lenient opening, recovery per
instance, mark timing, video frame conversion, Space, color cell and waveform)."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'windows' if os.name == 'nt' else 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')  # Tests compare Spanish texts.
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QImage, QColor
from PySide6.QtMultimedia import QVideoFrame
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QAbstractItemView
from lyric_candle import media
from lyric_candle.app import MainWindow
from lyric_candle.model import (Project, Cue, Keyframe, ProjectIssues, load, save, to_dict,
                                from_dict, add_span)
APP = QApplication.instance() or QApplication([])


def invalid_curve_project():
    return Project(cues=[Cue(end=4, original='Luz', keyframes=[Keyframe(1, .6), Keyframe(2, .4)])])


class ModelAndToolTests(unittest.TestCase):
    def test_ffmpeg_next_to_frozen_exe(self):
        with tempfile.TemporaryDirectory() as tmp:
            tools = Path(tmp) / 'tools'; tools.mkdir()
            name = 'ffmpeg' + ('.exe' if os.name == 'nt' else '')
            (tools / name).write_bytes(b'')
            with mock.patch.object(sys, 'frozen', True, create=True), \
                    mock.patch.object(sys, 'executable', str(Path(tmp) / 'LyricCandle.exe')):
                self.assertEqual(Path(media.executable('ffmpeg')), (tools / name).resolve())

    def test_lenient_open_keeps_project_and_lists_issues(self):
        data = to_dict(invalid_curve_project())
        with self.assertRaises(ProjectIssues) as raised:
            from_dict(data)
        self.assertTrue(any('keyframes' in issue for issue in raised.exception.issues))
        project = from_dict(data, strict=False)
        self.assertEqual(len(project.cues[0].keyframes), 2)
        self.assertTrue(project.problems())

    def test_structure_is_still_checked_in_lenient_mode(self):
        data = to_dict(Project()); data['style']['fps'] = 0
        with self.assertRaises(ValueError):
            from_dict(data, strict=False)

    def test_inconsistent_position_and_primary_are_normalized(self):
        data = to_dict(Project())
        data['style'].update(layout='one', position='left_split', primary='otra')
        style = from_dict(data).style
        self.assertEqual((style.position, style.primary), ('left_top', 'original'))
        data['style'].update(layout='two', position='right_bottom')
        self.assertEqual(from_dict(data).style.position, 'right_split')
        data['style'].update(position='???')
        self.assertEqual(from_dict(data).style.position, 'center')


class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = MainWindow(demo=False, recover=False); cls.w.show(); APP.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.w.dirty = False; cls.w.close(); APP.processEvents()

    def setUp(self):
        w = self.w; w.pause(); w.link_selection.setChecked(False)
        w.project = Project(duration=12, cues=[Cue(start=0, end=3, original='Vuelve a brillar'),
                                               Cue(start=3, end=6, original='Otra frase')])
        w.history.clear(); w.future.clear(); w.mark_index = 0; w.last_marked = -1; w.dirty = False
        w.reset_text_editors(); w.refresh_all(); w.table.selectRow(0); w.seek(0); APP.processEvents()

    def test_open_with_issues_asks_and_opens_for_review(self):
        w = self.w
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'revisar.lyric.json'; save(invalid_curve_project(), path)
            with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
                self.assertIsNone(w.load_checked(path, 'Abrir'))
            with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes) as asked:
                project = w.load_checked(path, 'Abrir')
            self.assertIn('keyframes', asked.call_args[0][2])
            w.load_project_path(path, project)
            self.assertTrue(w.issue_label.text())

    def test_undo_never_refuses_its_own_snapshots(self):
        w = self.w; w.project = invalid_curve_project(); w.refresh_all()
        w.set_style('size', 60); w.undo()
        self.assertEqual(len(w.project.cues[0].keyframes), 2); w.redo()
        self.assertEqual(w.project.style.size, 60)

    def test_recovery_is_per_instance(self):
        w = self.w
        legacy = w.recovery_dir / 'recovery.lyric.json'
        save(Project(title='perdido'), legacy, relative=False)
        other = MainWindow(demo=False, recover=False)
        try:
            other.dirty = True; other.autosave(); w.dirty = True; w.autosave()
            orphans = w.orphan_recoveries()
            self.assertIn(legacy, orphans)
            self.assertNotIn(other.recovery_path, orphans)  # Still running.
            self.assertNotIn(w.recovery_path, orphans)
            with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
                w.offer_recovery()
            self.assertEqual(w.project.title, 'perdido'); self.assertFalse(legacy.exists())
            self.assertTrue(w.recovery_path.exists())
        finally:
            other.dirty = False; other.close(); APP.processEvents()
            legacy.unlink(missing_ok=True); w.remove_recovery()
        self.assertFalse(other.recovery_path.exists())

    def test_marks_use_the_clock_at_the_key_press(self):
        w = self.w; w.position = 1.0  # Last tick value, already stale.
        w.virtual_start = 5.0; w.virtual_clock.start(); w.virtual_playing = True
        try:
            w.mark_next()
        finally:
            w.virtual_playing = False
        self.assertGreaterEqual(w.project.cues[0].start, 5.0)
        self.assertLess(w.project.cues[0].start, 5.5)

    def test_video_frames_are_converted_only_for_video_background(self):
        w = self.w; image = QImage(64, 36, QImage.Format.Format_RGBA8888); image.fill(QColor('red'))
        frame = QVideoFrame(image); w.preview.video = None
        w.project.style.background = 'gradient'; w.video_frame(frame)
        self.assertIsNone(w.preview.video)
        w.project.style.background = 'video'; w.video_frame(frame)
        self.assertIsNotNone(w.preview.video)
        w.project.style.background = 'gradient'

    def test_space_plays_from_a_plain_combo_but_not_while_typing_a_font(self):
        w = self.w; w.activateWindow(); w.tabs.setCurrentIndex(2); APP.processEvents()
        w.speed.setFocus(); APP.processEvents(); w.tick()
        if QApplication.focusWidget() is not w.speed:
            self.skipTest('La plataforma sin pantalla no entregó el foco.')
        self.assertTrue(w.space_shortcut.isEnabled())
        w.font_combo.setFocus(); APP.processEvents(); w.tick()
        self.assertFalse(w.space_shortcut.isEnabled())

    def test_double_click_on_color_opens_only_the_dialog(self):
        w = self.w; add_span(w.project.cues[0], 'original', 9, 12); w.tabs.setCurrentIndex(1); w.refresh_all()
        APP.processEvents()
        calls = []
        w.bulk_color = lambda: calls.append(1)
        try:
            self.double_click(w.span_table, 0, 4)
        finally:
            del w.bulk_color
        self.assertEqual(calls, [1])
        self.assertNotEqual(w.span_table.state(), QAbstractItemView.State.EditingState)
        self.double_click(w.span_table, 0, 5)  # Lift still edits on double click.
        self.assertEqual(w.span_table.state(), QAbstractItemView.State.EditingState)
        w.span_table.closePersistentEditor(w.span_table.item(0, 5)); w.span_table.setFocus()

    @staticmethod
    def double_click(table, row, col):
        # A real double click is press, release, double click; QTest's mouseDClick alone
        # skips the first press, so the view would treat it as a new press.
        pos = table.visualItemRect(table.item(row, col)).center()
        QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        QTest.mouseDClick(table.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        APP.processEvents()

    def test_waveform_keeps_short_attacks_and_previews_edge_drag(self):
        wave = self.w.waveform; wave.resize(300, 120)
        wave.peaks = [0.0]*12000; wave.peaks[5003] = 1.0; wave.audio_duration = 12.0
        wave.project.duration = 12.0
        image = wave.grab().toImage()
        # Rows well above the centre line: only a tall (spike) stroke reaches them.
        tall = sum(1 for y in range(35, 60) for x in range(image.width())
                   if QColor(image.pixel(x, y)).blue() > 100)
        self.assertGreater(tall, 10)
        wave.selected = 0; x = round(wave.time_x(3.0))
        QTest.mousePress(wave, Qt.MouseButton.LeftButton, pos=QPoint(x, 80))
        QTest.mouseMove(wave, QPoint(x + 25, 80))
        self.assertGreater(wave.drag_time, 3.0); self.assertEqual(wave.dragging, 'end')
        QTest.mouseRelease(wave, Qt.MouseButton.LeftButton, pos=QPoint(x + 25, 80))
        self.assertIsNone(wave.drag_time)
        self.assertGreater(self.w.project.cues[0].end, 3.0)
        wave.peaks = []


if __name__ == '__main__':
    unittest.main()
