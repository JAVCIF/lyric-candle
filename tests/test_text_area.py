"""1.0.1: rectangular text area (per-side margins) and the draw-on-preview tool."""
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'windows' if os.name == 'nt' else 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')
import unittest

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from lyric_candle.app import MainWindow
from lyric_candle.model import SIDES, Cue, Project, from_dict, side_margins, text_area, to_dict
from lyric_candle.render import Renderer, line_positions

APP = QApplication.instance() or QApplication([])


def project_800x600(**sides):
    project = Project(duration=4, cues=[Cue(start=0, end=4, original='Sou, kimi no te de', translation='Así es, con tus manos')])
    s = project.style
    s.width, s.height, s.margin, s.size, s.secondary_size = 800, 600, 78, 36, 36
    for key, value in sides.items():
        setattr(s, key, value)
    return project


class TextAreaModelTests(unittest.TestCase):
    def test_uniform_margin_is_the_default_area(self):
        s = project_800x600().style
        self.assertEqual(text_area(s), (78, 78, 722, 522))
        self.assertEqual(side_margins(s), (78, 78, 78, 78))

    def test_sides_override_the_uniform_margin(self):
        s = project_800x600(margin_left=10, margin_top=110).style
        self.assertEqual(text_area(s), (10, 110, 722, 522))

    def test_round_trip_and_older_projects(self):
        project = project_800x600(margin_left=12, margin_top=95, margin_right=14, margin_bottom=96)
        loaded = from_dict(to_dict(project))
        self.assertEqual(side_margins(loaded.style), (12, 95, 14, 96))
        data = to_dict(project_800x600())
        for key in SIDES:
            del data['style'][key]  # A 1.0.0 project file.
        self.assertEqual(text_area(from_dict(data).style), (78, 78, 722, 522))

    def test_hand_edited_values_fall_back_to_the_margin(self):
        data = to_dict(project_800x600())
        data['style'].update(margin_left=-5, margin_top='20', margin_right=True, margin_bottom=99999)
        self.assertEqual(side_margins(from_dict(data).style), (78, 78, 78, 78))

    def test_area_stays_inside_a_smaller_canvas(self):
        s = project_800x600(margin_left=500, margin_right=500).style
        x0, y0, x1, y1 = text_area(s)
        self.assertGreaterEqual(x0, 0)
        self.assertLessEqual(x1, s.width)
        self.assertAlmostEqual(x1 - x0, 32)


class TextAreaLayoutTests(unittest.TestCase):
    def test_lines_align_to_the_area(self):
        s = project_800x600(margin_left=20, margin_top=100, margin_right=30, margin_bottom=110).style
        s.layout, s.position = 'two', 'left_split'
        (x_top, y_top), (x_bottom, y_bottom) = line_positions(s, [200, 300], [30, 30], [8, 8])
        self.assertEqual((x_top, x_bottom), (20, 20))
        self.assertEqual((y_top, y_bottom), (130, 600 - 110 - 8))
        s.position = 'right_split'
        self.assertEqual(line_positions(s, [200, 300], [30, 30], [8, 8])[0][0], 800 - 30 - 200)
        s.position = 'center'
        (x, _), _ = line_positions(s, [200, 300], [30, 30], [8, 8])
        self.assertEqual(x + 100, (20 + 770) / 2)  # Centred in the area, not in the canvas.

    def test_overflow_uses_the_area_width_and_height(self):
        renderer = Renderer()
        project = project_800x600()
        self.assertFalse(renderer.overflow(project, project.cues[0]))
        project.style.margin_left = project.style.margin_right = 300
        self.assertTrue(renderer.overflow(project, project.cues[0]))
        project = project_800x600(margin_top=270, margin_bottom=270)
        self.assertTrue(renderer.overflow(project, project.cues[0]))


