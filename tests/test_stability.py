"""0.2.4: no lost drafts, square-pixel export and rotated-video display geometry."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog
from lyric_candle.app import MainWindow
from lyric_candle.model import Project, Cue, add_span, save, load, to_dict, from_dict
from lyric_candle.media import (ExportWorker, StillFrameWorker, executable, stream_info, canvas_size)

APP = QApplication.instance() or QApplication([])
FFMPEG = executable('ffmpeg')
FFPROBE = executable('ffprobe')


def wait_for(condition, seconds=8):
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:
        APP.processEvents()
        QTest.qWait(10)
    APP.processEvents()
    if not condition():
        raise AssertionError('Timed out waiting for video')


class DraftModelTests(unittest.TestCase):
    def test_saved_drafts_keep_applied_text_marks_and_unicode(self):
        cue = Cue(original='Luz', translation='Light')
        add_span(cue, 'original', 0, 3)
        project = Project(cues=[cue], text_drafts={cue.uid: {'original': 'Luz\u00a0🌟\nNueva línea', 'translation': ''}})
        result = from_dict(to_dict(project))
        self.assertEqual(result.text_drafts, project.text_drafts)
        self.assertEqual(result.cues[0].original, 'Luz')
        self.assertEqual(len(result.cues[0].original_spans), 1)

    def test_legacy_project_without_drafts_still_opens(self):
        data = to_dict(Project())
        del data['text_drafts']
        self.assertEqual(from_dict(data).text_drafts, {})

    def test_malformed_drafts_are_rejected_in_both_load_modes(self):
        cue = Cue(original='Luz')
        for bad in ([], None, {cue.uid: []}, {cue.uid: {'original': 9}}, {cue.uid: {'other': 'x'}}):
            for strict in (True, False):
                with self.subTest(bad=bad, strict=strict):
                    data = to_dict(Project(cues=[cue])); data['text_drafts'] = bad
                    with self.assertRaises(ValueError):
                        from_dict(data, strict=strict)


class DraftEditorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.w = MainWindow(demo=False, recover=False)
        w = self.w
        w.link_selection.setChecked(False)
        w.project = Project(duration=6, cues=[Cue(original='Luz', translation='Light'),
                                              Cue(start=3, end=6, original='Otra', translation='Other')])
        add_span(w.project.cues[0], 'original', 0, 3)
        w.reset_text_editors(); w.refresh_all(); w.table.selectRow(0)
        w.dirty = False

    def tearDown(self):
        self.w.dirty = False; self.w.close(); APP.processEvents()
        self.tmp.cleanup()

    def test_typing_triggers_close_confirmation_and_cancel_keeps_text(self):
        w = self.w
        self.assertFalse(w.dirty)
        w.original_edit.setPlainText('Corrección')
        self.assertTrue(w.dirty)
        self.assertIn('1 frase(s)', w.draft_label.text())
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Cancel) as asked:
            self.assertFalse(w.close())
        self.assertEqual(asked.call_count, 1)
        self.assertEqual(w.original_edit.toPlainText(), 'Corrección')

    def test_save_reopen_preserves_drafts_on_current_and_other_rows(self):
        w = self.w
        w.original_edit.setPlainText('Luz\u00a0🌟\nNueva línea')
        w.table.selectRow(1); w.translation_edit.setPlainText('')
        path = Path(self.tmp.name) / 'drafts.lyric.json'
        self.assertTrue(w.write_project(path))
        saved = load(path)
        self.assertEqual(len(saved.text_drafts), 2)
        self.assertFalse(w.dirty)
        w.load_project_path(path)
        self.assertFalse(w.dirty)  # Loading boxes is not a new user edit.
        w.table.selectRow(0)
        self.assertEqual(w.editor_text(w.original_edit), 'Luz\u00a0🌟\nNueva línea')
        self.assertEqual(w.project.cues[0].original, 'Luz')
        self.assertEqual(len(w.project.cues[0].original_spans), 1)
        w.table.selectRow(1)
        self.assertEqual(w.translation_edit.toPlainText(), '')
        self.assertEqual(w.project.cues[1].translation, 'Other')
        self.assertIn('2 frase(s)', w.draft_label.text())

    def test_save_on_close_keeps_unapplied_text(self):
        w = self.w
        w.path = Path(self.tmp.name) / 'close.lyric.json'
        w.original_edit.setPlainText('Guardar al salir')
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Save):
            self.assertTrue(w.close())
        saved = load(w.path)
        self.assertEqual(saved.cues[0].original, 'Luz')
        self.assertEqual(saved.text_drafts[saved.cues[0].uid]['original'], 'Guardar al salir')

    def test_autosave_recovery_restores_unapplied_text(self):
        w = self.w
        w.recovery_dir = Path(self.tmp.name)
        w.recovery_path = w.recovery_dir / 'recovery-current.lyric.json'
        w.original_edit.setPlainText('Borrador recuperado')
        w.table.selectRow(1); w.translation_edit.setPlainText('Otra traducción')
        w.autosave()
        orphan = w.recovery_dir / 'recovery-old.lyric.json'
        shutil.copy2(w.recovery_path, orphan)
        w.project = Project(); w.reset_text_editors(); w.refresh_all(); w.dirty = False
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            w.offer_recovery()
        w.table.selectRow(0)
        self.assertEqual(w.original_edit.toPlainText(), 'Borrador recuperado')
        w.table.selectRow(1)
        self.assertEqual(w.translation_edit.toPlainText(), 'Otra traducción')
        self.assertTrue(w.recovery_path.exists())

    def test_applying_one_draft_preserves_other_drafts_and_undo(self):
        w = self.w
        w.original_edit.setPlainText('Luz nueva')
        w.table.selectRow(1); w.translation_edit.setPlainText('New translation')
        w.apply_text()
        self.assertEqual(w.project.cues[1].translation, 'New translation')
        self.assertEqual(len(w.all_text_drafts()), 1)
        w.undo(); w.table.selectRow(0)
        self.assertEqual(w.original_edit.toPlainText(), 'Luz nueva')
        self.assertEqual(w.project.cues[1].translation, 'Other')
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            w.apply_text()
        self.assertEqual(w.project.cues[0].original, 'Luz nueva')
        self.assertEqual(w.project.cues[0].original_spans, [])
        self.assertEqual(w.all_text_drafts(), {})
        self.assertEqual(w.draft_label.text(), '')

    def test_timing_style_undo_and_save_leave_drafts_intact(self):
        w = self.w
        w.original_edit.setPlainText('Pendiente A')
        w.table.selectRow(1); w.translation_edit.setPlainText('Pending B')
        w.cue_time('end', 5.5); w.set_style('size', 70); w.undo(); w.redo()
        w.table.selectRow(0)
        self.assertEqual(w.original_edit.toPlainText(), 'Pendiente A')
        w.table.selectRow(1)
        self.assertEqual(w.translation_edit.toPlainText(), 'Pending B')
        self.assertEqual(len(w.project_with_drafts().text_drafts), 2)

    def test_reverting_a_saved_draft_removes_it_from_next_save(self):
        w = self.w
        path = Path(self.tmp.name) / 'p.lyric.json'
        w.original_edit.setPlainText('Borrador'); w.write_project(path); w.load_project_path(path)
        w.original_edit.setPlainText('Luz')
        self.assertTrue(w.dirty)
        self.assertEqual(w.all_text_drafts(), {})
        w.write_project(path)
        self.assertEqual(load(path).text_drafts, {})

    def test_export_stops_at_first_pending_line_before_opening_destination(self):
        w = self.w
        w.original_edit.setPlainText('Pendiente'); w.table.selectRow(1)
        with patch.object(QMessageBox, 'information') as informed, \
                patch.object(QFileDialog, 'getSaveFileName') as choose:
            w.export_video()
        self.assertEqual(informed.call_args.args[1], 'Texto sin aplicar')
        choose.assert_not_called()
        self.assertEqual(w.selected_index(), 0)
        self.assertEqual(w.original_edit.toPlainText(), 'Pendiente')


@unittest.skipUnless(FFMPEG and FFPROBE, 'FFmpeg and ffprobe not installed')
class VideoGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.base = cls.root / 'base.mp4'
        cls.anamorphic = cls.root / 'anamorphic.mp4'
        cls.unknown_sar = cls.root / 'unknown-sar.mp4'
        cls.narrow_pixels = cls.root / 'narrow-pixels.mp4'
        for path, size, filters in ((cls.base, '640x360', 'setsar=1'),
                                    (cls.anamorphic, '720x480', 'setsar=32/27'),
                                    (cls.unknown_sar, '640x360', 'setsar=0'),
                                    (cls.narrow_pixels, '720x480', 'setsar=1/2')):
            subprocess.run([FFMPEG, '-v', 'error', '-f', 'lavfi', '-i',
                            f'color=red:s={size}:r=25,drawbox=x=iw/2:y=0:w=iw/2:h=ih:color=blue:t=fill',
                            '-vf', filters, '-t', '0.4', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)], check=True)
        cls.rotated = {}
        for angle in (90, -90, 180):
            path = cls.root / f'rotated-{angle}.mp4'
            subprocess.run([FFMPEG, '-v', 'error', '-display_rotation', str(angle), '-i', str(cls.base),
                            '-c', 'copy', str(path)], check=True)
            cls.rotated[angle] = path
        cls.anamorphic_rotated = cls.root / 'anamorphic-rotated.mp4'
        subprocess.run([FFMPEG, '-v', 'error', '-display_rotation', '90', '-i', str(cls.anamorphic),
                        '-c', 'copy', str(cls.anamorphic_rotated)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def still(self, path):
        job = StillFrameWorker(str(path), .1)
        images, errors = [], []
        job.ready.connect(images.append); job.failed.connect(errors.append); job.run()
        self.assertEqual(errors, [])
        self.assertTrue(images)
        return images[0]

    def export(self, path, source=False):
        project = Project(duration=.4, media=str(path))
        project.style.width, project.style.height = canvas_size(stream_info(path)['video'])
        project.style.fps = 25; project.style.background = 'video'
        project.style.export_format = 'source' if source else 'mp4'
        destination = self.root / ('out-' + path.name)
        job = ExportWorker(project, destination)
        errors, done = [], []
        job.failed.connect(errors.append); job.done.connect(done.append); job.run()
        self.assertEqual(errors, []); self.assertEqual(done, [str(destination)])
        return self.still(destination), stream_info(destination)['video']

    def assert_filled(self, image):
        # Input has no black bars. Check both axes, well outside codec edge rounding.
        for x, y in ((2, image.height()//4), (image.width()-3, image.height()//4),
                     (image.width()//4, 2), (image.width()//4, image.height()-3)):
            with self.subTest(pixel=(x, y)):
                color = image.pixelColor(x, y)
                self.assertGreater(max(color.red(), color.blue()), 150)

    def test_anamorphic_still_is_square_pixels(self):
        image = self.still(self.anamorphic)
        self.assertEqual((image.width(), image.height()), (854, 480))
        self.assert_filled(image)

    def test_anamorphic_export_has_correct_aspect_and_no_added_bars(self):
        for source in (False, True):
            with self.subTest(source=source):
                image, video = self.export(self.anamorphic, source)
                self.assertEqual((video['width'], video['height']), (854, 480))
                self.assertEqual(video['sample_aspect_ratio'], '1:1')
                self.assert_filled(image)

    def test_rotated_export_uses_display_dimensions_and_correct_orientation(self):
        for angle, path in self.rotated.items():
            with self.subTest(angle=angle):
                expected = (360, 640) if abs(angle) == 90 else (640, 360)
                self.assertEqual(canvas_size(stream_info(path)['video']), expected)
                image, video = self.export(path)
                self.assertEqual((video['width'], video['height']), expected)
                self.assert_filled(image)
                if angle == 90:
                    self.assertGreater(image.pixelColor(180, 30).blue(), 200)
                    self.assertGreater(image.pixelColor(180, 610).red(), 200)
                elif angle == -90:
                    self.assertGreater(image.pixelColor(180, 30).red(), 200)
                    self.assertGreater(image.pixelColor(180, 610).blue(), 200)
                else:
                    self.assertGreater(image.pixelColor(30, 180).blue(), 200)
                    self.assertGreater(image.pixelColor(610, 180).red(), 200)

    def test_anamorphic_rotation_combines_both_display_transforms(self):
        path = self.anamorphic_rotated
        self.assertEqual(canvas_size(stream_info(path)['video']), (480, 854))
        image, video = self.export(path)
        self.assertEqual((video['width'], video['height']), (480, 854))
        self.assert_filled(image)

    def test_missing_and_narrow_pixel_aspects_do_not_collapse_the_image(self):
        for path, expected in ((self.unknown_sar, (640, 360)), (self.narrow_pixels, (360, 480))):
            with self.subTest(source=path.name):
                self.assertEqual(canvas_size(stream_info(path)['video']), expected)
                image, video = self.export(path)
                self.assertEqual((video['width'], video['height']), expected)
                self.assert_filled(image)

    def test_paused_reopen_and_qt_fallback_keep_display_aspect(self):
        from lyric_candle import app as editor
        real_executable = editor.executable
        w = MainWindow(demo=False, recover=False)
        try:
            for path, fallback in ((self.anamorphic, False), (self.rotated[90], False),
                                    (self.anamorphic_rotated, True)):
                with self.subTest(path=path.name, qt_fallback=fallback):
                    project = Project(duration=.4, media=str(path), playhead=.1)
                    project.style.background = 'video'; project.style.match_media = True
                    # A 0.2.3 project may have stored the encoded dimensions instead.
                    project.style.width, project.style.height = (640, 360)
                    saved = self.root / 'paused.lyric.json'; save(project, saved)
                    lookup = (lambda name: None if name == 'ffmpeg' else real_executable(name)) if fallback else real_executable
                    with patch.object(editor, 'executable', side_effect=lookup):
                        w.load_project_path(saved)
                        wait_for(lambda: w.preview.video is not None and not w._warming_video
                                 and w._pending_player_seek is None)
                    image = w.preview.video
                    expected = canvas_size(stream_info(path)['video'])
                    self.assertEqual((w.project.style.width, w.project.style.height), expected)
                    self.assertAlmostEqual(image.width()/image.height(), expected[0]/expected[1], delta=.01)
                    self.assertAlmostEqual(w.position, .1, delta=.04)
                    self.assertFalse(w.is_playing())
                    self.assertNotEqual(w.player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
                    self.assert_filled(image)
        finally:
            w.dirty = False; w.close(); APP.processEvents()

    def test_worker_refuses_a_saved_project_with_unapplied_drafts(self):
        cue = Cue(original='Luz')
        project = Project(cues=[cue], text_drafts={cue.uid: {'original': 'Pendiente'}})
        output = self.root / 'draft-export.mp4'
        job = ExportWorker(project, output); errors = []
        job.failed.connect(errors.append); job.run()
        self.assertTrue(errors); self.assertIn('borradores', errors[0])
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
