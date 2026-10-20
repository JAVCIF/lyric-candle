"""1.0: export only the lyrics as ProRes 4444 with a real alpha channel."""
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'windows' if os.name == 'nt' else 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from lyric_candle.app import MainWindow
from lyric_candle.media import ExportWorker, executable, probe
from lyric_candle.model import Cue, Project, from_dict, to_dict
from lyric_candle.render import Renderer

APP = QApplication.instance() or QApplication([])
FFMPEG = executable('ffmpeg') and executable('ffprobe')


def lyric_project(**style):
    project = Project(duration=1.0, cues=[Cue(start=0, end=1.0, original='LUZ ALFA', translation='ALPHA LIGHT')])
    project.style.width, project.style.height, project.style.fps = 320, 240, 24
    project.style.size, project.style.secondary_size = 48, 36
    project.style.mode = 'repaint'
    for key, value in style.items():
        setattr(project.style, key, value)
    return project


class AlphaRenderTests(unittest.TestCase):
    def test_transparent_frame_keeps_only_the_lyrics(self):
        project = lyric_project(background='gradient')
        normal = Renderer().frame(project, .5)
        alpha = Renderer().frame(project, .5, transparent=True)
        self.assertEqual(normal.pixelColor(0, 0).alpha(), 255)  # Opaque background as before.
        self.assertEqual(alpha.pixelColor(0, 0).alpha(), 0)     # No background at all.
        data = bytes(alpha.constBits())
        alphas = data[3::4]
        self.assertGreater(max(alphas), 250)                    # Solid lyric pixels.
        self.assertGreater(sum(1 for a in alphas if a == 0), len(alphas) // 2)

    def test_alpha_is_straight_not_premultiplied(self):
        # FFmpeg's rgba input expects straight alpha: edge pixels of bright text keep bright
        # colour values above their alpha (impossible in premultiplied data).
        data = bytes(Renderer().frame(lyric_project(), .5, transparent=True).constBits())
        straight = any(10 < data[i+3] < 200 and max(data[i:i+3]) > data[i+3] + 20 for i in range(0, len(data), 4))
        self.assertTrue(straight)

    def test_format_is_saved_and_unknown_values_fall_back(self):
        project = lyric_project(export_format='prores_alpha')
        self.assertEqual(from_dict(to_dict(project)).style.export_format, 'prores_alpha')
        data = to_dict(project); data['style']['export_format'] = 'gif'
        self.assertEqual(from_dict(data).style.export_format, 'mp4')


@unittest.skipUnless(FFMPEG, 'FFmpeg not installed')
class AlphaExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.video = Path(cls.tmp.name, 'base.mp4')  # Video + audio the alpha export must ignore.
        subprocess.run([executable('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=size=320x240:rate=24',
                        '-f', 'lavfi', '-i', 'sine=frequency=440', '-t', '1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', str(cls.video)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def export(self, project, target):
        job = ExportWorker(project, target)
        errors, done = [], []
        job.failed.connect(errors.append); job.done.connect(done.append)
        job.start()
        deadline = time.monotonic() + 60
        while job.isRunning() and time.monotonic() < deadline:
            APP.processEvents(); job.wait(20)
        APP.processEvents()
        self.assertEqual(errors, []); self.assertTrue(done)
        return job

    def test_mov_is_prores_4444_with_alpha_and_no_audio(self):
        project = lyric_project(background='video', export_format='prores_alpha')
        project.media = str(self.video)
        target = Path(self.tmp.name, 'letra-alpha.mov')
        job = self.export(project, target)
        self.assertIn('ProRes 4444', job.summary)
        info = probe(str(target))
        streams = info['streams']
        self.assertEqual([st['codec_type'] for st in streams], ['video'])  # No audio track.
        video = streams[0]
        self.assertEqual((video['codec_name'], video['profile']), ('prores', '4444'))
        self.assertTrue(video['pix_fmt'].startswith('yuva444p'), video['pix_fmt'])
        self.assertEqual((video['width'], video['height'], video['r_frame_rate']), (320, 240, '24/1'))
        frame = subprocess.run([executable('ffmpeg'), '-v', 'error', '-i', str(target), '-vf', 'select=eq(n\\,12)',
                                '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgba', 'pipe:1'],
                               capture_output=True, check=True).stdout
        alphas = frame[3::4]
        self.assertEqual(len(alphas), 320 * 240)
        self.assertEqual(alphas[0], 0)  # The video background is not in the file.
        self.assertGreater(max(alphas), 250)  # The lyrics are.
        self.assertGreater(sum(1 for a in alphas if a == 0), len(alphas) // 2)

    def test_export_dialog_proposes_a_mov(self):
        w = MainWindow(demo=False, recover=False)
        try:
            w.project = lyric_project(export_format='prores_alpha', size=24, secondary_size=18)
            w.project.media = str(self.video)
            w.refresh_all()
            self.assertEqual(w.export_format.itemData(2), 'prores_alpha')
            unexpected = AssertionError('unexpected modal dialog')
            with mock.patch.object(QMessageBox, 'question', side_effect=unexpected), \
                    mock.patch.object(QMessageBox, 'information', side_effect=unexpected), \
                    mock.patch.object(QMessageBox, 'warning', side_effect=unexpected), \
                    mock.patch.object(QFileDialog, 'getSaveFileName', return_value=('', '')) as dialog:
                w.export_video()
            _, _, default, file_filter = dialog.call_args[0]
            self.assertTrue(default.endswith('base-lyrics-alpha.mov'), default)
            self.assertIn('*.mov', file_filter)
        finally:
            w.dirty = False; w.close(); APP.processEvents()


if __name__ == '__main__':
    unittest.main()
