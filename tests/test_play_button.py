"""Alpha 0.2.3: drawn play/pause icons that follow the playback state."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'windows' if os.name == 'nt' else 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')  # Tests compare Spanish texts.
import unittest
from PySide6.QtWidgets import QApplication
from lyric_candle.app import MainWindow
from lyric_candle.model import Project, Cue
APP = QApplication.instance() or QApplication([])


class PlayButtonTests(unittest.TestCase):
    def test_icon_and_caption_follow_playback(self):
        w = MainWindow(demo=False, recover=False); w.show()
        try:
            w.project = Project(duration=12, cues=[Cue(end=3, original='Luz')]); w.refresh_all(); w.seek(0)
            button = w.play_button
            self.assertFalse(button.icon().isNull()); self.assertEqual(button.text(), 'Reproducir')
            idle = button.icon().pixmap(18, 18).toImage()
            w.play(); w.tick()
            self.assertEqual(button.text(), 'Pausar')
            self.assertNotEqual(button.icon().pixmap(18, 18).toImage(), idle)
            w.pause(); w.tick()
            self.assertEqual(button.text(), 'Reproducir')
            self.assertEqual(button.icon().pixmap(18, 18).toImage(), idle)
        finally:
            w.dirty = False; w.close(); APP.processEvents()


if __name__ == '__main__':
    unittest.main()
