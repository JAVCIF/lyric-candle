"""1.0.1: crossed two-line positions and centered lines kept apart."""
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'windows' if os.name == 'nt' else 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')
import unittest

from PySide6.QtWidgets import QApplication

from lyric_candle.app import MainWindow
from lyric_candle.model import POSITIONS, Cue, Project, from_dict, to_dict
from lyric_candle.render import line_positions

APP = QApplication.instance() or QApplication([])
WIDTHS, ASCENTS, DESCENTS = [200, 300], [30, 30], [8, 8]


def style(position, **values):
    s = Project().style
    s.width, s.height, s.margin, s.layout, s.position = 800, 600, 50, 'two', position
    for key, value in values.items():
        setattr(s, key, value)
    return s


class PositionLayoutTests(unittest.TestCase):
    def test_crossed_sides(self):
        (x_main, y_main), (x_second, y_second) = line_positions(style('left_right_split'), WIDTHS, ASCENTS, DESCENTS)
        self.assertEqual((x_main, x_second), (50, 750 - 300))
        self.assertEqual((y_main, y_second), (80, 542))  # Top and bottom of the area, like *_split.
        (x_main, _), (x_second, _) = line_positions(style('right_left_split'), WIDTHS, ASCENTS, DESCENTS)
        self.assertEqual((x_main, x_second), (750 - 200, 50))

    def test_centered_lines_stay_apart(self):
        s = style('center_split')
        (x_main, y_main), (x_second, y_second) = line_positions(s, WIDTHS, ASCENTS, DESCENTS)
        self.assertEqual((x_main + 100, x_second + 150), (400, 400))
        self.assertEqual((y_main, y_second), (80, 542))
        s.gap = 120  # Spacing only belongs to the stacked «center».
        self.assertEqual(line_positions(s, WIDTHS, ASCENTS, DESCENTS)[1][1], 542)

    def test_positions_follow_the_text_area(self):
        s = style('right_left_split', margin_left=10, margin_right=40, margin_top=100, margin_bottom=120)
        (x_main, y_main), (x_second, y_second) = line_positions(s, WIDTHS, ASCENTS, DESCENTS)
        self.assertEqual((x_main, y_main, x_second, y_second), (800 - 40 - 200, 130, 10, 600 - 120 - 8))

    def test_saved_and_mapped_when_the_layout_cannot_show_them(self):
        project = Project(cues=[Cue()])
        for position in ('left_right_split', 'right_left_split', 'center_split'):
            project.style.position = position
            self.assertEqual(from_dict(to_dict(project)).style.position, position)
        data = to_dict(project)
        for position, expected in (('left_right_split', 'left_top'), ('right_left_split', 'right_top'),
                                   ('center_split', 'center')):
            data['style'].update(layout='one', position=position)
            self.assertEqual(from_dict(data).style.position, expected)


class PositionEditorTests(unittest.TestCase):
    def setUp(self):
        self.w = MainWindow(demo=False, recover=False)
        self.w.project = Project(cues=[Cue(original='Frase', translation='Line')])
        self.w.refresh_all()

    def tearDown(self):
        self.w.dirty = False
        self.w.close()
        APP.processEvents()

    def test_combo_offers_every_two_line_position(self):
        combo = self.w.position_combo
        self.assertEqual([combo.itemData(i) for i in range(combo.count())], list(POSITIONS['two']))
        combo.setCurrentIndex(combo.findData('center_split'))
        self.assertEqual(self.w.project.style.position, 'center_split')
        self.assertFalse(self.w.style_controls['gap'].isEnabled())
        self.w.undo()
        self.assertEqual(self.w.project.style.position, 'left_split')

    def test_switching_to_one_line_keeps_the_main_side(self):
        w = self.w
        for position, expected in (('right_left_split', 'right_top'), ('left_right_split', 'left_top'),
                                   ('center_split', 'center')):
            w.set_style('layout', 'two')
            w.set_style('position', position)
            w.set_style('layout', 'one')
            self.assertEqual(w.project.style.position, expected)


if __name__ == '__main__':
    unittest.main()
