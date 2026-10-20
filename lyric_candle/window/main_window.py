"""Lyric Candle main window: layout, menus and shared refresh; behaviour lives in the mixins."""
from __future__ import annotations

import uuid
from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QLocale, QLockFile, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QDesktopServices,
    QFont,
    QKeySequence,
    QShortcut,
)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoSink
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QTableWidget,
    QTabWidget,
    QTextBrowser,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .. import media as media_tools
from ..guide import guide_html
from ..i18n import language, resolve, tr
from ..media import ROOT
from ..model import Cue, Project, load
from ..paths import app_settings, data_dir, is_portable
from ..widgets import (
    BrandMark,
    ColorButton,
    Preview,
    StepDoubleSpinBox,
    Waveform,
    transport_icon,
)
from .common import DARK, version_label
from .cues import CueEditorMixin
from .export import ExportMixin
from .history import HistoryMixin
from .keyframes import KeyframeMixin
from .marking import MarkingMixin
from .project import ProjectMixin
from .style import StyleMixin
from .syllables import SyllableMixin
from .transport import TransportMixin


class MainWindow(TransportMixin, MarkingMixin, CueEditorMixin, SyllableMixin, KeyframeMixin, StyleMixin, HistoryMixin, ProjectMixin, ExportMixin, QMainWindow):

    def __init__(self, demo=True, recover=True):
        super().__init__()
        self.project = Project()
        self.path = None
        self.dirty = False
        self.loading = False
        self._ui_ready = False
        self._following_selection = False
        self._seeking = False
        self.history = []
        self.future = []
        self.export_job = None
        self.wave_job = None
        self.export_dialog = None
        self.loaded_media = ''
        self.adopt_duration = False
        self._source_generation = 0
        self._still_serial = 0
        self.still_jobs = []
        self._pending_player_seek = None
        self._desired_position = 0.0
        self._video_at = None
        self._warming_video = False
        self._prime_mute_before = False
        self.position = 0.0
        # Text boxes of the Frase tab: which cue they show, the text loaded into them
        # (as Qt reports it back) and unapplied drafts of other cues, keyed by uid.
        self._text_uid = None
        self._text_loaded = {'original': '', 'translation': ''}
        self._text_drafts = {}
        self._history_group = None
        self._history_time = 0.0
        self._media_info = (None, None)  # ((path, mtime), stream_info) of the loaded media.
        self.mark_index = 0
        self._shown_target = None
        self._sequence_done = False  # The last phrase was started and closed: no target until a row is picked.
        self._pinned_uid = None  # Provisional phrase picked by hand; automatic following keeps it.
        self.last_marked = -1
        self.virtual_playing = False
        self.virtual_clock = QElapsedTimer()
        self.virtual_start = 0.0
        self.settings = app_settings()
        self.restart_requested = False
        # Each running instance autosaves to its own file, held by a lock file. A recovery
        # file whose lock is free belongs to a session that closed unexpectedly.
        self.recovery_dir = data_dir()
        self.recovery_dir.mkdir(parents=True, exist_ok=True)
        session = 'recovery-' + uuid.uuid4().hex[:12]
        self.recovery_path = self.recovery_dir / (session + '.lyric.json')
        self.recovery_lock = QLockFile(str(self.recovery_dir / (session + '.lock')))
        self.recovery_lock.setStaleLockTime(0)
        self.recovery_lock.tryLock(0)
        self._frame_clock = QElapsedTimer()
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.7)
        self.player.setAudioOutput(self.audio)
        self.sink = QVideoSink(self)
        self.player.setVideoSink(self.sink)
        self.player.positionChanged.connect(self.player_position)
        self.player.durationChanged.connect(self.media_duration)
        self.player.mediaStatusChanged.connect(self.media_status_changed)
        self.player.hasVideoChanged.connect(self.video_available)
        self.player.errorOccurred.connect(lambda error, message: self.statusBar().showMessage(tr('Medio: ') + message, 12000))
        self.sink.videoFrameChanged.connect(self.video_frame)
        self.make_ui()
        self.make_actions()
        self._ui_ready = True
        self.resize(1510, 960)
        self.setMinimumSize(1120, 760)
        self.setStyleSheet(DARK)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(33)
        self.still_timer = QTimer(self)
        self.still_timer.setSingleShot(True)
        self.still_timer.timeout.connect(self.start_still_frame)
        self.prime_timer = QTimer(self)
        self.prime_timer.setSingleShot(True)
        self.prime_timer.timeout.connect(self.finish_video_prime)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave)
        self.autosave_timer.start(20000)
        if demo:
            try:
                self.project = load(ROOT / 'examples' / 'Demo.lyric.json')
            except (OSError, ValueError, TypeError, KeyError):  # Missing or damaged demo file.
                self.project.cues = [Cue(original='Tu primera frase', translation='Your first line')]
        self.refresh_all()
        self.set_media_source()
        self.seek(1.4)
        if recover and self.orphan_recoveries():
            QTimer.singleShot(350, self.offer_recovery)

    def make_ui(self):
        center = QWidget()
        self.setCentralWidget(center)
        outer = QVBoxLayout(center)
        outer.setContentsMargins(12, 8, 12, 8)
        head = QHBoxLayout()
        self.brand = BrandMark()
        head.addWidget(self.brand, 0, Qt.AlignmentFlag.AlignBottom)
        head.addSpacing(10)
        label = QLabel(tr('{0}  ·  escuchar / marcar / animar').format(version_label()))
        label.setStyleSheet('color:#8199b8; padding-bottom:5px;')
        head.addWidget(label, 0, Qt.AlignmentFlag.AlignBottom)
        head.addStretch()
        self.draft_label = QLabel('')
        self.draft_label.setStyleSheet('color:#ffcb88;')
        self.draft_label.setToolTip(tr('Guardar conserva los borradores. Aplica el texto en la pestaña Frase para verlo y exportarlo.'))
        head.addWidget(self.draft_label)
        self.issue_label = QLabel('')
        self.issue_label.setStyleSheet('color:#ffcb88;')
        head.addWidget(self.issue_label)
        outer.addLayout(head)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(self.splitter, 1)
        left = QWidget()
        leftlayout = QVBoxLayout(left)
        leftlayout.setContentsMargins(0, 0, 8, 0)
        self.preview = Preview()
        leftlayout.addWidget(self.preview, 5)
        transport = QHBoxLayout()
        self.play_icons = {False: transport_icon('play'), True: transport_icon('pause')}
        self.play_button = QPushButton()
        self.play_button.setIconSize(QSize(18, 18))
        self.play_button.setMinimumWidth(122)
        self._shown_playing = None
        self.update_play_button()
        self.play_button.clicked.connect(self.toggle_play)
        transport.addWidget(self.play_button)
        self.time_label = QLabel('00:00.000 / 00:12.000')
        transport.addWidget(self.time_label)
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 12000)
        self.seek_slider.valueChanged.connect(lambda v: self.seek(v / 1000))
        transport.addWidget(self.seek_slider, 1)
        self.speed = QComboBox()
        for caption, rate in [('0.5×', .5), ('0.75×', .75), ('1×', 1.0), ('1.25×', 1.25)]:
            self.speed.addItem(caption, rate)
        self.speed.setCurrentIndex(2)
        self.speed.currentIndexChanged.connect(self.change_speed)
        transport.addWidget(self.speed)
        leftlayout.addLayout(transport)
        marks = QHBoxLayout()
        for name, caption, method in [('mark_start_button', tr('Marcar inicio y avanzar  [Ctrl+M]'), self.mark_next),
                                      ('mark_end_button', tr('Marcar final  [Ctrl+F]'), self.mark_end),
                                      ('repeat_cue_button', tr('Repetir frase'), self.play_cue)]:
            button = QPushButton(caption)
            setattr(self, name, button)
            button.clicked.connect(method)
            marks.addWidget(button)
        self.loop = QCheckBox(tr('Bucle'))
        marks.addWidget(self.loop)
        self.zoom = QCheckBox(tr('Zoom frase'))
        self.zoom.setToolTip(tr('Mantiene seleccionada esta frase. Marcar inicio/final ajusta solo sus límites, sin avanzar.'))
        self.zoom.toggled.connect(lambda v: self.set_zoom(v))
        marks.addWidget(self.zoom)
        self.guides = QCheckBox(tr('Guías'))
        self.guides.setChecked(True)
        self.guides.toggled.connect(lambda v: self.set_guides(v))
        marks.addWidget(self.guides)
        leftlayout.addLayout(marks)
        syncrow = QHBoxLayout()
        self.link_selection = QCheckBox(tr('Vincular frase ↔ tiempo'))
        self.link_selection.setChecked(self.settings.value('link_selection', False, type=bool))
        self.link_selection.setToolTip(tr('Seleccionar una frase lleva el cabezal a su inicio. Buscar o reproducir selecciona la frase activa. En los huecos conserva la selección.'))
        self.link_selection.toggled.connect(self.link_toggled)
        syncrow.addWidget(self.link_selection)
        syncrow.addStretch()
        syncrow.addWidget(self.help_label(tr('Lista → inicio de frase · Tiempo → frase activa')))
        leftlayout.addLayout(syncrow)
        self.waveform = Waveform()
        self.waveform.seek.connect(self.seek)
        self.waveform.edge_moved.connect(self.move_edge)
        leftlayout.addWidget(self.waveform)
        tablebar = QHBoxLayout()
        self.cue_count = QLabel(tr('FRASES'))
        tablebar.addWidget(self.cue_count)
        tablebar.addStretch()
        for caption, method in [(tr('+ Frase'), self.add_cue), (tr('Duplicar'), self.duplicate_cue),
                                 (tr('Eliminar'), self.delete_cue), (tr('Desplazar tiempos'), self.offset_cues)]:
            btn = QPushButton(caption)
            btn.clicked.connect(method)
            tablebar.addWidget(btn)
        leftlayout.addLayout(tablebar)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['#', tr('Inicio'), tr('Final'), tr('Original'), tr('Traducción')])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().hide()
        for c, width in [(0, 38), (1, 100), (2, 100)]:
            self.table.setColumnWidth(c, width)
        for col in (3, 4):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self.cue_cell_changed)
        self.table.itemSelectionChanged.connect(self.cue_selected)
        self.table.cellClicked.connect(self.cue_clicked)
        self.table.cellDoubleClicked.connect(lambda row, col: self.seek(self.project.cues[row].start) if col == 0 else None)
        leftlayout.addWidget(self.table, 3)
        self.splitter.addWidget(left)
        self.tabs = QTabWidget()
        self.tabs.setMinimumWidth(345)
        self.tabs.setMaximumWidth(470)
        self.tabs.addTab(self.make_cue_panel(), tr('Frase'))
        self.tabs.addTab(self.make_span_panel(), tr('Sílabas'))
        self.tabs.addTab(self.make_style_panel(), tr('Diseño'))
        self.tabs.addTab(self.make_effect_panel(), tr('Efectos'))
        self.tabs.addTab(self.make_keyframe_panel(), tr('Keyframes'))
        self.splitter.addWidget(self.tabs)
        self.splitter.setSizes([1070, 390])
        self.statusBar().showMessage(tr('Demo lista. Carga tu medio e importa la letra para comenzar.'))

    def scroll_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 12, 12, 12)
        scroll.setWidget(box)
        return scroll, layout

    @staticmethod
    def help_label(text):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet('color:#93a8c5; font-size:11px;')
        return label

    @staticmethod
    def spin(low=0, high=36000, value=0, decimals=3, step=.05):
        box = StepDoubleSpinBox()
        box.setRange(low, high)
        box.setDecimals(decimals)
        box.setSingleStep(step)
        box.setValue(value)
        box.setKeyboardTracking(False)
        return box

    def make_actions(self):
        toolbar = QToolBar(tr('Proyecto'), self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        file_menu = self.menuBar().addMenu(tr('Proyecto'))
        for label, fn, shortcut in [(tr('Nuevo'), self.new_project, 'Ctrl+N'), (tr('Abrir'), self.open_project, 'Ctrl+O'),
                                     (tr('Guardar'), self.save_project, 'Ctrl+S'), (tr('Guardar como…'), self.save_as, 'Ctrl+Shift+S'),
                                     (tr('Importar letra'), self.import_lyrics, 'Ctrl+I'), (tr('Audio / video'), self.choose_media, ''),
                                     (tr('Exportar video'), self.export_video, 'Ctrl+E')]:
            action = QAction(label, self)
            if shortcut:
                action.setShortcut(shortcut)
            action.triggered.connect(fn)
            file_menu.addAction(action)
            if label != tr('Guardar como…'):
                toolbar.addAction(action)
        edit_menu = self.menuBar().addMenu(tr('Edición'))
        for label, fn, key in [(tr('Deshacer'), self.undo, 'Ctrl+Z'), (tr('Rehacer'), self.redo, 'Ctrl+Y'),
                                (tr('Marcar inicio y avanzar'), self.mark_next, 'Ctrl+M'), (tr('Marcar final'), self.mark_end, 'Ctrl+F')]:
            action = QAction(label, self)
            action.setShortcut(key)
            if key in ('Ctrl+M', 'Ctrl+F'):
                action.setAutoRepeat(False)  # Holding the key must not mark several phrases.
            action.triggered.connect(fn)
            edit_menu.addAction(action)
        options_menu = self.menuBar().addMenu(tr('Opciones'))
        language_menu = options_menu.addMenu(tr('Idioma'))
        self.language_group = QActionGroup(self)
        saved = self.settings.value('language', 'auto')
        for code, caption in (('auto', tr('Automático (según el sistema)')), ('es', 'Español'), ('en', 'English')):
            action = QAction(caption, self, checkable=True)
            action.setData(code)
            action.setChecked(code == saved)
            action.triggered.connect(lambda checked=False, c=code: self.choose_language(c))
            self.language_group.addAction(action)
            language_menu.addAction(action)
        action = QAction(tr('Abrir carpeta de datos (ajustes, autoguardado, registro)'), self)
        action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir()))))
        options_menu.addAction(action)
        help_menu = self.menuBar().addMenu(tr('Ayuda'))
        action = QAction(tr('Guía rápida'), self)
        action.setShortcut('F1')
        action.triggered.connect(self.show_help)
        help_menu.addAction(action)
        action = QAction(tr('Cargar demo'), self)
        action.triggered.connect(self.open_demo)
        help_menu.addAction(action)
        self.space_shortcut = QShortcut(QKeySequence('Space'), self)
        self.space_shortcut.activated.connect(self.toggle_play)

    def selected_index(self):
        return self.table.currentRow()

    def selected_cue(self):
        i = self.selected_index()
        return self.project.cues[i] if 0 <= i < len(self.project.cues) else None

    def changed(self, tables=False, panels=False):
        self.dirty = True
        if tables:
            self.refresh_table()
        if panels:
            self.refresh_panels()
        self.preview.project = self.project
        self.waveform.project = self.project
        self.preview.update()
        self.waveform.update()
        self.update_labels()

    def update_labels(self):
        self.setWindowTitle('Lyric Candle')
        self.update_draft_indicator()
        self.cue_count.setText(tr('FRASES · {0}').format(len(self.project.cues)))
        issues = self.project.problems()
        self.issue_label.setText(tr('{0} ajuste(s) pendiente(s)').format(len(issues)) if issues else '')
        self.issue_label.setToolTip('\n'.join(issues[:15]))
        cue = self.selected_cue()
        overflow = cue is not None and self.preview.renderer.overflow(self.project, cue)
        self.overflow_label.setText(tr('⚠ Esta frase excede los márgenes. Reduce el tamaño, edita el texto o divídelo en otra frase.') if overflow else '')
        s = self.project.style
        self.style_controls['secondary_size'].setEnabled(s.layout == 'two')
        stacked = s.layout == 'two' and s.position == 'center'
        self.style_controls['gap'].setEnabled(stacked)
        self.style_controls['gap'].setToolTip(tr('Distancia vertical entre las dos líneas centradas.') if stacked else
                                              tr('Solo se usa con «Dos líneas» en posición «Centro». A izquierda/derecha '
                                              'cada línea va pegada a su margen (arriba y abajo).'))
        advanced = s.mode == 'advanced'
        for name in ('repaint', 'fade', 'lift', 'scale', 'effect_color'):
            self.style_controls[name].setEnabled(advanced)
        self.seek_slider.setMaximum(max(1, int(self.project.duration * 1000)))
        self.media_label.setText(tr('Medio: ') + (Path(self.project.media).name if self.project.media else tr('ninguno · reproducción de prueba sin audio')))

    def refresh_all(self):
        self.loading = True
        try:
            self.preview.project = self.project
            self.waveform.project = self.project
            self.refresh_table()
            self.refresh_panels()
        finally:
            self.loading = False
        self.update_labels()
        self.preview.update()
        self.waveform.update()

    def refresh_panels(self):
        was_loading = self.loading
        self.loading = True
        try:
            s = self.project.style
            for key, widget in self.style_controls.items():
                value = getattr(s, key)
                if isinstance(widget, ColorButton):
                    widget.set_color(value)
                elif isinstance(widget, QComboBox):
                    widget.setCurrentIndex(widget.findData(value))
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(value)
                else:
                    widget.setValue(value)
            self.font_combo.setCurrentFont(QFont(s.font))
            self.fill_positions()
            self.total_duration.setValue(self.project.duration)
            self.fill_canvas_controls()
            self.match_media.setChecked(s.match_media)
            self.update_source_label()
            cue = self.selected_cue()
            if cue:
                self.cue_heading.setText(tr('Frase {0}').format(self.selected_index()+1))
                for widget, val in [(self.cue_start, cue.start), (self.cue_end, cue.end),
                                     (self.paint_start, cue.paint_start),
                                     (self.paint_end, cue.duration if cue.paint_end is None else cue.paint_end)]:
                    widget.setValue(val)
            else:
                self.cue_heading.setText(tr('Agrega una frase'))
            self.load_text_editors(cue)
            for widget in (self.cue_start, self.cue_end, self.paint_start, self.paint_end,
                           self.original_edit, self.translation_edit):
                widget.setEnabled(cue is not None)
            self.refresh_spans()
            self.refresh_keyframes()
        finally:
            self.loading = was_loading

    def show_help(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(tr('Lyric Candle · Guía rápida'))
        dialog.resize(780, 680)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(guide_html(version_label(), is_portable(), str(data_dir()), bool(media_tools.executable('ffmpeg'))))
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(tr('Cerrar'))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        self.help_dialog = dialog  # Reachable from tests; closed with the window.
        dialog.show()

    def choose_language(self, code):
        """Save the choice; the interface is rebuilt in the new language on restart."""
        if self.settings.value('language', 'auto') == code:
            return
        self.settings.setValue('language', code)
        self.settings.sync()
        target = resolve(code, QLocale.system().uiLanguages())
        if target == language():
            return
        # Bilingual on purpose: the reader may not know the current language.
        answer = QMessageBox.question(self, 'Idioma · Language',
                                      'El idioma cambiará al reiniciar Lyric Candle. ¿Reiniciar ahora?\n\n'
                                      'The language will change after restarting Lyric Candle. Restart now?',
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.restart_requested = True
            self.close()
            if not self.isVisible():
                return
            self.restart_requested = False  # Closing was cancelled (unsaved changes, export…).

    def closeEvent(self, event):
        if self.export_job and self.export_job.isRunning():
            QMessageBox.information(self, tr('Exportación activa'), tr('Cancela la exportación o espera a que termine antes de cerrar.'))
            event.ignore()
            return
        self.pause()
        if not self.confirm_unsaved():
            event.ignore()
            return
        if self.wave_job and self.wave_job.isRunning():
            self.wave_job.cancel()
            if not self.wave_job.wait(4000):
                event.ignore()
                return
        self.cancel_still_frames()
        for job in tuple(self.still_jobs):
            if job.isRunning() and not job.wait(4000):
                event.ignore()
                return
        self.still_timer.stop()
        self.prime_timer.stop()
        self.timer.stop()
        self.autosave_timer.stop()
        self.remove_recovery()
        self.recovery_lock.unlock()
        self.player.stop()
        # stop() keeps the decoder/source loaded. Release it as well, so Windows
        # does not keep the media file locked while this closed window survives.
        self.player.setSource(QUrl())
        event.accept()
