"""Alpha 0.2.3: fixed window title, version label from model.VERSION and the logo."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'windows' if os.name == 'nt' else 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')  # Tests compare Spanish texts.
import unittest
from PySide6.QtWidgets import QApplication
from lyric_candle.app import MainWindow, version_label
from lyric_candle.model import VERSION
from lyric_candle.widgets import logo_pixmap, app_icon, LOGO_PATH
APP = QApplication.instance() or QApplication([])


class BrandingTests(unittest.TestCase):
    def test_version_label_comes_from_model(self):
        self.assertEqual(version_label('0.2.3-alpha'), 'ALPHA 0.2.3')
        self.assertEqual(version_label('1.0.0'), '1.0.0')
        self.assertTrue(version_label().endswith(VERSION.split('-')[0]))

    def test_logo_renders(self):
        self.assertTrue(LOGO_PATH.is_file())
        image = logo_pixmap(64).toImage()
        self.assertFalse(image.isNull())
        self.assertEqual(image.pixelColor(32, 32).alpha(), 255)  # Inside the badge.
        self.assertEqual(image.pixelColor(0, 0).alpha(), 0)  # Transparent corner.
        self.assertGreaterEqual(len(app_icon().availableSizes()), 5)

    def test_window_title_is_just_the_app_name(self):
        w = MainWindow(demo=True, recover=False); w.show()
        try:
            w.set_style('size', 50)  # Demo project, unsaved change.
            self.assertEqual(w.windowTitle(), 'Lyric Candle')
            self.assertEqual(w.brand.TEXT, 'Lyric Candle'); self.assertFalse(w.brand.grab().isNull())
        finally:
            w.dirty = False; w.close(); APP.processEvents()


if __name__ == '__main__':
    unittest.main()
