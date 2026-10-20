"""0.2.3: Spanish/English interface, language choice, quick guide and portable data folder."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'windows' if os.name == 'nt' else 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')  # Tests compare Spanish texts.
import ast
import re
import string
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from PySide6.QtWidgets import (QApplication, QAbstractButton, QLabel, QComboBox, QTabWidget, QTableWidget,
                               QGroupBox, QLineEdit, QPlainTextEdit, QTextBrowser)
from lyric_candle import i18n, paths
from lyric_candle.i18n_en import EN
from lyric_candle.guide import guide_html
APP = QApplication.instance() or QApplication([])
PACKAGE = Path(__file__).resolve().parents[1] / 'lyric_candle'
SPANISH = re.compile(r'[áéíóúñ¿¡]|\b(Frase|frase|Sílaba|Guardar|Abrir|Reproducir|Pausar|Marcar|Desvanec|Repint|Exportar|Ajust|Duración|Fondo|Bucle|Guías|Inicio|Fin|Subir|Escala|Parte)\b')


def tr_keys():
    keys = set()
    for path in PACKAGE.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'tr':
                assert isinstance(node.args[0], ast.Constant), f'{path.name}:{node.lineno} tr() needs a literal'
                keys.add(node.args[0].value)
    return keys


def fields(text):
    return sorted(f'{name}:{spec}!{conv}' for _, name, spec, conv in string.Formatter().parse(text) if name is not None)


class DictionaryTests(unittest.TestCase):
    def test_every_text_has_an_english_version(self):
        missing = sorted(tr_keys() - set(EN))
        self.assertEqual(missing, [], 'Add these to i18n_en.EN')

    def test_placeholders_and_edges_match(self):
        for key, value in EN.items():
            self.assertEqual(fields(key), fields(value), key)
            self.assertEqual((key[:1].isspace(), key[-1:].isspace()), (value[:1].isspace(), value[-1:].isspace()), key)
            self.assertEqual(key.count('\n'), value.count('\n'), key)

    def test_no_stale_entries(self):
        self.assertEqual(sorted(set(EN) - tr_keys()), [])


class LanguageChoiceTests(unittest.TestCase):
    def test_system_language_decides_auto(self):
        with mock.patch.dict(os.environ, {'LYRIC_CANDLE_LANG': ''}):
            self.assertEqual(i18n.resolve('auto', ['es-CO', 'en-US']), 'es')
            self.assertEqual(i18n.resolve('auto', ['es_ES']), 'es')
            self.assertEqual(i18n.resolve('auto', ['pt-BR', 'es-MX']), 'en')  # First preference wins.
            self.assertEqual(i18n.resolve('auto', ['ja-JP']), 'en')
            self.assertEqual(i18n.resolve('auto', []), 'en')
            self.assertEqual(i18n.resolve('es', ['en-US']), 'es')
            self.assertEqual(i18n.resolve('en', ['es-CO']), 'en')

    def test_environment_variable_wins(self):
        with mock.patch.dict(os.environ, {'LYRIC_CANDLE_LANG': 'en'}):
            self.assertEqual(i18n.resolve('es', ['es-CO']), 'en')


class EnglishInterfaceTests(unittest.TestCase):
    def setUp(self):
        i18n.set_language('en')

    def tearDown(self):
        i18n.set_language('es')

    def visible_texts(self, window):
        texts = [window.windowTitle()]
        for action in window.findChildren(type(window.menuBar().actions()[0])):
            texts.append(action.text())
        for widget in window.findChildren(QAbstractButton):
            texts += [widget.text(), widget.toolTip()]
        for widget in window.findChildren(QLabel):
            texts += [widget.text(), widget.toolTip()]
        for widget in window.findChildren(QGroupBox):
            texts.append(widget.title())
        for widget in window.findChildren(QComboBox):
            if not widget.isEditable():
                texts += [widget.itemText(i) for i in range(widget.count())]
            texts.append(widget.toolTip())
        for widget in window.findChildren(QTabWidget):
            texts += [widget.tabText(i) for i in range(widget.count())]
        for widget in window.findChildren(QTableWidget):
            texts += [widget.horizontalHeaderItem(i).text() for i in range(widget.columnCount())
                      if widget.horizontalHeaderItem(i)]
        for kind in (QLineEdit, QPlainTextEdit):
            for widget in window.findChildren(kind):
                texts.append(widget.placeholderText())
        texts.append(window.statusBar().currentMessage())
        return [t for t in texts if t]

    def test_main_window_has_no_spanish_left(self):
        from lyric_candle.app import MainWindow
        from lyric_candle.model import Project, Cue
        w = MainWindow(demo=False, recover=False); w.show()
        try:
            w.project = Project(cues=[Cue(end=3, original='Luz', translation='Light')])
            w.refresh_all(); w.table.selectRow(0); APP.processEvents()
            leftovers = [t for t in self.visible_texts(w) if SPANISH.search(t) and t not in ('Luz', 'Español')]
            self.assertEqual(leftovers, [])
            self.assertEqual(w.play_button.text(), 'Play')
            self.assertEqual([w.tabs.tabText(i) for i in range(w.tabs.count())],
                             ['Line', 'Syllables', 'Design', 'Effects', 'Keyframes'])
            self.assertIn('Line 1: ends after the project.', Project(duration=1, cues=[Cue(end=3)]).problems())
            w.show_help(); APP.processEvents()
            guide = w.help_dialog.findChild(QTextBrowser).toPlainText()
            self.assertIn('Installed or portable', guide); self.assertIn('Ctrl+M', guide)
            w.help_dialog.close()
        finally:
            w.dirty = False; w.close(); APP.processEvents()

    def test_import_dialog_in_english(self):
        from lyric_candle.dialogs import ImportDialog
        dialog = ImportDialog(12)
        self.assertEqual(dialog.windowTitle(), 'Import lyrics · original and translation')
        self.assertEqual(dialog.input_tabs.tabText(1), 'Two columns')
        dialog.combined.setPlainText('Luz\nLight')
        self.assertIn('pair(s) ready', dialog.summary.text())


class GuideAndPortableTests(unittest.TestCase):
    def test_guide_in_both_languages(self):
        es = guide_html('ALPHA 0.2.3', True, r'D:\LyricCandle\data', True)
        self.assertIn('Instalada o portable', es); self.assertIn('portable (se encontró portable.txt)', es)
        self.assertIn(r'D:\LyricCandle\data', es); self.assertIn('Ctrl+M', es)
        i18n.set_language('en')
        try:
            en = guide_html('ALPHA 0.2.3', False, 'C:/Users/x/AppData', False)
        finally:
            i18n.set_language('es')
        self.assertIn('Installed or portable', en); self.assertIn('<b>installed</b>', en); self.assertIn('not found', en)
        self.assertIsNone(SPANISH.search(re.sub(r'<[^>]+>', ' ', en).replace('LEEME', '')))

    def test_portable_marker_moves_data_next_to_the_program(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(paths, 'program_dir', return_value=Path(tmp)):
                self.assertFalse(paths.is_portable())
                self.assertNotEqual(paths.data_dir(), Path(tmp) / 'data')
                (Path(tmp) / 'portable.txt').write_text('')
                self.assertTrue(paths.is_portable())
                self.assertEqual(paths.data_dir(), Path(tmp) / 'data')
                settings = paths.app_settings(); settings.setValue('language', 'en'); settings.sync()
                self.assertTrue((Path(tmp) / 'data' / 'settings.ini').is_file())


if __name__ == '__main__':
    unittest.main()
