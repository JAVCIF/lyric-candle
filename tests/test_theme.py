"""1.0.1: the same theme on every system, and numeric fields that keep their numbers visible
(Qt 6.12 collapsed the text box of a spin box without native buttons to 1 px)."""
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'windows' if os.name == 'nt' else 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')
import unittest

from PySide6.QtGui import QFontMetrics, QPalette
from PySide6.QtWidgets import QApplication

from lyric_candle.app import MainWindow
from lyric_candle.widgets import StepDoubleSpinBox, StepSpinBox
from lyric_candle.window.common import apply_theme

APP = QApplication.instance() or QApplication([])


class ThemeTests(unittest.TestCase):
    def test_fusion_with_our_selection_colour(self):
        apply_theme(APP)
        self.assertEqual(APP.style().name().lower(), 'fusion')
        self.assertEqual(APP.palette().color(QPalette.ColorRole.Highlight).name(), '#294c70')

    def test_spin_numbers_stay_clear_of_the_step_buttons(self):
        apply_theme(APP)
        w = MainWindow(demo=False, recover=False)
        try:
            w.resize(1500, 900)
            w.tabs.setCurrentIndex(2)  # Design: the panel in the report.
            w.show()
            APP.processEvents()
            spins = [s for s in w.findChildren(StepSpinBox) + w.findChildren(StepDoubleSpinBox) if s.isVisible()]
            self.assertGreater(len(spins), 6)
            for spin in spins:
                with self.subTest(spin=spin.objectName() or spin.text()):
                    edit = spin.lineEdit()
                    self.assertLessEqual(edit.geometry().right(), spin.minus_button.x())
                    self.assertGreaterEqual(edit.width(), QFontMetrics(edit.font()).horizontalAdvance(spin.text()))
        finally:
            w.dirty = False
            w.close()
            APP.processEvents()


if __name__ == '__main__':
    unittest.main()