class TextAreaEditorTests(unittest.TestCase):
    def setUp(self):
        self.w = MainWindow(demo=False, recover=False)
        self.w.project = project_800x600()
        self.w.refresh_all()
        self.w.resize(1400, 900)
        self.w.show()
        APP.processEvents()
        self.w.history.clear()
        self.w.future.clear()

    def tearDown(self):
        self.w.preview.set_area_tool(False)
        self.w.dirty = False
        self.w.close()
        APP.processEvents()

    def widget_point(self, x, y):
        scale, dx, dy = self.w.preview.canvas_transform()
        return QPoint(round(dx + x * scale), round(dy + y * scale))

    def drag(self, a, b):
        preview = self.w.preview
        QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=self.widget_point(*a))
        QTest.mouseMove(preview, self.widget_point(*b))
        QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=self.widget_point(*b))
        APP.processEvents()

    def test_side_spin_sets_one_side_and_undoes(self):
        w = self.w
        w.side_spins['margin_left'].setValue(12)
        self.assertEqual(side_margins(w.project.style), (12, 78, 78, 78))
        self.assertEqual(w.project.style.margin_top, None)
        w.undo()
        self.assertEqual(w.project.style.margin_left, None)
        self.assertEqual(w.side_spins['margin_left'].value(), 78)

    def test_uniform_margin_replaces_the_sides(self):
        w = self.w
        w.side_spins['margin_top'].setValue(120)
        w.style_controls['margin'].setValue(40)
        self.assertEqual(side_margins(w.project.style), (40, 40, 40, 40))
        self.assertEqual([w.side_spins[k].value() for k in SIDES], [40] * 4)

    def test_drawing_on_the_preview_sets_the_area(self):
        w = self.w
        w.area_button.setChecked(True)
        self.assertTrue(w.preview.area_tool)
        self.drag((16, 300 - 190), (790, 300 + 190))  # Inside the picture of a letterboxed 4:3 video.
        self.assertFalse(w.preview.area_tool)
        self.assertFalse(w.area_button.isChecked())
        x0, y0, x1, y1 = text_area(w.project.style)
        tolerance = 2 / w.preview.canvas_transform()[0]
        for got, want in zip((x0, y0, x1, y1), (16, 110, 790, 490)):
            self.assertAlmostEqual(got, want, delta=tolerance)
        self.assertEqual(w.side_spins['margin_left'].value(), w.project.style.margin_left)
        self.assertEqual(len(w.history), 1)
        w.undo()
        self.assertEqual(text_area(w.project.style), (78, 78, 722, 522))

    def test_drag_backwards_and_outside_the_canvas_is_clamped(self):
        w = self.w
        w.area_button.setChecked(True)
        preview = w.preview
        start = self.widget_point(700, 500)
        QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=QPoint(-50, -50))
        self.assertEqual(text_area(w.project.style)[:2], (0, 0))

    def test_click_without_drag_and_escape_change_nothing(self):
        w = self.w
        w.area_button.setChecked(True)
        self.drag((100, 100), (110, 105))  # Too small: the tool stays on.
        self.assertTrue(w.preview.area_tool)
        QTest.keyClick(w.preview, Qt.Key.Key_Escape)
        self.assertFalse(w.preview.area_tool)
        self.assertFalse(w.area_button.isChecked())
        self.assertEqual(w.history, [])
        self.assertEqual(side_margins(w.project.style), (78, 78, 78, 78))

    def test_reset_returns_to_the_whole_canvas(self):
        w = self.w
        w.side_spins['margin_bottom'].setValue(5)
        w.history.clear()
        w.reset_text_area()
        self.assertTrue(all(getattr(w.project.style, k) is None for k in SIDES))
        self.assertEqual(len(w.history), 1)
        w.reset_text_area()  # Already reset: no extra undo step.
        self.assertEqual(len(w.history), 1)

    def test_preview_maps_widget_points_to_canvas(self):
        preview = self.w.preview
        scale, dx, dy = preview.canvas_transform()
        point = preview.to_canvas(QPointF(dx + 400 * scale, dy + 300 * scale))
        self.assertAlmostEqual(point.x(), 400, places=3)
        self.assertAlmostEqual(point.y(), 300, places=3)


if __name__ == '__main__':
    unittest.main()
