"""Alpha 0.2.3: base-video canvas/format, moved project files, Separación and keyframe locks."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')  # Tests compare Spanish texts.
import json
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog
from lyric_candle.app import MainWindow
from lyric_candle.media import (ExportWorker, executable, frame_rate, canvas_size, source_settings,
                                stream_info, probe)
from lyric_candle.model import Project, Cue, Keyframe, save, load, to_dict, from_dict
APP = QApplication.instance() or QApplication([])
FFMPEG = executable('ffmpeg') and executable('ffprobe')


def avi_info(codec='mpeg4', tag='XVID', ext='.avi', audio='mp3'):
    return {'ext': ext, 'format': {'bit_rate': '1200000'},
            'video': {'codec_name': codec, 'codec_tag_string': tag, 'width': 640, 'height': 360,
                      'pix_fmt': 'yuv420p', 'avg_frame_rate': '24000/1001'},
            'audio': {'codec_name': audio, 'bit_rate': '128000'} if audio else None}


class ModelTests(unittest.TestCase):
    def test_project_moved_alone_finds_media_by_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp, 'a'), Path(tmp, 'b'); a.mkdir(); b.mkdir()
            media = a / 'movie1_en.avi'; media.write_bytes(b'x')
            save(Project(media=str(media)), a / 'p.lyric.json')
            shutil.move(str(a / 'p.lyric.json'), b / 'p.lyric.json')
            self.assertEqual(Path(load(b / 'p.lyric.json').media), media.resolve())

    def test_project_and_media_moved_together_use_relative_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp, 'a'); (a / 'media').mkdir(parents=True)
            media = a / 'media' / 'song.wav'; media.write_bytes(b'x')
            save(Project(media=str(media)), a / 'p.lyric.json')
            moved = Path(tmp, 'moved'); shutil.move(str(a), moved)
            self.assertEqual(Path(load(moved / 'p.lyric.json').media), (moved / 'media' / 'song.wav').resolve())

    def test_media_next_to_project_is_found_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp, 'a'), Path(tmp, 'b'); a.mkdir(); b.mkdir()
            media = a / 'song.wav'; media.write_bytes(b'x')
            save(Project(media=str(media)), a / 'p.lyric.json')
            shutil.move(str(a / 'p.lyric.json'), b / 'p.lyric.json'); shutil.move(str(media), b / 'song.wav')
            self.assertEqual(Path(load(b / 'p.lyric.json').media), (b / 'song.wav').resolve())

    def test_video_frame_rates_are_accepted(self):
        data = to_dict(Project()); data['style']['fps'] = 23.976024
        self.assertAlmostEqual(from_dict(data).style.fps, 23.976024)
        for bad in (0, 500, 'x', True):
            data['style']['fps'] = bad
            with self.assertRaises(ValueError):
                from_dict(data)

    def test_rates_and_canvas_from_probe(self):
        self.assertAlmostEqual(frame_rate({'avg_frame_rate': '24000/1001'}), 23.976024)
        self.assertEqual(frame_rate({'avg_frame_rate': '0/0', 'r_frame_rate': '25/1'}), 25)
        self.assertEqual(canvas_size({'width': 1920, 'height': 800}), (1920, 800))
        self.assertEqual(canvas_size({'width': 720, 'height': 480, 'sample_aspect_ratio': '32:27'}), (854, 480))
        self.assertEqual(canvas_size({'width': 4096, 'height': 2160}), (3840, 2024))
        self.assertEqual(canvas_size({'width': 160, 'height': 120}), (320, 240))

    def test_source_settings_reproduce_avi_xvid(self):
        settings = source_settings(avi_info(), {'mpeg4', 'libx264'})
        self.assertEqual(settings['ext'], '.avi')
        self.assertEqual(settings['video_args'][:2], ['-c:v', 'mpeg4'])
        self.assertIn('XVID', settings['video_args']); self.assertIn('1072000', settings['video_args'])
        self.assertEqual(settings['audio_args'], ['-c:a', 'copy']); self.assertEqual(settings['note'], '')

    def test_source_settings_fall_back_with_a_note(self):
        settings = source_settings(avi_info(codec='cinepak', tag='cvid'), {'mpeg4', 'libx264'})
        self.assertEqual(settings['video_args'][:2], ['-c:v', 'mpeg4']); self.assertNotIn('-vtag', settings['video_args'])
        self.assertIn('cinepak', settings['note'])
        settings = source_settings(avi_info(codec='h264', ext='.ts'), {'libx264'})
        self.assertEqual(settings['ext'], '.mkv'); self.assertIn('MKV', settings['note'])


class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = MainWindow(demo=False, recover=False); cls.w.show(); APP.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.w.dirty = False; cls.w.close(); APP.processEvents()

    def setUp(self):
        w = self.w; w.pause()
        w.project = Project(duration=4, cues=[Cue(end=3, original='Luz', translation='Light',
                                                  keyframes=[Keyframe(1, .4)])])
        w.history.clear(); w.future.clear(); w.dirty = False
        w.refresh_all(); w.table.selectRow(0); APP.processEvents()

    def test_resolution_shows_the_project_value(self):
        w = self.w
        self.assertEqual(w.resolution.currentText(), '1280 × 720')
        w.resolution.setCurrentIndex(w.resolution.findData('1920x1080'))
        self.assertEqual((w.project.style.width, w.project.style.height), (1920, 1080))
        self.assertEqual(w.resolution.currentText(), '1920 × 1080')
        w.project.style.width, w.project.style.height = 1920, 800; w.refresh_all()
        self.assertEqual(w.resolution.currentText(), '1920 × 800 · personalizada')
        w.fps.setCurrentIndex(w.fps.findData(repr(25.0))); self.assertEqual(w.project.style.fps, 25)

    def test_separation_only_where_it_applies(self):
        w = self.w; gap = w.style_controls['gap']
        w.set_style('layout', 'two'); w.set_style('position', 'left_split'); self.assertFalse(gap.isEnabled())
        w.set_style('position', 'center'); self.assertTrue(gap.isEnabled())
        w.set_style('layout', 'one'); self.assertFalse(gap.isEnabled())

    def drag_point(self, dx, dy):
        curve = self.w.keyframe_curve; self.w.tabs.setCurrentIndex(4); APP.processEvents()
        point = self.w.project.cues[0].keyframes[0]
        start = curve.point_xy(point.time, point.progress).toPoint()
        QTest.mousePress(curve, Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(curve, start + type(start)(dx, dy))
        QTest.mouseRelease(curve, Qt.MouseButton.LeftButton, pos=start + type(start)(dx, dy)); APP.processEvents()
        return self.w.project.cues[0].keyframes[0]

    def test_keyframe_axis_locks(self):
        w = self.w
        w.lock_time.setChecked(True)
        point = self.drag_point(40, -30)
        self.assertEqual(point.time, 1); self.assertGreater(point.progress, .4)
        w.lock_time.setChecked(False); w.lock_progress.setChecked(True)
        before = point.progress; point = self.drag_point(30, 40)
        self.assertGreater(point.time, 1); self.assertAlmostEqual(point.progress, before)
        w.lock_progress.setChecked(False)
        w.history.clear(); self.drag_point(0, 0)
        self.assertEqual(len(w.history), 0)  # A click on a point is not an edit.

    def test_moved_project_offers_to_locate_missing_media(self):
        w = self.w
        with tempfile.TemporaryDirectory() as tmp:
            found = Path(tmp, 'nuevo.wav'); found.write_bytes(b'x')
            w.project.media = str(Path(tmp, 'perdido.wav'))
            with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes), \
                    mock.patch.object(QFileDialog, 'getOpenFileName', return_value=(str(found), '')):
                w.offer_relink()
            self.assertEqual(Path(w.project.media), found.resolve()); self.assertTrue(w.dirty)
            w.project.media = ''; w.set_media_source(force=True)


@unittest.skipUnless(FFMPEG, 'FFmpeg not installed')
class BaseVideoExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.source = Path(cls.tmp.name, 'movie1_en.avi')
        audio = ['-c:a', 'libmp3lame'] if 'libmp3lame' in subprocess.run(
            [executable('ffmpeg'), '-hide_banner', '-encoders'], capture_output=True, text=True).stdout else ['-c:a', 'pcm_s16le']
        subprocess.run([executable('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=size=640x360:rate=24000/1001',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100', '-t', '2',
                        '-c:v', 'mpeg4', '-vtag', 'XVID', '-q:v', '4', *audio, str(cls.source)], check=True)
        cls.audio_codec = stream_info(str(cls.source))['audio']['codec_name']
        cls.w = MainWindow(demo=False, recover=False); cls.w.show(); APP.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.w.dirty = False; cls.w.close(); APP.processEvents(); cls.tmp.cleanup()

    def test_canvas_follows_video_and_export_keeps_its_format(self):
        w = self.w
        w.project = Project(duration=2, media=str(self.source), cues=[Cue(end=1.5, original='Luz')])
        w.refresh_all(); w.set_media_source(force=True, position=0)
        self.assertIn('AVI · 640×360 · 23.976 fps · mpeg4 (XVID)', w.source_label.text())
        w.match_media.setChecked(True)
        s = w.project.style
        self.assertEqual((s.width, s.height), (640, 360)); self.assertAlmostEqual(s.fps, 23.976024)
        self.assertFalse(w.resolution.isEnabled()); self.assertIn('video', w.fps.currentText())
        w.undo(); self.assertFalse(w.project.style.match_media); self.assertEqual(w.project.style.width, 1280)
        w.redo(); w.set_style('export_format', 'source')
        out = Path(self.tmp.name, 'salida.avi')
        job = ExportWorker(w.project, out); job.start()
        deadline = time.monotonic() + 60
        while job.isRunning() and time.monotonic() < deadline:
            APP.processEvents(); job.wait(20)
        APP.processEvents()
        self.assertTrue(out.exists(), job.note)
        info = probe(str(out)); fmt = info['format']
        video = next(st for st in info['streams'] if st['codec_type'] == 'video')
        audio = next(st for st in info['streams'] if st['codec_type'] == 'audio')
        self.assertEqual(fmt['format_name'], 'avi')
        self.assertEqual((video['codec_name'], video['codec_tag_string']), ('mpeg4', 'XVID'))
        self.assertEqual((video['width'], video['height'], video['r_frame_rate']), (640, 360, '24000/1001'))
        self.assertEqual(audio['codec_name'], self.audio_codec)
        self.assertIn('AVI · mpeg4', job.summary)


if __name__ == '__main__':
    unittest.main()
