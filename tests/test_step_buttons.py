"""Real pointer clicks on explicit +/- controls, including the reported Design fields."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')  # Tests compare Spanish texts.
import unittest
from PySide6.QtCore import Qt,QLocale
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from lyric_candle.app import MainWindow
from lyric_candle.model import Project,Cue
from lyric_candle.widgets import StepSpinBox,StepDoubleSpinBox
APP=QApplication.instance() or QApplication([])


class StepButtonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w=MainWindow(demo=False,recover=False);cls.w.show();APP.processEvents()
    @classmethod
    def tearDownClass(cls):
        cls.w.dirty=False;cls.w.close();APP.processEvents()
    def setUp(self):
        w=self.w;w.pause();w.link_selection.setChecked(False)
        w.project=Project(cues=[Cue(end=3,original='Controles')]);w.refresh_all()
        w.table.selectRow(0);w.tabs.setCurrentIndex(2);w.history.clear();w.future.clear();w.dirty=False
        APP.processEvents()
    def click(self,button):
        QTest.mouseClick(button,Qt.MouseButton.LeftButton);APP.processEvents()
    def test_all_reported_design_integer_fields_increment_and_decrement(self):
        self.w.set_style('position','center')  # 0.2.3: Separación only applies to two centred lines.
        for key,value in [('size',70),('secondary_size',65),('margin',20),('gap',20)]:
            box=self.w.style_controls[key];box.setValue(value)
            self.click(box.plus_button)
            self.assertEqual((box.value(),getattr(self.w.project.style,key)),(value+1,value+1))
            self.click(box.minus_button)
            self.assertEqual((box.value(),getattr(self.w.project.style,key)),(value,value))
    def test_outline_decimal_plus_and_minus(self):
        box=self.w.style_controls['outline_width'];box.setValue(2.5)
        self.click(box.plus_button);self.assertEqual((box.value(),self.w.project.style.outline_width),(3,3))
        self.click(box.minus_button);self.assertEqual(box.value(),2.5)
    def test_limits_disable_only_the_unavailable_direction(self):
        box=self.w.style_controls['size'];box.setValue(box.maximum())
        self.assertFalse(box.plus_button.isEnabled());self.assertTrue(box.minus_button.isEnabled())
        self.click(box.minus_button);self.assertTrue(box.plus_button.isEnabled())
        box.setValue(box.minimum())
        self.assertFalse(box.minus_button.isEnabled());self.assertTrue(box.plus_button.isEnabled())
        self.click(box.plus_button);self.assertEqual(box.value(),box.minimum()+1)
    def test_buttons_have_distinct_visible_click_rectangles(self):
        box=self.w.style_controls['size']
        self.assertEqual((box.minus_button.text(),box.plus_button.text()),('−','+'))
        self.assertFalse(box.minus_button.geometry().intersects(box.plus_button.geometry()))
        for button in (box.minus_button,box.plus_button):
            self.assertGreaterEqual(button.width(),24);self.assertTrue(box.rect().contains(button.geometry()))
        self.assertLess(box.minus_button.x(),box.plus_button.x())
    def test_keyboard_entry_and_arrows_keep_working(self):
        box=self.w.style_controls['size'];box.setValue(70)
        box.lineEdit().setText('77');QTest.keyClick(box,Qt.Key.Key_Return);APP.processEvents()
        self.assertEqual(self.w.project.style.size,77)
        QTest.keyClick(box,Qt.Key.Key_Up);APP.processEvents();self.assertEqual(self.w.project.style.size,78)
        QTest.keyClick(box,Qt.Key.Key_Down);APP.processEvents();self.assertEqual(self.w.project.style.size,77)
    def test_decimal_comma_locale(self):
        box=self.w.style_controls['outline_width'];box.setLocale(QLocale(QLocale.Language.Spanish,QLocale.Country.Colombia))
        box.setValue(2.5);self.assertIn(',',box.text())
        self.click(box.plus_button);self.assertEqual(box.value(),3)
        self.click(box.minus_button);self.assertEqual(box.value(),2.5)
    def test_readonly_and_disabled_fields_cannot_step(self):
        box=self.w.style_controls['size'];box.setReadOnly(True)
        self.assertFalse(box.plus_button.isEnabled());self.assertFalse(box.minus_button.isEnabled())
        box.setReadOnly(False);self.assertTrue(box.plus_button.isEnabled())
        self.w.set_style('layout','one')
        secondary=self.w.style_controls['secondary_size']
        self.assertFalse(secondary.plus_button.isEnabled());self.assertFalse(secondary.minus_button.isEnabled())
    def test_repeated_clicks_survive_panel_refresh_and_are_undoable(self):
        box=self.w.style_controls['size'];box.setValue(70);self.w.history.clear()
        for _ in range(3):self.click(box.plus_button)
        for _ in range(2):self.click(box.minus_button)
        # 0.2.3: consecutive steps of one control share a single undo step.
        self.assertEqual(self.w.project.style.size,71);self.assertEqual(len(self.w.history),1)
        self.w.undo();self.assertEqual(self.w.project.style.size,70)
    def test_time_fields_use_the_same_working_buttons(self):
        self.w.tabs.setCurrentIndex(0);APP.processEvents()
        self.assertIsInstance(self.w.cue_start,StepDoubleSpinBox)
        self.click(self.w.cue_start.plus_button)
        self.assertAlmostEqual(self.w.project.cues[0].start,.05)
        self.click(self.w.cue_start.minus_button)
        self.assertAlmostEqual(self.w.project.cues[0].start,0)


if __name__=='__main__':unittest.main()
