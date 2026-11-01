"""1.0.1: full-screen preview with Space to play/pause and Esc to return."""
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'windows' if os.name == 'nt' else 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')
import unittest

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from lyric_candle.app import MainWindow
from lyric_candle.model import Cue, Project
from lyric_candle.widgets import FullscreenView

APP = QApplication.instance() or QApplication([])


class FullscreenPreviewTests(unittest.TestCase):
    def setUp(self):
        self.w = MainWindow(demo=False, recover=False)
        self.w.project = Project(duration=8, cues=[Cue(start=0, end=4, original='Frase', translation='Line')])
        self.w.refresh_all()
        self.w.show()
        APP.processEvents()
        self.slot = self.w.preview_layout.indexOf(self.w.preview)

    def tearDown(self):
        self.w.exit_fullscreen_preview()
        self.w.pause()
        self.w.dirty = False
        self.w.close()
        APP.processEvents()

    def assert_back_in_editor(self):
        w = self.w
        self.assertIsNone(w.fullscreen_view)
        self.assertEqual(w.preview_layout.indexOf(w.preview), self.slot)
        self.assertTrue(w.preview.isVisible())
        self.assertEqual(w.preview.guides, w.guides.isChecked())
        self.assertEqual(w.preview.backdrop.name(), '#080e18')
        self.assertFalse(w.fullscreen_button.isChecked())

    def test_button_opens_full_screen_and_escape_returns(self):
        w = self.w
        QTest.mouseClick(w.fullscreen_button, Qt.MouseButton.LeftButton)
        view = w.fullscreen_view
        self.assertIsInstance(view, FullscreenView)
        self.assertIs(w.preview.window(), view)
        self.assertTrue(view.isFullScreen())
        self.assertFalse(w.preview.guides)
        self.assertTrue(w.fullscreen_button.isChecked())
        self.assertTrue(view.hint.isVisible())
        QTest.keyClick(w.preview, Qt.Key.Key_Escape)  # The preview has focus; the key reaches the view.
        self.assert_back_in_editor()

    def test_space_plays_and_pauses_while_full_screen(self):
        w = self.w
        w.enter_fullscreen_preview()
        QTest.keyClick(w.preview, Qt.Key.Key_Space)
        self.assertTrue(w.is_playing())
        QTest.keyClick(w.preview, Qt.Key.Key_Space)
        self.assertFalse(w.is_playing())
        QTest.keyClick(w.preview, Qt.Key.Key_Space)
        held = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier, ' ', True)
        QApplication.sendEvent(w.preview, held)  # Holding Space must not flicker play/pause.
        self.assertTrue(w.is_playing())
        w.tick()
        self.assertFalse(w.space_shortcut.isEnabled())  # Only the full-screen view handles Space.
        QTest.keyClick(w.preview, Qt.Key.Key_F11)
        self.assert_back_in_editor()
        self.assertTrue(w.is_playing())  # Playback is not interrupted by leaving full screen.
        self.assertTrue(w.space_shortcut.isEnabled())

    def test_double_click_toggles_and_the_draw_tool_is_turned_off(self):
        w = self.w
        w.area_button.setChecked(True)
        w.area_button.setChecked(False)
        center = QPoint(w.preview.width() // 2, w.preview.height() // 2)
        QTest.mouseDClick(w.preview, Qt.MouseButton.LeftButton, pos=center)
        self.assertIsNotNone(w.fullscreen_view)
        w.exit_fullscreen_preview()
        w.area_button.setChecked(True)
        w.enter_fullscreen_preview()
        self.assertFalse(w.preview.area_tool)
        self.assertFalse(w.area_button.isChecked())
        QTest.mouseDClick(w.preview, Qt.MouseButton.LeftButton, pos=center)
        self.assert_back_in_editor()

    def test_closing_the_full_screen_window_gives_the_preview_back(self):
        w = self.w
        w.enter_fullscreen_preview()
        w.fullscreen_view.close()
        APP.processEvents()
        self.assert_back_in_editor()
        w.enter_fullscreen_preview()
        w.toggle_fullscreen_preview()
        self.assert_back_in_editor()


if __name__ == '__main__':
    unittest.main()
