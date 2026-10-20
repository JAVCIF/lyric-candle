from __future__ import annotations
import copy
import json
import logging
import math
import sys
import time
import unicodedata
import uuid
from pathlib import Path
from PySide6.QtCore import (Qt, QTimer, QUrl, QStandardPaths, QSettings, QElapsedTimer, QLockFile, QSize, QLocale,
                            QProcess, QTranslator, QLibraryInfo, QSignalBlocker)
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QFont, QKeySequence, QShortcut, QColor, QImage, QTextCursor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QComboBox, QDoubleSpinBox, QSpinBox, QFormLayout, QTabWidget, QScrollArea, QCheckBox,
    QLineEdit, QPlainTextEdit, QFontComboBox, QSlider, QFileDialog, QMessageBox, QProgressDialog,
    QDialog, QGroupBox, QToolBar, QAbstractSpinBox, QColorDialog, QTextBrowser, QDialogButtonBox)
from .model import (Project, Style, Cue, Keyframe, VERSION, ProjectIssues, load, save, to_dict, from_dict, time_text,
                    parse_time, clamp_cue, retime_cue, add_span, split_spans, propose_spans, snap_spans_to_audio,
                    keyframe_points, animation_progress, animation_to_elapsed, retime_keyframes)
from .widgets import (Preview, Waveform, ColorButton, KeyframeCurve, HoverFontComboBox,
                      StepSpinBox, StepDoubleSpinBox, transport_icon, app_icon, BrandMark)
from .media import (ExportWorker, WaveWorker, StillFrameWorker, ROOT, executable, stream_info, frame_rate,
                    canvas_size, describe_source, SOURCE_CONTAINERS, CONTAINER_NAMES)
from .dialogs import ImportDialog
from .i18n import tr, language, set_language, resolve
from .paths import app_settings, data_dir, is_portable, portable_marker
from .guide import guide_html

DARK = '''
QMainWindow, QDialog, QWidget { background:#0e1623; color:#e3eaf6; font-family:"Segoe UI","DejaVu Sans"; font-size:12px; }
QToolBar { background:#121e30; border:0; spacing:6px; padding:7px; }
QToolButton, QPushButton { background:#20314a; border:1px solid #344b69; padding:6px 10px; border-radius:5px; }
QPushButton:hover,QToolButton:hover { background:#2b4667; }
QPushButton:disabled { color:#677992; background:#182337; }
QLineEdit,QPlainTextEdit,QSpinBox,QDoubleSpinBox,QComboBox,QFontComboBox { background:#162236; border:1px solid #344863; border-radius:4px; padding:4px; selection-background-color:#385e88; }
QLineEdit:disabled,QPlainTextEdit:disabled,QSpinBox:disabled,QDoubleSpinBox:disabled,QComboBox:disabled { color:#677992; background:#111a29; border-color:#263650; }
QCheckBox:disabled { color:#677992; }
QTableWidget { background:#111d2f; alternate-background-color:#162337; gridline-color:#293d59; selection-background-color:#294c70; }
QHeaderView::section { background:#1e2e45; padding:6px; border:0; border-bottom:1px solid #354967; }
QTabWidget::pane { border:1px solid #2c405d; }
QTabBar::tab { background:#17243a; padding:9px 12px; }
QTabBar::tab:selected { background:#2c4664; color:#9dd4ff; }
QScrollArea { border:0; }
QGroupBox { border:1px solid #30435e; border-radius:6px; margin-top:14px; padding-top:10px; }
QGroupBox::title { subcontrol-origin:margin; left:10px; color:#9ed6fa; }
QSlider::groove:horizontal { height:5px; background:#283e59; }
QSlider::handle:horizontal { background:#81c6ff; width:12px; margin:-5px 0; border-radius:5px; }
QStatusBar { color:#9cb0ca; }
QToolTip { color:#e5edfa; background:#253955; border:1px solid #657b9a; }
'''


MEDIA_PATTERNS = '*.mp3 *.wav *.ogg *.flac *.m4a *.aac *.mp4 *.m4v *.mkv *.webm *.mov *.avi *.wmv *.flv *.mpg *.mpeg'


def media_filter():
    # Functions, not constants: the language is chosen after this module is imported.
    return f"{tr('Audio / video')} ({MEDIA_PATTERNS});;{tr('Todos')} (*)"


def image_filter():
    return f"{tr('Imágenes')} (*.png *.jpg *.jpeg *.bmp *.webp)"
RESOLUTIONS = ((1280, 720), (1920, 1080), (1080, 1920), (720, 720))
FPS_PRESETS = (24, 25, 30, 60)


def version_label(version=VERSION):
    """'0.2.3-alpha' -> 'ALPHA 0.2.3'. The number lives only in model.VERSION."""
    number, _, stage = version.partition('-')
    return f'{stage.upper()} {number}'.strip()


def fps_text(fps):
    return f'{fps:.3f}'.rstrip('0').rstrip('.')


class MainWindow(QMainWindow):
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
            except Exception:
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
        for caption, method in [(tr('Marcar inicio y avanzar  [Ctrl+M]'), self.mark_next),
                                 (tr('Marcar final  [Ctrl+F]'), self.mark_end),
                                 (tr('Repetir frase'), self.play_cue)]:
            button = QPushButton(caption)
            button.clicked.connect(method)
            marks.addWidget(button)
        self.loop = QCheckBox(tr('Bucle'))
        marks.addWidget(self.loop)
        self.zoom = QCheckBox(tr('Zoom frase'))
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

    def make_cue_panel(self):
        scroll, layout = self.scroll_panel()
        self.cue_heading = QLabel(tr('Frase seleccionada'))
        self.cue_heading.setStyleSheet('font-size:16px; color:#b8defc;')
        layout.addWidget(self.cue_heading)
        form = QFormLayout()
        self.cue_start = self.spin()
        self.cue_end = self.spin(value=3)
        self.paint_start = self.spin()
        self.paint_end = self.spin(value=3)
        for caption, widget in [(tr('Inicio (s)'), self.cue_start), (tr('Final (s)'), self.cue_end),
                                (tr('Repintar desde (+s)'), self.paint_start), (tr('Hasta (+s)'), self.paint_end)]:
            form.addRow(caption, widget)
        self.cue_start.valueChanged.connect(lambda v: self.cue_time('start', v))
        self.cue_end.valueChanged.connect(lambda v: self.cue_time('end', v))
        self.paint_start.valueChanged.connect(lambda v: self.cue_time('paint_start', v))
        self.paint_end.valueChanged.connect(lambda v: self.cue_time('paint_end', v))
        layout.addLayout(form)
        layout.addWidget(self.help_label(tr('Inicio y final son absolutos. El intervalo de repintado se cuenta desde el inicio de la frase.')))
        button = QPushButton(tr('Repintar durante toda la frase'))
        button.clicked.connect(self.reset_paint_interval)
        layout.addWidget(button)
        layout.addWidget(QLabel(tr('Original')))
        self.original_edit = QPlainTextEdit()
        self.original_edit.setMaximumHeight(85)
        layout.addWidget(self.original_edit)
        layout.addWidget(QLabel(tr('Traducción')))
        self.translation_edit = QPlainTextEdit()
        self.translation_edit.setMaximumHeight(85)
        layout.addWidget(self.translation_edit)
        for _track, editor in self.text_editors():
            editor.textChanged.connect(self.text_edited)
        button = QPushButton(tr('Aplicar cambios de texto'))
        button.clicked.connect(self.apply_text)
        layout.addWidget(button)
        layout.addWidget(self.help_label(tr('También puedes editar el texto en la tabla. Cambiar un texto elimina sus marcas de sílabas para evitar animar caracteres equivocados.')))
        self.overflow_label = QLabel('')
        self.overflow_label.setWordWrap(True)
        self.overflow_label.setStyleSheet('color:#ffcb88;')
        layout.addWidget(self.overflow_label)
        layout.addStretch()
        return scroll

    def make_span_panel(self):
        scroll, layout = self.scroll_panel()
        self.track = QComboBox()
        self.track.addItem(tr('Original'), 'original')
        self.track.addItem(tr('Traducción'), 'translation')
        self.track.currentIndexChanged.connect(self.refresh_spans)
        layout.addWidget(self.track)
        button = QPushButton(tr('Ampliar editor de sílabas'))
        button.clicked.connect(self.expand_span_editor)
        layout.addWidget(button)
        layout.addWidget(self.help_label(tr('Selecciona letras en el texto y pulsa «Marcar selección». Las marcas son rangos del texto; no agregan espacios visibles.')))
        self.span_text = QPlainTextEdit()
        self.span_text.setReadOnly(True)
        self.span_text.setMaximumHeight(78)
        layout.addWidget(self.span_text)
        row = QHBoxLayout()
        btn = QPushButton(tr('Marcar selección'))
        btn.clicked.connect(self.mark_selection)
        row.addWidget(btn)
        btn = QPushButton(tr('Repetir en frases'))
        btn.clicked.connect(self.repeat_selection)
        row.addWidget(btn)
        layout.addLayout(row)
        self.split_edit = QLineEdit()
        self.split_edit.setPlaceholderText(tr('Alternativa: vuel|ve a bri|llar'))
        layout.addWidget(self.split_edit)
        btn = QPushButton(tr('Crear marcas separadas con |'))
        btn.clicked.connect(self.apply_split)
        layout.addWidget(btn)
        layout.addWidget(self.help_label(tr('Tiempos de animación relativos al inicio de la frase. Si usas keyframes para énfasis, la curva reprograma cuándo se alcanzan. Color, subida y escala vacíos heredan el estilo global. ✓ activa el énfasis.')))
        self.span_table = QTableWidget(0, 7)
        self.span_table.setHorizontalHeaderLabels(['✓', tr('Parte'), tr('+Inicio'), tr('+Fin'), tr('Color'), tr('Subir'), tr('Escala')])
        self.span_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.span_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.span_table.verticalHeader().hide()
        for col, width in enumerate([30, 95, 67, 67, 85, 57, 57]):
            self.span_table.setColumnWidth(col, width)
        self.span_table.setMinimumHeight(200)
        # Double click is handled in span_double_click: it edits times/lift/scale, plays a
        # part, or opens the color dialog without also opening the cell editor.
        self.span_table.setEditTriggers(QAbstractItemView.EditTrigger.EditKeyPressed
                                        | QAbstractItemView.EditTrigger.AnyKeyPressed)
        self.span_table.itemChanged.connect(self.span_cell_changed)
        self.span_table.cellDoubleClicked.connect(self.span_double_click)
        layout.addWidget(self.span_table)
        row = QHBoxLayout()
        for caption, fn in [(tr('Estimar tiempos'), self.auto_spans), (tr('Eliminar marcas'), self.remove_spans)]:
            btn = QPushButton(caption)
            btn.clicked.connect(fn)
            row.addWidget(btn)
        layout.addLayout(row)
        btn = QPushButton(tr('Ajustar marcas a ataques del audio (±0.18 s)'))
        btn.clicked.connect(self.snap_audio)
        layout.addWidget(btn)
        row = QHBoxLayout()
        btn = QPushButton(tr('Color a selección'))
        btn.clicked.connect(self.bulk_color)
        row.addWidget(btn)
        btn = QPushButton(tr('Heredar global'))
        btn.clicked.connect(self.inherit_spans)
        row.addWidget(btn)
        layout.addLayout(row)
        layout.addWidget(self.help_label(tr('Estimar reparte por texto. Ajustar al audio busca ataques cercanos: puede seguir instrumentos. No detecta voz ni separa sílabas. Doble clic en una parte: reproducir su momento.')))
        layout.addStretch()
        return scroll

    def make_style_panel(self):
        scroll, layout = self.scroll_panel()
        form = QFormLayout()
        self.style_controls = {}
        self.layout_combo = self.combo([(tr('Una línea'), 'one'), (tr('Dos líneas'), 'two')], lambda v: self.set_style('layout', v))
        self.style_controls['layout'] = self.layout_combo
        form.addRow(tr('Distribución'), self.layout_combo)
        self.position_combo = QComboBox()
        self.position_combo.currentIndexChanged.connect(lambda: self.set_style('position', self.position_combo.currentData()) if not self.loading else None)
        form.addRow(tr('Posición'), self.position_combo)
        self.primary_combo = self.combo([(tr('Original'), 'original'), (tr('Traducción'), 'translation')], lambda v: self.set_style('primary', v))
        self.style_controls['primary'] = self.primary_combo
        form.addRow(tr('Texto principal'), self.primary_combo)
        self.font_combo = HoverFontComboBox()
        self.font_combo.fontHovered.connect(self.font_hover)
        self.font_combo.fontCommitted.connect(self.font_commit)
        self.font_combo.previewEnded.connect(self.font_preview_end)
        form.addRow(tr('Fuente'), self.font_combo)
        self.font_preview_note = self.help_label(tr('Pasa el mouse por una fuente para probarla. Clic para aplicar; Esc para cancelar.'))
        form.addRow(self.font_preview_note)
        for key, caption, lo, hi in [('size', tr('Tamaño principal'), 8, 180), ('secondary_size', tr('Tamaño secundario'), 8, 180),
                                     ('margin', tr('Margen (px)'), 0, 240), ('gap', tr('Separación (px)'), 0, 180)]:
            spin = StepSpinBox()
            spin.setRange(lo, hi)
            spin.setKeyboardTracking(False)
            spin.valueChanged.connect(lambda v, k=key: self.set_style(k, v))
            self.style_controls[key] = spin
            form.addRow(caption, spin)
        for key, caption in [('fill', tr('Relleno inicial')), ('painted', tr('Relleno repintado')), ('outline', tr('Contorno'))]:
            button = ColorButton(getattr(self.project.style, key))
            button.changed.connect(lambda c, k=key: self.set_style(k, c))
            self.style_controls[key] = button
            form.addRow(caption, button)
        width = self.spin(0, 12, decimals=1, step=.5)
        width.valueChanged.connect(lambda v: self.set_style('outline_width', v))
        self.style_controls['outline_width'] = width
        form.addRow(tr('Grosor del contorno'), width)
        layout.addLayout(form)
        layout.addWidget(self.help_label(tr('Principal: arriba en dos líneas; secundario: abajo. Izquierda/derecha comparten margen; centrado comparte eje. Las animaciones nunca redistribuyen las letras.')))
        group = QGroupBox(tr('Lienzo y fondo'))
        gf = QFormLayout(group)
        # Item data are strings: QComboBox.findData compares Python tuples by identity.
        self.resolution = QComboBox()
        self.resolution.currentIndexChanged.connect(self.change_resolution)
        gf.addRow(tr('Resolución'), self.resolution)
        self.fps = QComboBox()
        self.fps.currentIndexChanged.connect(self.change_fps)
        gf.addRow(tr('FPS'), self.fps)
        self.total_duration = self.spin(.1, 36000, value=12)
        self.total_duration.valueChanged.connect(self.change_duration)
        gf.addRow(tr('Duración (s)'), self.total_duration)
        self.background = self.combo([(tr('Degradado'), 'gradient'), (tr('Imagen'), 'image'), (tr('Video del medio'), 'video')], lambda v: self.set_style('background', v))
        self.style_controls['background'] = self.background
        gf.addRow(tr('Fondo'), self.background)
        self.bgcolor = ColorButton(self.project.style.background_color)
        self.bgcolor.changed.connect(lambda c: self.set_style('background_color', c))
        self.style_controls['background_color'] = self.bgcolor
        gf.addRow(tr('Color base'), self.bgcolor)
        btn = QPushButton(tr('Elegir imagen de fondo'))
        btn.clicked.connect(self.choose_image)
        gf.addRow(btn)
        layout.addWidget(group)
        group = QGroupBox(tr('Video base y exportación'))
        vb = QVBoxLayout(group)
        self.match_media = QCheckBox(tr('Usar resolución y FPS del video base'))
        self.match_media.setToolTip(tr('El lienzo toma el tamaño y la velocidad de fotogramas del video cargado. '
                                    'Al cambiar de video se vuelven a leer.'))
        self.match_media.toggled.connect(self.match_media_toggled)
        vb.addWidget(self.match_media)
        ef = QFormLayout()
        self.export_format = self.combo([(tr('MP4 · H.264 + AAC'), 'mp4'), (tr('Igual que el video base'), 'source')],
                                        lambda v: self.set_style('export_format', v))
        self.export_format.setToolTip(tr('«Igual que el video base» usa su contenedor (AVI, MKV, MOV…), su códec de video, '
                                      'formato de píxel y bitrate, y copia su audio sin recodificar.'))
        self.style_controls['export_format'] = self.export_format
        ef.addRow(tr('Exportar como'), self.export_format)
        vb.addLayout(ef)
        self.source_label = self.help_label('')
        vb.addWidget(self.source_label)
        layout.addWidget(group)
        self.media_label = self.help_label(tr('Sin medio'))
        layout.addWidget(self.media_label)
        layout.addStretch()
        return scroll

    # --- Base video -------------------------------------------------------------------
    def media_info(self, quiet=True):
        """ffprobe data of the loaded media, cached per file version; None if unavailable."""
        media = self.project.media
        if not media or not Path(media).is_file() or not executable('ffprobe'):
            return None
        try:
            key = (media, Path(media).stat().st_mtime)
        except OSError:
            return None
        if self._media_info[0] != key:
            try:
                self._media_info = (key, stream_info(media))
            except Exception as exc:  # Unreadable file or ffprobe failure.
                self._media_info = (key, None)
                if not quiet:
                    self.statusBar().showMessage(tr('No se pudo leer el video: ') + str(exc)[:200], 9000)
        return self._media_info[1]

    def base_video_canvas(self):
        """(width, height, fps) of the base video for the canvas, or None with a message."""
        if not executable('ffprobe'):
            self.statusBar().showMessage(tr('Leer el video base necesita ffprobe (tools/ o PATH).'), 9000)
            return None
        info = self.media_info(quiet=False)
        if not info or not info.get('video'):
            self.statusBar().showMessage(tr('Carga un video con «Audio / video» para usar su resolución y FPS.'), 9000)
            return None
        size = canvas_size(info['video'])
        if size is None:
            self.statusBar().showMessage(tr('El video no informa su resolución.'), 9000)
            return None
        return (*size, frame_rate(info['video']))

    def adopt_base_video(self):
        """Copy the base video's size/rate into the style. Caller records undo first."""
        canvas = self.base_video_canvas()
        if canvas is None:
            return False
        s = self.project.style
        s.width, s.height = canvas[0], canvas[1]
        if canvas[2]:
            s.fps = canvas[2]
        return True

    def match_media_toggled(self, enabled):
        s = self.project.style
        if self.loading or enabled == s.match_media:
            return
        if enabled:
            canvas = self.base_video_canvas()
            if canvas is None:
                self.refresh_panels()
                return
            self.record()
            s.width, s.height = canvas[0], canvas[1]
            if canvas[2]:
                s.fps = canvas[2]
        else:
            self.record()  # Keep the video's values; they become editable again.
        s.match_media = enabled
        self.changed(panels=True)

    def update_source_label(self):
        s = self.project.style
        info = self.media_info()
        if not self.project.media:
            text = tr('Sin medio. Carga un video para usar su resolución, FPS y formato.')
        elif not executable('ffprobe'):
            text = tr('Instala ffprobe para leer las propiedades del video base.')
        elif info is None:
            text = tr('No se pudieron leer las propiedades del medio.')
        else:
            text = tr('Video base: ') + describe_source(info)
            video = info.get('video')
            if video:
                size, rate = canvas_size(video), frame_rate(video)
                if size and (size != (s.width, s.height) or (rate and abs(rate - s.fps) > 1e-3)):
                    text += tr('\nEl lienzo ({0}×{1} · {2} fps) no coincide con el video.').format(s.width, s.height, fps_text(s.fps))
                elif size and (size[0], size[1]) != (int(video.get('width') or 0), int(video.get('height') or 0)):
                    text += tr('\nLienzo ajustado a {0}×{1} (rotación, píxeles no cuadrados o límites de tamaño).').format(size[0], size[1])
        self.source_label.setText(text)
        has_video = bool(info and info.get('video'))
        self.match_media.setEnabled(has_video or s.match_media)
        self.resolution.setEnabled(not s.match_media)
        self.fps.setEnabled(not s.match_media)

    def fill_canvas_controls(self):
        s = self.project.style
        self.resolution.clear()
        for w, h in RESOLUTIONS:
            self.resolution.addItem(f'{w} × {h}', f'{w}x{h}')
        key = f'{s.width}x{s.height}'
        if self.resolution.findData(key) < 0:
            self.resolution.addItem(f'{s.width} × {s.height} · ' + ('video' if s.match_media else tr('personalizada')), key)
        self.resolution.setCurrentIndex(self.resolution.findData(key))
        self.fps.clear()
        for value in FPS_PRESETS:
            self.fps.addItem(str(value), repr(float(value)))
        key = repr(float(s.fps))
        if self.fps.findData(key) < 0:
            self.fps.addItem(fps_text(s.fps) + (tr(' · video') if s.match_media else ''), key)
        self.fps.setCurrentIndex(self.fps.findData(key))

    def make_effect_panel(self):
        scroll, layout = self.scroll_panel()
        form = QFormLayout()
        self.mode_combo = self.combo([(tr('1 · Repintado'), 'repaint'), (tr('2 · Desvanecimiento'), 'fade'),
                                      (tr('3 · Avanzado por sílabas'), 'advanced')], lambda v: self.set_style('mode', v))
        self.style_controls['mode'] = self.mode_combo
        form.addRow(tr('Modo'), self.mode_combo)
        layout.addLayout(form)
        layout.addWidget(self.help_label(tr('Repintado conserva la frase hasta su salida. Desvanecimiento usa opacidad. Avanzado combina ambos con las partes marcadas en «Sílabas».')))
        for key, caption in [('repaint', tr('Repintar en modo avanzado')), ('fade', tr('Desvanecer en modo avanzado')),
                              ('crossfade', tr('Solapar la salida con la siguiente frase'))]:
            check = QCheckBox(caption)
            check.toggled.connect(lambda v, k=key: self.set_style(k, v))
            self.style_controls[key] = check
            layout.addWidget(check)
        form = QFormLayout()
        for key, caption, lo, hi, step, dec in [('fade_in', tr('Entrada (s)'), 0, 3, .05, 2),
                                              ('fade_out', tr('Salida (s)'), 0, 3, .05, 2),
                                              ('lift', tr('Subida global (px)'), -100, 160, 1, 1),
                                              ('scale', tr('Escala global'), .5, 3, .05, 2)]:
            spin = self.spin(lo, hi, decimals=dec, step=step)
            spin.valueChanged.connect(lambda v, k=key: self.set_style(k, v))
            self.style_controls[key] = spin
            form.addRow(caption, spin)
        color = ColorButton(self.project.style.effect_color)
        color.changed.connect(lambda c: self.set_style('effect_color', c))
        self.style_controls['effect_color'] = color
        form.addRow(tr('Color de énfasis'), color)
        layout.addLayout(form)
        layout.addWidget(self.help_label(tr('Subida 0 y escala 1 desactivan el movimiento y el crecimiento. Cada marca puede sobrescribir estos valores. El énfasis regresa suavemente a la posición original.')))
        layout.addWidget(self.help_label(tr('Con solapado, la salida continúa después del final de la frase. Sin solapado, termina dentro de su intervalo. La duración del proyecto siempre recorta el resultado final.')))
        btn = QPushButton(tr('Abrir editor de sílabas'))
        btn.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        layout.addWidget(btn)
        layout.addStretch()
        return scroll

    def combo(self, items, callback):
        box = QComboBox()
        for label, data in items:
            box.addItem(label, data)
        box.currentIndexChanged.connect(lambda: callback(box.currentData()) if not self.loading else None)
        return box

    def font_hover(self, family):
        if self.loading or not self._ui_ready:
            return
        self.preview.font_override = family
        self.font_preview_note.setText(tr('Vista previa: {0} · todavía sin aplicar').format(family))
        self.preview.update()
        cue = self.selected_cue()
        effective = self.preview.effective_project()
        if cue:
            overflow = self.preview.renderer.overflow(effective, cue)
            self.overflow_label.setText(tr('⚠ Con esta fuente la frase excede los márgenes.') if overflow else '')

    def font_preview_end(self):
        self.preview.font_override = ''
        if not self._ui_ready:
            return
        self.font_preview_note.setText(tr('Pasa el mouse por una fuente para probarla. Clic para aplicar; Esc para cancelar.'))
        self.preview.update()
        if not self.loading:
            self.update_labels()
        QTimer.singleShot(0, self.restore_font_control)

    def restore_font_control(self):
        if not self.font_combo.preview_open():
            self.font_combo.setCurrentFont(QFont(self.project.style.font))

    def font_commit(self, family):
        if not self.loading:
            self.font_preview_end()
            self.set_style('font', family)

    def make_keyframe_panel(self):
        scroll, layout = self.scroll_panel()
        self.keyframe_heading = QLabel(tr('Avance de la frase'))
        self.keyframe_heading.setStyleSheet('font-size:16px; color:#b8defc;')
        layout.addWidget(self.keyframe_heading)
        self.keyframe_enabled = QCheckBox(tr('Usar keyframes en esta frase'))
        self.keyframe_enabled.toggled.connect(self.keyframe_toggle)
        layout.addWidget(self.keyframe_enabled)
        self.keyframe_scope = self.combo([(tr('Repintado y énfasis'), 'all'), (tr('Solo repintado'), 'paint'),
                                          (tr('Solo énfasis'), 'emphasis')], self.keyframe_scope_changed)
        layout.addWidget(self.keyframe_scope)
        layout.addWidget(self.help_label(tr('Eje horizontal: segundos desde el inicio. Eje vertical: avance. Dos puntos con el mismo % sostienen la animación; un tramo más inclinado la acelera. Entrada y salida conservan sus tiempos.')))
        self.keyframe_curve = KeyframeCurve()
        self.keyframe_curve.add_requested.connect(self.keyframe_add)
        self.keyframe_curve.moved.connect(self.keyframe_move)
        self.keyframe_curve.seek_requested.connect(self.keyframe_seek)
        self.keyframe_curve.editing_started.connect(self.pause)
        layout.addWidget(self.keyframe_curve)
        row = QHBoxLayout()
        self.lock_time = QCheckBox(tr('Bloquear tiempo (X)'))
        self.lock_time.setToolTip(tr('Arrastrar un punto solo cambia su avance (%).'))
        self.lock_progress = QCheckBox(tr('Bloquear avance (Y)'))
        self.lock_progress.setToolTip(tr('Arrastrar un punto solo cambia su tiempo.'))
        for check, key, attr in ((self.lock_time, 'lock_keyframe_time', 'lock_time'),
                                 (self.lock_progress, 'lock_keyframe_progress', 'lock_progress')):
            check.setChecked(self.settings.value(key, False, type=bool))
            setattr(self.keyframe_curve, attr, check.isChecked())
            check.toggled.connect(lambda value, k=key, a=attr: (self.settings.setValue(k, value),
                                                                setattr(self.keyframe_curve, a, value)))
            row.addWidget(check)
        row.addStretch()
        layout.addLayout(row)
        self.keyframe_now = QLabel('')
        layout.addWidget(self.keyframe_now)
        row = QHBoxLayout()
        button = QPushButton(tr('+ En el cabezal'))
        button.clicked.connect(lambda: self.keyframe_at_head(False))
        row.addWidget(button)
        button = QPushButton(tr('Sostener hasta aquí'))
        button.clicked.connect(lambda: self.keyframe_at_head(True))
        row.addWidget(button)
        layout.addLayout(row)
        self.keyframe_table = QTableWidget(0, 2)
        self.keyframe_table.setHorizontalHeaderLabels([tr('+Tiempo (s)'), tr('Avance (%)')])
        self.keyframe_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.keyframe_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.keyframe_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.keyframe_table.setMinimumHeight(185)
        self.keyframe_table.itemChanged.connect(self.keyframe_cell_changed)
        self.keyframe_table.cellDoubleClicked.connect(lambda row, col: self.keyframe_seek_row(row) if col == 0 else None)
        layout.addWidget(self.keyframe_table)
        row = QHBoxLayout()
        button = QPushButton(tr('Eliminar puntos'))
        button.clicked.connect(self.keyframe_delete)
        row.addWidget(button)
        button = QPushButton(tr('Restablecer lineal'))
        button.clicked.connect(self.keyframe_reset)
        row.addWidget(button)
        layout.addLayout(row)
        layout.addWidget(self.help_label(tr('Los extremos 0% y 100% son automáticos: siguen «Repintar desde / Hasta» en Frase. Edita los puntos interiores en la tabla o arrástralos. Doble clic en el gráfico agrega un punto.')))
        layout.addWidget(self.help_label(tr('Ejemplo: +1.0 s → 40%; +2.5 s → 40%; final +3.0 s → 100%. Sostiene entre 1.0 y 2.5 s y completa el resto en 0.5 s. La curva se comparte entre original y traducción.')))
        layout.addStretch()
        return scroll

    def update_keyframe_position(self):
        cue = self.selected_cue()
        if not cue:
            self.keyframe_now.setText(tr('Selecciona una frase.'))
            return
        elapsed = self.position-cue.start
        self.keyframe_curve.elapsed = elapsed
        self.keyframe_now.setText(tr('Cabezal {0:+.3f} s · avance {1:.1f}%').format(elapsed, animation_progress(cue, elapsed)*100))
        self.keyframe_curve.update()

    def refresh_keyframes(self):
        was_loading = self.loading
        self.loading = True
        try:
            cue = self.selected_cue()
            self.keyframe_heading.setText(tr('Avance · frase {0}').format(self.selected_index()+1) if cue else tr('Selecciona una frase'))
            self.keyframe_enabled.setEnabled(cue is not None)
            self.keyframe_enabled.setChecked(cue.use_keyframes if cue else False)
            self.keyframe_scope.setEnabled(cue is not None)
            self.keyframe_scope.setCurrentIndex(self.keyframe_scope.findData(cue.keyframe_scope) if cue else 0)
            self.keyframe_curve.cue = cue
            self.keyframe_curve.drag_index = None
            self.keyframe_curve.drag_value = None
            points = keyframe_points(cue) if cue else []
            self.keyframe_table.setRowCount(len(points))
            for row, (time, progress) in enumerate(points):
                endpoint = row in (0, len(points)-1)
                self.keyframe_table.setVerticalHeaderItem(row, QTableWidgetItem(tr('Inicio') if row == 0 else tr('Final') if row == len(points)-1 else str(row)))
                for col, value in enumerate((f'{time:.3f}', f'{progress*100:.2f}')):
                    item = QTableWidgetItem(value)
                    if endpoint:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        item.setForeground(QColor('#8297b4'))
                        item.setToolTip(tr('Extremo automático del intervalo de repintado.'))
                    self.keyframe_table.setItem(row, col, item)
            self.keyframe_curve.update()
            self.update_keyframe_position()
        finally:
            self.loading = was_loading

    def keyframe_commit(self, points):
        cue = self.selected_cue()
        if not cue:
            return False
        points = sorted(points, key=lambda point: point.time)
        trial = copy.copy(cue)
        trial.keyframes = points
        issues = [text for code, text in Project(duration=max(self.project.duration, cue.end), cues=[trial]).problem_items()
                  if code == 'keyframes']
        if issues:
            self.statusBar().showMessage(tr('Los tiempos deben ser únicos e interiores al intervalo. El avance debe ir de 0 a 100%, sin retroceder.'), 10000)
            return False
        self.record()
        cue.keyframes = points
        self.changed(panels=True)
        return True

    def keyframe_add(self, time, progress):
        cue = self.selected_cue()
        if not cue:
            return False
        self.pause()
        point = Keyframe(round(time, 6), round(progress, 6))
        points = copy.deepcopy(cue.keyframes)
        existing = next((i for i, p in enumerate(points) if abs(p.time-point.time) < .001), None)
        if existing is None:
            points.append(point)
        else:
            point.time = points[existing].time
            points[existing] = point
        return self.keyframe_commit(points)

    def keyframe_at_head(self, hold=False):
        cue = self.selected_cue()
        if not cue:
            return
        elapsed = self.position-cue.start
        points = keyframe_points(cue)
        if not points[0][0] < elapsed < points[-1][0]:
            self.statusBar().showMessage(tr('Sitúa el cabezal dentro del intervalo de repintado de esta frase.'), 8000)
            return
        if hold:
            previous = [p for p in points if p[0] < elapsed-.000001]
            progress = previous[-1][1] if previous else 0.0
        else:
            progress = animation_progress(cue, elapsed)
        self.keyframe_add(elapsed, progress)

    def keyframe_move(self, index, time, progress):
        cue = self.selected_cue()
        if not cue or not 0 <= index < len(cue.keyframes):
            return
        self.pause()
        points = copy.deepcopy(cue.keyframes)
        points[index] = Keyframe(round(time, 6), round(progress, 6))
        if self.keyframe_commit(points):
            self.keyframe_seek(time)

    def keyframe_cell_changed(self, item):
        cue = self.selected_cue()
        if self.loading or not cue:
            return
        index = item.row()-1
        if not 0 <= index < len(cue.keyframes):
            return
        try:
            time = parse_time(self.keyframe_table.item(item.row(), 0).text())
            progress = float(self.keyframe_table.item(item.row(), 1).text().replace(',', '.'))/100
            self.keyframe_move(index, time, progress)
        except ValueError:
            self.statusBar().showMessage(tr('Tiempo inválido o porcentaje fuera de 0 a 100.'), 8000)
        self.refresh_keyframes()

    def keyframe_delete(self):
        cue = self.selected_cue()
        if not cue:
            return
        indexes = {idx.row()-1 for idx in self.keyframe_table.selectionModel().selectedRows()}
        points = [copy.deepcopy(p) for i, p in enumerate(cue.keyframes) if i not in indexes]
        if len(points) != len(cue.keyframes):
            self.keyframe_commit(points)

    def keyframe_reset(self):
        cue = self.selected_cue()
        if cue and cue.keyframes:
            self.keyframe_commit([])

    def keyframe_toggle(self, enabled):
        cue = self.selected_cue()
        if self.loading or not cue or cue.use_keyframes == enabled:
            return
        self.record()
        cue.use_keyframes = enabled
        self.changed(panels=True)

    def keyframe_scope_changed(self, scope):
        cue = self.selected_cue()
        if self.loading or not cue or cue.keyframe_scope == scope:
            return
        self.record()
        cue.keyframe_scope = scope
        self.changed(panels=True)

    def keyframe_seek(self, relative):
        cue = self.selected_cue()
        if cue:
            self.seek(cue.start+relative)

    def keyframe_seek_row(self, row):
        cue = self.selected_cue()
        if cue and 0 <= row < len(keyframe_points(cue)):
            self.keyframe_seek(keyframe_points(cue)[row][0])

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

    def record(self, group=None):
        """Snapshot for undo. Consecutive changes of the same control within a second
        (held +/- buttons, repeated clicks) share one undo step."""
        if self.loading:
            return
        now = time.monotonic()
        if (group is not None and group == self._history_group and self.history
                and now - self._history_time < 1.0):
            self._history_time = now
            self.future.clear()
            self.dirty = True
            return
        self._history_group, self._history_time = group, now
        self.history.append(copy.deepcopy(to_dict(self.project)))
        self.history = self.history[-80:]
        self.future.clear()
        self.dirty = True

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

    def refresh_table(self):
        old_loading = self.loading
        self.loading = True
        old_row = self.table.currentRow()
        try:
            self.table.setRowCount(len(self.project.cues))
            for i, cue in enumerate(self.project.cues):
                values = [str(i+1), time_text(cue.start), time_text(cue.end), cue.original, cue.translation]
                for col, text in enumerate(values):
                    item = QTableWidgetItem(text)
                    if col == 0:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(i, col, item)
            if self.project.cues:
                self.table.selectRow(max(0, min(old_row, len(self.project.cues)-1)))
            self.waveform.selected = self.table.currentRow()
        finally:
            self.loading = old_loading

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

    def text_editors(self):
        return (('original', self.original_edit), ('translation', self.translation_edit))

    def pending_text(self):
        """Tracks the user typed in the Frase tab and has not applied yet."""
        if self._text_uid is None:
            return {}
        return {track: self.editor_text(editor) for track, editor in self.text_editors()
                if self.editor_text(editor) != self._text_loaded[track]}

    def all_text_drafts(self):
        """Current box plus drafts of other rows; keep applied text and marks separate."""
        drafts = copy.deepcopy(self._text_drafts)
        pending = self.pending_text()
        if pending:
            drafts[self._text_uid] = pending
        cues = {cue.uid: cue for cue in self.project.cues}
        return {uid: tracks for uid, values in drafts.items() if uid in cues
                if (tracks := {track: text for track, text in values.items()
                               if text != getattr(cues[uid], track)})}

    def update_draft_indicator(self):
        count = len(self.all_text_drafts())
        self.draft_label.setText(tr('{0} frase(s) con texto sin aplicar').format(count) if count else '')

    def text_edited(self):
        if self.loading or self._text_uid is None:
            return
        self.dirty = True
        self.update_draft_indicator()

    def project_with_drafts(self):
        """Persistence snapshot; unapplied text does not enter the renderer or undo stack."""
        project = copy.deepcopy(self.project)
        project.text_drafts = self.all_text_drafts()
        return project

    @staticmethod
    def editor_text(editor):
        """Document text without Qt's plain-text normalization, so U+00A0 survives."""
        return editor.document().toRawText().replace('\u2029', '\n').replace('\u2028', '\n')

    @staticmethod
    def fill_text_editor(editor, text):
        with QSignalBlocker(editor):
            editor.setPlainText(text)

    def load_text_editors(self, cue):
        """Refresh the text boxes without discarding what the user is typing."""
        uid = cue.uid if cue else None
        pending = self.pending_text()
        if pending and uid == self._text_uid:
            # Same phrase: keep the typed boxes, refresh only the untouched ones.
            for track, editor in self.text_editors():
                if track not in pending:
                    self.fill_text_editor(editor, getattr(cue, track))
                    self._text_loaded[track] = self.editor_text(editor)
            return
        if pending:
            self._text_drafts.setdefault(self._text_uid, {}).update(pending)
            self.statusBar().showMessage(tr('La frase anterior conserva su texto sin aplicar. '
                                         'Vuelve a seleccionarla y pulsa «Aplicar cambios de texto».'), 8000)
        self._text_uid = uid
        draft = self._text_drafts.pop(uid, {}) if uid else {}
        for track, editor in self.text_editors():
            self.fill_text_editor(editor, getattr(cue, track) if cue else '')
            self._text_loaded[track] = self.editor_text(editor)
            if track in draft:
                self.fill_text_editor(editor, draft[track])

    def reset_text_editors(self, restore=False):
        """Load saved drafts on opening, or discard them when replacing the lyrics."""
        self._text_uid = None
        self._text_drafts = copy.deepcopy(self.project.text_drafts) if restore else {}
        self.project.text_drafts = {}  # Runtime drafts live in the editors, not in undo snapshots.

    def fill_positions(self):
        self.position_combo.clear()
        if self.project.style.layout == 'one':
            items = [(tr('Superior izquierda'), 'left_top'), (tr('Inferior izquierda'), 'left_bottom'),
                     (tr('Superior derecha'), 'right_top'), (tr('Inferior derecha'), 'right_bottom'), (tr('Centro'), 'center')]
        else:
            items = [(tr('Izquierda · arriba / abajo'), 'left_split'), (tr('Derecha · arriba / abajo'), 'right_split'),
                     (tr('Centro · principal arriba'), 'center')]
        for caption, data in items:
            self.position_combo.addItem(caption, data)
        idx = self.position_combo.findData(self.project.style.position)
        self.position_combo.setCurrentIndex(max(0, idx))

    def cue_selected(self):
        if self.loading or self._following_selection:
            return
        self.mark_index = max(0, self.selected_index())
        self.last_marked = -1
        self.waveform.selected = self.selected_index()
        self.refresh_panels()
        self.update_labels()
        self.waveform.update()
        cue = self.selected_cue()
        if self.link_selection.isChecked() and cue:
            self.seek(cue.start)

    def cue_clicked(self, row, column):
        cue = self.selected_cue()
        if (self.link_selection.isChecked() and cue and row == self.selected_index()
                and not self.loading and not self._following_selection and abs(self.position-cue.start) > .001):
            self.cue_selected()

    def link_toggled(self, enabled):
        self.settings.setValue('link_selection', enabled)
        if enabled:
            self.follow_time_selection(self.position)

    def follow_time_selection(self, value):
        if not self.link_selection.isChecked() or self.loading or self._following_selection:
            return
        selected = self.selected_cue()
        if 0 <= self.last_marked and self.mark_index < len(self.project.cues):
            # Ctrl+M sequence: keep showing the phrase the next mark will start.
            index = self.mark_index
        else:
            if selected and selected.start <= value < selected.end:
                return
            candidates = [(cue.start, i) for i, cue in enumerate(self.project.cues) if cue.start <= value < cue.end]
            if not candidates:
                return
            index = max(candidates)[1]
        if index == self.selected_index():
            return
        if selected and self.pending_text():
            self.statusBar().showMessage(tr('Aplica los cambios de texto para reanudar el seguimiento automático de frases.'), 6000)
            return
        self._following_selection = True
        try:
            self.table.selectRow(index)
            self.table.scrollToItem(self.table.item(index, 0))
            self.waveform.selected = index
            self.refresh_panels()
            self.update_labels()
        finally:
            self._following_selection = False

    def set_style(self, key, value):
        if self.loading or value is None or getattr(self.project.style, key) == value:
            return
        self.record(('style', key))
        setattr(self.project.style, key, value)
        if key == 'layout':
            pos = self.project.style.position
            if value == 'one':
                self.project.style.position = {'left_split': 'left_top', 'right_split': 'right_top'}.get(pos, 'center')
            else:
                self.project.style.position = 'left_split' if pos.startswith('left') else 'right_split' if pos.startswith('right') else 'center'
        self.changed(panels=True)
        if key == 'background' and value == 'video':
            self.request_still_frame()

    def change_resolution(self):
        data = self.resolution.currentData()
        if self.loading or not data:
            return
        width, height = (int(v) for v in data.split('x'))
        if (width, height) == (self.project.style.width, self.project.style.height):
            return
        self.record()
        self.project.style.width, self.project.style.height = width, height
        self.changed(panels=True)

    def change_fps(self):
        data = self.fps.currentData()
        if not self.loading and data:
            self.set_style('fps', float(data))

    def change_duration(self, value):
        if self.loading or value == self.project.duration:
            return
        self.record('duration')
        self.project.duration = value
        self.changed()

    def cue_time(self, key, value):
        cue = self.selected_cue()
        if self.loading or cue is None:
            return
        if key == 'start' and value >= cue.end or key == 'end' and value <= cue.start:
            self.statusBar().showMessage(tr('El final debe ser mayor que el inicio.'), 5000)
            self.refresh_panels()
            return
        if key == 'paint_start' and value >= (cue.duration if cue.paint_end is None else cue.paint_end):
            self.refresh_panels()
            return
        if key == 'paint_end' and not cue.paint_start < value <= cue.duration:
            self.refresh_panels()
            return
        self.record(('cue', cue.uid, key))
        previous_duration = cue.duration
        old_paint_start = cue.paint_start
        old_paint_end = cue.duration if cue.paint_end is None else cue.paint_end
        setattr(cue, key, value)
        if key in ('start', 'end'):
            retime_cue(cue, previous_duration)
        else:
            clamp_cue(cue)
            retime_keyframes(cue, old_paint_start, old_paint_end)
        self.changed(tables=True, panels=True)

    def reset_paint_interval(self):
        cue = self.selected_cue()
        if cue:
            self.record()
            old_start = cue.paint_start
            old_end = cue.duration if cue.paint_end is None else cue.paint_end
            cue.paint_start, cue.paint_end = 0, None
            retime_keyframes(cue, old_start, old_end)
            self.changed(panels=True)

    def cue_cell_changed(self, item):
        if self.loading:
            return
        i, col = item.row(), item.column()
        if not 0 <= i < len(self.project.cues) or col == 0:
            return
        cue = self.project.cues[i]
        try:
            if col in (1, 2):
                value = parse_time(item.text())
                if col == 1 and value >= cue.end or col == 2 and value <= cue.start:
                    raise ValueError(tr('El final debe ser mayor que el inicio.'))
                self.record()
                previous_duration = cue.duration
                setattr(cue, 'start' if col == 1 else 'end', value)
                retime_cue(cue, previous_duration)
            else:
                track = 'original' if col == 3 else 'translation'
                if item.text() == getattr(cue, track):
                    return
                if not self.confirm_clear_spans(cue, track):
                    self.refresh_table()
                    return
                self.record()
                setattr(cue, track, item.text().replace('\n', ' '))
                cue.spans(track).clear()
            self.changed(tables=True, panels=True)
        except ValueError as exc:
            self.statusBar().showMessage(str(exc), 6000)
            self.refresh_table()

    def confirm_clear_spans(self, cue, track):
        if not cue.spans(track):
            return True
        return QMessageBox.question(self, tr('Cambiar texto'), tr('Este texto tiene marcas de sílabas. Cambiarlo eliminará sus marcas. ¿Continuar?'),
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def apply_text(self):
        cue = self.selected_cue()
        if not cue:
            return
        changes = {}
        # Only boxes the user edited count: Qt's plain text may differ from the stored text
        # (for example, non-breaking spaces), and that alone must not look like a change.
        pending = self.pending_text() if self._text_uid == cue.uid else {}
        for track, text in pending.items():
            value = text.replace('\n', ' ')
            if value != getattr(cue, track):
                if not self.confirm_clear_spans(cue, track):
                    return
                changes[track] = value
        self._text_uid = None  # Reload both boxes from the phrase after applying.
        if changes:
            self.record()
            for track, value in changes.items():
                setattr(cue, track, value)
                cue.spans(track).clear()
            self.changed(tables=True, panels=True)
        else:
            self.load_text_editors(cue)
        self.update_draft_indicator()

    def add_cue(self):
        self.record()
        start = min(self.position, max(0, self.project.duration - .1))
        # Insert in time order: Ctrl+M and linked navigation walk the list from top to bottom.
        row = next((i for i, c in enumerate(self.project.cues) if c.start > start), len(self.project.cues))
        self.project.cues.insert(row, Cue(start=start, end=min(self.project.duration, start+3), original=tr('Nueva frase')))
        self.changed(tables=True)
        self.table.selectRow(row)
        self.refresh_panels()

    def duplicate_cue(self):
        cue = self.selected_cue()
        if not cue:
            return
        self.record()
        from uuid import uuid4
        duplicate = copy.deepcopy(cue)
        duplicate.uid = uuid4().hex
        duration = cue.duration
        duplicate.start = cue.end
        duplicate.end = duplicate.start + duration
        self.project.duration = max(self.project.duration, duplicate.end)
        row = self.selected_index()+1
        self.project.cues.insert(row, duplicate)
        self.changed(tables=True)
        self.table.selectRow(row)
        self.refresh_panels()

    def delete_cue(self):
        i = self.selected_index()
        if 0 <= i < len(self.project.cues):
            self.record()
            del self.project.cues[i]
            self.changed(tables=True, panels=True)

    def offset_cues(self):
        from PySide6.QtWidgets import QInputDialog
        offset, ok = QInputDialog.getDouble(self, tr('Desplazar tiempos'), tr('Segundos para todas las frases (negativo adelanta):'), 0, -36000, 36000, 3)
        if not ok or offset == 0:
            return
        if any(c.start + offset < 0 for c in self.project.cues):
            QMessageBox.warning(self, tr('Desplazamiento inválido'), tr('Alguna frase quedaría antes de cero. Usa un desplazamiento menor.'))
            return
        self.record()
        for cue in self.project.cues:
            cue.start += offset
            cue.end += offset
        self.project.duration = max(self.project.duration, max((c.end for c in self.project.cues), default=0))
        self.changed(tables=True, panels=True)

    def move_edge(self, edge, value):
        cue = self.selected_cue()
        if not cue:
            return
        if edge == 'start' and value >= cue.end or edge == 'end' and value <= cue.start:
            return
        self.record()
        previous_duration = cue.duration
        setattr(cue, edge, round(value, 3))
        retime_cue(cue, previous_duration)
        self.changed(tables=True, panels=True)

    def refresh_spans(self):
        was_loading = self.loading
        self.loading = True
        try:
            cue = self.selected_cue()
            track = self.track.currentData() or 'original'
            text = getattr(cue, track) if cue else ''
            self.span_text.setPlainText(text)
            self.split_edit.setText(text)
            spans = cue.spans(track) if cue else []
            self.span_table.setRowCount(len(spans))
            for row, span in enumerate(spans):
                item = QTableWidgetItem('')
                item.setFlags((item.flags() | Qt.ItemFlag.ItemIsUserCheckable) & ~Qt.ItemFlag.ItemIsEditable)
                item.setCheckState(Qt.CheckState.Checked if span.enabled else Qt.CheckState.Unchecked)
                self.span_table.setItem(row, 0, item)
                values = [text[span.begin:span.end], f'{span.start:.3f}', f'{span.finish:.3f}', span.color,
                          '' if span.lift is None else str(span.lift), '' if span.scale is None else str(span.scale)]
                for col, value in enumerate(values, 1):
                    item = QTableWidgetItem(value)
                    if col == 1:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if col == 4 and value:
                        item.setForeground(QColor(value))
                    self.span_table.setItem(row, col, item)
        finally:
            self.loading = was_loading

    def selected_text_range(self):
        cue = self.selected_cue()
        cursor = self.span_text.textCursor()
        if not cue or not cursor.hasSelection():
            raise ValueError(tr('Selecciona primero la sílaba o parte del texto en el recuadro superior.'))
        text = getattr(cue, self.track.currentData())
        # QTextCursor offsets are UTF-16 units, Python offsets are Unicode code points.
        raw = text.encode('utf-16-le')
        begin = len(raw[:cursor.selectionStart()*2].decode('utf-16-le'))
        end = len(raw[:cursor.selectionEnd()*2].decode('utf-16-le'))
        if (begin < len(text) and unicodedata.combining(text[begin])) or (end < len(text) and unicodedata.combining(text[end])):
            raise ValueError(tr('Incluye el carácter completo junto con su acento.'))
        return begin, end, text[begin:end]

    def mark_selection(self):
        cue = self.selected_cue()
        if not cue:
            return
        try:
            begin, end, _ = self.selected_text_range()
            track = self.track.currentData()
            if any(begin < s.end and end > s.begin for s in cue.spans(track)):
                raise ValueError(tr('La selección se cruza con una marca existente; elimínala primero.'))
            self.record()
            add_span(cue, track, begin, end)
            self.changed(panels=True)
        except ValueError as exc:
            self.statusBar().showMessage(str(exc), 8000)

    def repeat_selection(self):
        try:
            _, _, fragment = self.selected_text_range()
        except ValueError as exc:
            self.statusBar().showMessage(str(exc), 8000)
            return
        if not fragment.strip():
            return
        track = self.track.currentData()
        matches = []
        for cue in self.project.cues:
            text = getattr(cue, track)
            offset = 0
            while True:
                begin = text.find(fragment, offset)
                if begin < 0:
                    break
                end = begin + len(fragment)
                if not any(begin < s.end and end > s.begin for s in cue.spans(track)):
                    matches.append((cue, begin, end))
                offset = end
        if matches:
            self.record()
            for cue, begin, end in matches:
                add_span(cue, track, begin, end)
            self.changed(panels=True)
        self.statusBar().showMessage(tr('{0} marca(s) creada(s). Revisa sus tiempos estimados.').format(len(matches)), 8000)

    def apply_split(self):
        cue = self.selected_cue()
        if not cue:
            return
        marked = self.split_edit.text()
        track = self.track.currentData()
        if marked.replace('|', '') != getattr(cue, track):
            self.statusBar().showMessage(tr('Conserva exactamente el texto y los espacios; agrega únicamente |.'), 8000)
            return
        self.record()
        split_spans(cue, track, marked)
        self.changed(panels=True)
        self.statusBar().showMessage(tr('Marcas creadas con tiempos estimados; corrígelos escuchando.'), 6000)

    def span_cell_changed(self, item):
        if self.loading:
            return
        cue = self.selected_cue()
        if not cue:
            return
        row, col = item.row(), item.column()
        spans = cue.spans(self.track.currentData())
        if row >= len(spans) or col == 1:
            return
        span = spans[row]
        try:
            value = item.text().strip()
            if col in (2, 3):
                parsed = parse_time(value)
                if col == 2 and not 0 <= parsed < span.finish or col == 3 and not span.start < parsed <= cue.duration:
                    raise ValueError(tr('El intervalo debe quedar dentro de la frase y tener duración positiva.'))
            elif col == 4:
                if value and not QColor(value).isValid():
                    raise ValueError(tr('Color inválido. Usa #RRGGBB o deja vacío para heredar.'))
                parsed = QColor(value).name() if value else ''
            elif col in (5, 6):
                parsed = float(value) if value else None
                if parsed is not None and (not math.isfinite(parsed) or (col == 5 and not -100 <= parsed <= 160) or (col == 6 and not .5 <= parsed <= 3)):
                    raise ValueError(tr('Subida: -100 a 160 px. Escala: 0.5 a 3.'))
            else:
                parsed = item.checkState() == Qt.CheckState.Checked
            self.record()
            setattr(span, {0:'enabled', 2:'start', 3:'finish', 4:'color', 5:'lift', 6:'scale'}[col], parsed)
            self.changed()
        except ValueError as exc:
            self.statusBar().showMessage(str(exc), 8000)
        self.refresh_spans()

    def span_double_click(self, row, col):
        cue = self.selected_cue()
        if not cue:
            return
        span = cue.spans(self.track.currentData())[row]
        if col == 1:
            elapsed = animation_to_elapsed(cue, span.start) if cue.keyframe_scope in ('all', 'emphasis') else span.start
            self.seek(cue.start + elapsed)
            self.play()
        elif col == 4:
            self.bulk_color()
        elif col in (2, 3, 5, 6):
            self.span_table.editItem(self.span_table.item(row, col))

    def span_rows(self):
        return sorted({idx.row() for idx in self.span_table.selectionModel().selectedRows()})

    def auto_spans(self):
        cue = self.selected_cue()
        if cue:
            self.record()
            propose_spans(cue, self.track.currentData())
            self.changed(panels=True)
            self.statusBar().showMessage(tr('Reparto estimado aplicado. No se ha analizado la voz.'), 7000)

    def snap_audio(self):
        cue = self.selected_cue()
        if cue is None:
            return
        if not self.waveform.peaks:
            QMessageBox.information(self, tr('Audio pendiente'), tr('Carga un medio y espera a que aparezca su forma de onda. Esta función necesita FFmpeg.'))
            return
        self.record()
        count = snap_spans_to_audio(cue, self.track.currentData(), self.waveform.peaks, self.waveform.audio_duration)
        self.changed(panels=True)
        QMessageBox.information(self, tr('Ajuste orientativo'), tr('{0} marca(s) ajustada(s) a ataques cercanos del audio.\nLos instrumentos también generan ataques: revisa escuchando.').format(count))

    def expand_span_editor(self):
        panel = self.tabs.widget(1)
        self.tabs.removeTab(1)
        dialog = QDialog(self)
        dialog.setWindowTitle(tr('Sílabas · editor ampliado'))
        dialog.resize(1150, 760)
        layout = QVBoxLayout(dialog)
        split = QSplitter(Qt.Orientation.Horizontal)
        visual = QWidget()
        vl = QVBoxLayout(visual)
        preview = Preview()
        preview.setMinimumSize(420, 250)
        vl.addWidget(preview, 1)
        label = QLabel()
        vl.addWidget(label)
        play_toggle = QPushButton()
        play_toggle.setIconSize(QSize(18, 18))
        play_toggle.clicked.connect(self.toggle_play)
        vl.addWidget(play_toggle)
        for caption, fn in [(tr('Repetir frase'), self.play_cue),
                            (tr('Retroceder 0.1 s'), lambda: self.seek(self.position-.1)),
                            (tr('Avanzar 0.1 s'), lambda: self.seek(self.position+.1))]:
            button = QPushButton(caption)
            button.clicked.connect(fn)
            vl.addWidget(button)
        loop = QCheckBox(tr('Bucle de la frase seleccionada'))
        loop.setChecked(self.loop.isChecked())
        loop.toggled.connect(self.loop.setChecked)
        vl.addWidget(loop)
        split.addWidget(visual)
        split.addWidget(panel)
        split.setSizes([500, 650])
        layout.addWidget(split)
        close = QPushButton(tr('Volver al editor principal'))
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        timer = QTimer(dialog)
        def refresh():
            preview.project = self.project
            preview.font_override = self.preview.font_override
            preview.time = self.position
            preview.video = self.preview.video
            preview.update()
            label.setText(time_text(self.position))
            self.update_play_button(play_toggle)
        timer.timeout.connect(refresh)
        timer.start(33)
        refresh()
        try:
            dialog.exec()
        finally:
            timer.stop()
            self.tabs.insertTab(1, panel, tr('Sílabas'))
            self.tabs.setCurrentIndex(1)

    def remove_spans(self):
        cue, rows = self.selected_cue(), self.span_rows()
        if cue and rows:
            self.record()
            spans = cue.spans(self.track.currentData())
            for row in reversed(rows):
                del spans[row]
            self.changed(panels=True)

    def bulk_color(self):
        cue, rows = self.selected_cue(), self.span_rows()
        if not cue or not rows:
            self.statusBar().showMessage(tr('Selecciona una o varias filas de sílabas (Ctrl / Shift).'), 5000)
            return
        color = QColorDialog.getColor(QColor(self.project.style.effect_color), self, tr('Color de énfasis para la selección'))
        if color.isValid():
            self.record()
            for row in rows:
                cue.spans(self.track.currentData())[row].color = color.name()
            self.changed(panels=True)

    def inherit_spans(self):
        cue, rows = self.selected_cue(), self.span_rows()
        if cue and rows:
            self.record()
            for row in rows:
                span = cue.spans(self.track.currentData())[row]
                span.color, span.lift, span.scale = '', None, None
            self.changed(panels=True)

    def undo(self):
        if self.history:
            self._history_group = None
            self.future.append(copy.deepcopy(to_dict(self.project)))
            self.project = from_dict(self.history.pop(), strict=False)
            self.dirty = True
            self.refresh_all()
            self.set_media_source()

    def redo(self):
        if self.future:
            self._history_group = None
            self.history.append(copy.deepcopy(to_dict(self.project)))
            self.project = from_dict(self.future.pop(), strict=False)
            self.dirty = True
            self.refresh_all()
            self.set_media_source()

    def set_zoom(self, value):
        self.waveform.zoom = value
        self.waveform.update()

    def set_guides(self, value):
        self.preview.guides = value
        self.preview.update()

    def tick(self):
        focus = QApplication.focusWidget()
        editing = (isinstance(focus, (QLineEdit, QPlainTextEdit, QAbstractSpinBox))
                   or (isinstance(focus, QComboBox) and focus.isEditable()))
        self.space_shortcut.setEnabled(not editing)
        if self.virtual_playing:
            self.set_position(self.virtual_start + self.virtual_clock.elapsed() / 1000 * self.speed.currentData())
        elif self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState and not self._warming_video:
            self.set_position(self.player.position() / 1000)
        self.update_play_button()

    def update_play_button(self, button=None):
        """Swap icon and caption only when the playback state changes."""
        playing = self.is_playing()
        if button is None:
            if playing == self._shown_playing:
                return
            self._shown_playing = playing
            button = self.play_button
        button.setIcon(self.play_icons[playing])
        button.setText(tr('Pausar') if playing else tr('Reproducir'))
        button.setToolTip((tr('Pausar') if playing else tr('Reproducir')) + tr('  [Espacio]'))

    def player_position(self, value):
        if self._warming_video or self._pending_player_seek is not None:
            return
        if (self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState
                and abs(value/1000-self._desired_position) > .1):
            return
        if not self.virtual_playing:
            self.set_position(value / 1000, allow_loop=not self._seeking)

    def set_position(self, value, allow_loop=True):
        cue = self.selected_cue()
        if allow_loop and self.loop.isChecked() and cue and self.is_playing() and value >= cue.end:
            self.seek(cue.start)
            return
        if value >= self.project.duration:
            self.pause()
            value = self.project.duration
        self.position = max(0, value)
        self.follow_time_selection(self.position)
        self.preview.time = self.position
        self.waveform.position = self.position
        if not self.seek_slider.isSliderDown():
            was_blocked = self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(int(self.position * 1000))
            self.seek_slider.blockSignals(was_blocked)
        self.time_label.setText(f'{time_text(self.position)} / {time_text(self.project.duration)}')
        self.update_keyframe_position()
        self.preview.update()
        self.waveform.update()

    def seek(self, value):
        value = max(0, min(self.project.duration, value))
        if self._warming_video:
            self.finish_video_prime()
        self._desired_position = value
        if self.project.media and self.player.mediaStatus() in (QMediaPlayer.MediaStatus.NoMedia, QMediaPlayer.MediaStatus.LoadingMedia):
            self._pending_player_seek = value
        self._seeking = True
        try:
            self.player.setPosition(round(value * 1000))
        finally:
            self._seeking = False
        if self.virtual_playing:
            self.virtual_start = value
            self.virtual_clock.restart()
        self.set_position(value, allow_loop=False)
        self.request_still_frame()

    def is_playing(self):
        return self.virtual_playing or (self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState and not self._warming_video)

    def play(self):
        if self._warming_video:
            self.finish_video_prime()
        self.cancel_still_frames()
        if self.position >= self.project.duration:
            self.seek(0)
        if self.project.media and Path(self.project.media).is_file():
            self.player.play()
        else:
            self.virtual_start = self.position
            self.virtual_clock.start()
            self.virtual_playing = True

    def pause(self):
        if self._warming_video:
            self.finish_video_prime()
        self._desired_position = self.position
        self.virtual_playing = False
        self.player.pause()

    def toggle_play(self):
        if self.is_playing():
            self.pause()
        else:
            self.play()

    def change_speed(self):
        if self.virtual_playing:
            self.virtual_start = self.position
            self.virtual_clock.restart()
        self.player.setPlaybackRate(self.speed.currentData())

    def play_cue(self):
        cue = self.selected_cue()
        if cue:
            self.seek(cue.start if self.link_selection.isChecked() else max(0, cue.start - .3))
            self.play()

    def current_time(self):
        """Playback time at this instant; self.position is only refreshed every tick."""
        if self.virtual_playing:
            value = self.virtual_start + self.virtual_clock.elapsed() / 1000 * self.speed.currentData()
        elif self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState and not self._warming_video:
            value = self.player.position() / 1000
        else:
            return self.position
        return max(0.0, min(self.project.duration, value))

    def mark_next(self):
        if not self.project.cues:
            return
        if self.mark_index >= len(self.project.cues):
            self.statusBar().showMessage(tr('Todas las frases están iniciadas. Marca el final o selecciona una fila para volver a marcar.'), 6000)
            return
        index = min(self.mark_index, len(self.project.cues)-1)
        t = self.current_time()
        if t >= self.project.duration - .05:
            self.statusBar().showMessage(tr('Retrocede: la frase necesita al menos 0.05 s.'), 5000)
            return
        if self.last_marked >= 0 and t <= self.project.cues[self.last_marked].start:
            self.statusBar().showMessage(tr('La siguiente marca debe estar después de la anterior.'), 5000)
            return
        self.record()
        if self.last_marked >= 0:
            previous = self.project.cues[self.last_marked]
            previous_duration = previous.duration
            previous.end = t
            retime_cue(previous, previous_duration)
        cue = self.project.cues[index]
        # Keep the provisional duration until the next mark closes it. Shrinking it here and
        # stretching it later would pass syllables/keyframes through clamp_cue's minimums.
        previous_duration = cue.duration
        cue.start = t
        cue.end = min(self.project.duration, t + previous_duration)
        retime_cue(cue, previous_duration)
        self.changed(tables=True)
        self.loading = True
        self.table.selectRow(min(index+1, len(self.project.cues)-1))
        self.loading = False
        self.last_marked = index
        self.mark_index = index + 1
        self.waveform.selected = self.selected_index()
        self.refresh_panels()
        self.update_labels()
        if self.mark_index >= len(self.project.cues):
            self.statusBar().showMessage(tr('Última frase iniciada. Usa «Marcar final» al terminar.'), 6000)

    def mark_end(self):
        index = self.last_marked if self.last_marked >= 0 else self.selected_index()
        if not 0 <= index < len(self.project.cues):
            return
        cue = self.project.cues[index]
        t = self.current_time()
        if t <= cue.start:
            self.statusBar().showMessage(tr('El final debe estar después del inicio.'), 5000)
            return
        self.record()
        previous_duration = cue.duration
        cue.end = t
        retime_cue(cue, previous_duration)
        self.changed(tables=True, panels=True)
        self.last_marked = -1

    def video_frame(self, frame, generation=None):
        if generation is not None and generation != self._source_generation:
            return
        if not frame.isValid() or self._pending_player_seek is not None:
            return
        if self.project.style.background != 'video' and not self._warming_video:
            return  # The preview does not draw video: skip the costly conversion.
        if self.is_playing():
            if self._frame_clock.isValid() and self._frame_clock.elapsed() < 30:
                return
            self._frame_clock.restart()
        start = frame.startTime()/1000000
        finish = frame.endTime()/1000000
        if not self.is_playing() and start >= 0:
            tolerance = max(.15, finish-start if finish > start else 0)
            if abs(start-self._desired_position) > tolerance:
                return
        image = frame.toImage()
        if image.isNull():
            return
        self.preview.video = image
        self._video_at = self._desired_position if not self.is_playing() else start
        self.preview.update()
        if self._warming_video:
            self.finish_video_prime()

    def media_status_changed(self, status):
        if status in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia):
            if self._pending_player_seek is not None:
                target = self._pending_player_seek
                self._pending_player_seek = None
                self._desired_position = target
                self._seeking = True
                try:
                    self.player.setPosition(round(target*1000))
                finally:
                    self._seeking = False
                self.set_position(target, allow_loop=False)
            if not executable('ffmpeg') and not self.is_playing():
                self.still_timer.start(0)
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self._pending_player_seek = None
            if self._warming_video:
                self.finish_video_prime()

    def video_available(self, available):
        if available and not self.is_playing() and not executable('ffmpeg'):
            self.still_timer.start(0)

    def cancel_still_frames(self):
        self._still_serial += 1
        if hasattr(self, 'still_timer'):
            self.still_timer.stop()
        for job in tuple(self.still_jobs):
            if job.isRunning():
                job.cancel()

    def request_still_frame(self):
        self.cancel_still_frames()
        if (self.project.style.background == 'video' and self.project.media
                and Path(self.project.media).is_file() and not self.is_playing()):
            self.still_timer.start(100)

    def start_still_frame(self):
        if (self.project.style.background != 'video' or self.is_playing()
                or not self.project.media or not Path(self.project.media).is_file()):
            return
        if not executable('ffmpeg'):
            self.begin_video_prime()
            return
        serial, generation, target = self._still_serial, self._source_generation, self._desired_position
        job = StillFrameWorker(self.project.media, target, self)
        self.still_jobs.append(job)
        job.ready.connect(lambda img, token=serial, source=generation, t=target: self.still_frame_ready(img, token, source, t))
        job.failed.connect(lambda message, token=serial, source=generation: self.still_frame_failed(message, token, source))
        job.finished.connect(lambda job=job: self.still_job_finished(job))
        job.start()

    def still_frame_ready(self, image, serial, generation, target):
        if (serial != self._still_serial or generation != self._source_generation or self.is_playing()
                or self.project.style.background != 'video' or abs(target-self._desired_position) > .001):
            return
        self.preview.video = image
        self._video_at = target
        self.preview.update()

    def still_frame_failed(self, message, serial, generation):
        if serial == self._still_serial and generation == self._source_generation and not self.is_playing():
            self.statusBar().showMessage(tr('Fotograma: ') + message, 9000)
            # Qt provides a decoder fallback if standalone FFmpeg cannot read this file.
            self.begin_video_prime()

    def still_job_finished(self, job):
        if job in self.still_jobs:
            self.still_jobs.remove(job)
        job.deleteLater()

    def begin_video_prime(self):
        if (self._warming_video or self.is_playing() or self._pending_player_seek is not None
                or self.project.style.background != 'video' or not self.player.hasVideo()):
            return
        if self._video_at is not None and abs(self._video_at-self._desired_position) < .05 and self.preview.video is not None:
            return
        self._prime_mute_before = self.audio.isMuted()
        self.audio.setMuted(True)
        self._warming_video = True
        self.prime_timer.start(2000)
        self.player.setPosition(round(self._desired_position*1000))
        if self._warming_video:
            self.player.play()

    def finish_video_prime(self):
        if not self._warming_video:
            return
        self._warming_video = False
        self.prime_timer.stop()
        self.player.pause()
        self._seeking = True
        try:
            self.player.setPosition(round(self._desired_position*1000))
        finally:
            self._seeking = False
        self.audio.setMuted(self._prime_mute_before)
        self.set_position(self._desired_position, allow_loop=False)

    def media_duration(self, milliseconds):
        if self.adopt_duration and milliseconds > 0:
            self.project.duration = milliseconds / 1000
            self.adopt_duration = False
            self.changed(panels=True)

    def set_media_source(self, force=False, position=None):
        if self.loaded_media == self.project.media and not force:
            return
        self.pause()
        self.cancel_still_frames()
        self._source_generation += 1
        generation = self._source_generation
        target = self.position if position is None else min(self.project.duration, max(0, position))
        self._desired_position = target
        self._pending_player_seek = target if self.project.media else None
        self.loaded_media = self.project.media
        self.preview.video = None
        self._video_at = None
        old_sink = self.sink
        self.sink = QVideoSink(self)
        self.sink.videoFrameChanged.connect(lambda frame, gen=generation: self.video_frame(frame, gen))
        self.player.setVideoSink(self.sink)
        old_sink.deleteLater()
        self.waveform.peaks = []
        self.waveform.hint = tr('Preparando forma de onda…') if self.project.media else tr('Sin audio: puedes probar los efectos con el reloj de vista previa.')
        if self.wave_job and self.wave_job.isRunning():
            self.wave_job.cancel()
            self.wave_job.wait(3000)
        if self.project.media and Path(self.project.media).is_file():
            self.player.setSource(QUrl.fromLocalFile(self.project.media))
            self.wave_job = WaveWorker(self.project.media, self)
            source = self.project.media
            self.wave_job.ready.connect(lambda peaks, duration, expected=source: self.wave_ready(peaks, duration) if self.project.media == expected else None)
            self.wave_job.failed.connect(lambda message, expected=source: self.wave_failed(message) if self.project.media == expected else None)
            self.wave_job.start()
        else:
            self._pending_player_seek = None
            self.player.setSource(QUrl())
            if self.project.media:
                self.waveform.hint = tr('Medio no encontrado. Vuelve a vincularlo con «Audio / video».')
                self.statusBar().showMessage(self.waveform.hint, 12000)
        self.waveform.update()
        self.seek(target)

    def wave_ready(self, peaks, duration):
        self.waveform.peaks = peaks
        self.waveform.audio_duration = duration
        self.waveform.update()

    def wave_failed(self, message):
        self.waveform.hint = message
        self.waveform.update()
        self.statusBar().showMessage(message, 12000)

    def choose_media(self):
        path, _ = QFileDialog.getOpenFileName(self, tr('Cargar audio o video'), '', media_filter())
        if path:
            self.record()
            self.project.media = str(Path(path).resolve())
            self.project.playhead = 0.0
            self.adopt_duration = True
            if Path(path).suffix.lower() in ('.mp4', '.m4v', '.mkv', '.webm', '.mov', '.avi', '.wmv', '.flv', '.mpg', '.mpeg'):
                self.project.style.background = 'video'
            elif self.project.style.background == 'video':
                self.project.style.background = 'gradient'
            if self.project.style.match_media and not self.adopt_base_video():
                self.project.style.match_media = False
            self.set_media_source(force=True, position=0)
            self.changed(panels=True)

    def choose_image(self):
        path, _ = QFileDialog.getOpenFileName(self, tr('Imagen de fondo'), '', image_filter())
        if path:
            if QImage(path).isNull():
                QMessageBox.warning(self, tr('Imagen no compatible'), tr('No se pudo leer esta imagen.'))
                return
            self.record()
            self.project.image = str(Path(path).resolve())
            self.project.style.background = 'image'
            self.changed(panels=True)

    def confirm_unsaved(self):
        if not self.dirty:
            return True
        answer = QMessageBox.question(self, tr('Guardar proyecto'), tr('Hay cambios sin guardar. ¿Quieres guardarlos?'),
                                      QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                      QMessageBox.StandardButton.Save)
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            return self.save_project()
        return True

    def new_project(self):
        if not self.confirm_unsaved():
            return
        self.pause()
        self.project, self.path = Project(), None
        self.project.cues = []
        self.history.clear()
        self.future.clear()
        self.dirty = False
        self.mark_index, self.last_marked = 0, -1
        self.reset_text_editors()
        self.refresh_all()
        self.set_media_source(force=True)
        self.seek(0)
        self.remove_recovery()

    def load_project_path(self, path, project=None):
        project = load(path) if project is None else project
        self.pause()
        self.font_preview_end()
        self.project, self.path = project, Path(path)
        self.history.clear()
        self.future.clear()
        self.dirty = False
        self.mark_index, self.last_marked = 0, -1
        self.adopt_duration = False
        if self.project.style.match_media:
            before = (project.style.width, project.style.height, project.style.fps)
            if self.adopt_base_video():
                self.dirty = before != (project.style.width, project.style.height, project.style.fps)
        self.reset_text_editors(restore=True)
        self.refresh_all()
        self.set_media_source(force=True, position=project.playhead)
        self.remove_recovery()

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, tr('Abrir proyecto'), '', 'Lyric Candle (*.lyric.json *.json)')
        if path and self.confirm_unsaved():
            try:
                project = self.load_checked(path, tr('Abrir proyecto'))
                if project is not None:
                    self.load_project_path(path, project)
                    self.offer_relink()
            except Exception as exc:
                QMessageBox.warning(self, tr('No se pudo abrir'), str(exc))

    def offer_relink(self):
        """Ask for media/image files that are not at any remembered location."""
        for key, caption, file_filter in (('media', tr('el audio / video'), media_filter()),
                                          ('image', tr('la imagen de fondo'), image_filter())):
            value = getattr(self.project, key)
            if not value or Path(value).is_file():
                continue
            answer = QMessageBox.question(self, tr('Archivo no encontrado'),
                                          tr('No se encontró {0}:\n{1}\n\n¿Quieres buscarlo?').format(caption, value),
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                continue
            start = str(self.path.parent) if self.path else ''
            path, _ = QFileDialog.getOpenFileName(self, tr('Buscar ') + caption, start, file_filter)
            if not path:
                continue
            setattr(self.project, key, str(Path(path).resolve()))
            self.dirty = True
            if key == 'media':
                if self.project.style.match_media:
                    self.adopt_base_video()
                self.set_media_source(force=True, position=self.project.playhead)
            self.refresh_all()
            self.statusBar().showMessage(tr('Archivo vinculado. Guarda el proyecto para recordarlo.'), 8000)

    def open_demo(self):
        if self.confirm_unsaved():
            self.load_project_path(ROOT / 'examples' / 'Demo.lyric.json')
            self.path = None
            self.seek(1.4)

    def save_project(self):
        if self.path is None or self.path.parent == ROOT / 'examples':
            return self.save_as()
        return self.write_project(self.path)

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, tr('Guardar proyecto'), str(self.path or Path.home() / tr('Mi-video.lyric.json')),
                                             'Lyric Candle (*.lyric.json)')
        if not path:
            return False
        if not path.lower().endswith('.json'):
            path += '.lyric.json'
        return self.write_project(Path(path))

    def write_project(self, path):
        try:
            self.project.playhead = min(self.project.duration, max(0, self.position))
            save(self.project_with_drafts(), path)
            self.path = Path(path)
            self.dirty = False
            self.remove_recovery()
            self.update_labels()
            self.statusBar().showMessage(tr('Proyecto guardado en {0}. Los medios se vinculan; conserva sus archivos.').format(time_text(self.project.playhead)), 6000)
            return True
        except Exception as exc:
            QMessageBox.warning(self, tr('No se pudo guardar'), str(exc))
            return False

    def import_lyrics(self):
        dialog = ImportDialog(self.project.duration, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.record()
            if dialog.replace.isChecked():
                self.reset_text_editors()
                self.project.cues = dialog.cues
            else:
                self.project.cues.extend(dialog.cues)
                self.project.cues.sort(key=lambda c: c.start)
            self.mark_index, self.last_marked = 0, -1
            self.changed(tables=True, panels=True)
            self.table.selectRow(0)

    def autosave(self):
        if self.dirty:
            try:
                self.project.playhead = min(self.project.duration, max(0, self.position))
                save(self.project_with_drafts(), self.recovery_path, relative=False)
            except Exception:
                logging.exception('Autosave failed')
                self.statusBar().showMessage(tr('No se pudo crear el autoguardado. Guarda el proyecto manualmente.'), 8000)

    def remove_recovery(self):
        try:
            self.recovery_path.unlink(missing_ok=True)
        except OSError:
            logging.exception('Recovery cleanup failed')

    def orphan_recoveries(self):
        """Autosaves of sessions that are no longer running, newest first.
        Includes the single recovery.lyric.json written by versions before 0.2.3."""
        found = []
        for path in self.recovery_dir.glob('recovery*.lyric.json'):
            if path == self.recovery_path:
                continue
            lock = QLockFile(str(path.with_name(path.name[:-len('.lyric.json')] + '.lock')))
            lock.setStaleLockTime(0)
            if lock.tryLock(0):  # Its owner is gone (Qt removes locks of dead processes).
                lock.unlock()
                found.append(path)
        return sorted(found, key=lambda path: path.stat().st_mtime, reverse=True)

    def offer_recovery(self):
        for path in self.orphan_recoveries():
            answer = QMessageBox.question(self, tr('Recuperar sesión'),
                                          tr('Hay un autoguardado de una sesión que se cerró inesperadamente ({0}). ¿Recuperarlo?').format(time.strftime("%Y-%m-%d %H:%M", time.localtime(path.stat().st_mtime))),
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                path.unlink(missing_ok=True)
                continue
            try:
                project = self.load_checked(path, tr('No se pudo recuperar'))
                if project is None:
                    return
                self.project = project
                self.path = None
                self.dirty = True
                if self.project.style.match_media:
                    self.adopt_base_video()
                self.reset_text_editors(restore=True)
                self.refresh_all()
                self.set_media_source(force=True, position=self.project.playhead)
                self.autosave()  # Now owned by this session.
                path.unlink(missing_ok=True)
            except Exception as exc:
                QMessageBox.warning(self, tr('No se pudo recuperar'), str(exc))
            return

    def load_checked(self, path, title):
        """Load strictly; if only timings need review, offer to open it for correction."""
        try:
            return load(path)
        except ProjectIssues as exc:
            listed = '\n'.join('• ' + issue for issue in exc.issues[:10])
            more = tr('\n… y {0} más.').format(len(exc.issues)-10) if len(exc.issues) > 10 else ''
            answer = QMessageBox.question(self, title,
                                          tr('El proyecto tiene {0} ajuste(s) pendiente(s):\n\n{1}{2}\n\n¿Abrirlo de todos modos para corregirlo? La exportación seguirá bloqueada hasta resolverlos.').format(len(exc.issues), listed, more),
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            return load(path, strict=False) if answer == QMessageBox.StandardButton.Yes else None

    def export_video(self):
        if self.export_job and self.export_job.isRunning():
            self.statusBar().showMessage(tr('Ya hay una exportación en curso.'), 5000)
            return
        drafts = self.all_text_drafts()
        if drafts:
            row = next(i for i, cue in enumerate(self.project.cues) if cue.uid in drafts)
            self.table.selectRow(row)
            self.tabs.setCurrentIndex(0)
            QMessageBox.information(self, tr('Texto sin aplicar'),
                                    tr('Hay {0} frase(s) con texto sin aplicar. Revisa y aplica sus cambios antes de exportar. '
                                       'Guardar conserva los borradores para retomarlos después.').format(len(drafts)))
            return
        if not executable('ffmpeg'):
            QMessageBox.information(self, tr('Hace falta FFmpeg'), tr('Puedes editar y previsualizar. Para exportar, coloca ffmpeg.exe y ffprobe.exe en tools/ o instala FFmpeg en PATH.\n\nConsulta LEEME.md.'))
            return
        problems = self.project.problems()
        if problems:
            QMessageBox.warning(self, tr('Corrige los tiempos antes de exportar'), '\n'.join(problems[:15]))
            return
        if any(self.preview.renderer.overflow(self.project, cue) for cue in self.project.cues):
            if QMessageBox.question(self, tr('Texto fuera de márgenes'), tr('Hay frases que exceden los márgenes y pueden cortarse. ¿Exportar de todos modos?'),
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
        ext, folder, stem = '.mp4', Path.home(), tr('Mi-video-lyrics')
        if self.project.media:
            folder, stem = Path(self.project.media).parent, Path(self.project.media).stem + '-lyrics'
        if self.project.style.export_format == 'source' and self.project.media:
            info = self.media_info(quiet=False)
            if info is None:
                QMessageBox.warning(self, tr('Formato del video base'), tr('Para exportar como el video base hace falta ffprobe '
                                    '(junto a ffmpeg en tools/ o en PATH) y un medio legible.'))
                return
            if info.get('video'):
                ext = info['ext'] if info['ext'] in SOURCE_CONTAINERS else '.mkv'
        name = CONTAINER_NAMES.get(ext, ext.lstrip('.').upper())
        path, _ = QFileDialog.getSaveFileName(self, tr('Exportar video'), str(folder / (stem + ext)), tr('Video {0} (*{1})').format(name, ext))
        if not path:
            return
        if not path.lower().endswith(ext):
            path += ext
        self.pause()
        self.export_dialog = QProgressDialog(tr('Generando video…'), tr('Cancelar'), 0, 100, self)
        self.export_dialog.setWindowTitle(tr('Exportar · Lyric Candle'))
        self.export_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.export_dialog.setAutoClose(False)
        self.export_dialog.setAutoReset(False)
        self.export_dialog.setMinimumDuration(0)
        self.export_job = ExportWorker(self.project, path, self)
        self.export_job.progress.connect(self.export_dialog.setValue)
        self.export_job.done.connect(self.export_done)
        self.export_job.failed.connect(self.export_failed)
        self.export_job.cancelled.connect(self.export_cancelled)
        self.export_dialog.canceled.connect(self.export_job.cancel)
        self.export_dialog.show()
        self.export_job.start()

    def export_done(self, path):
        if self.export_dialog:
            self.export_dialog.close()
        job = self.export_job
        details = tr('\n\nFormato: {0}').format(job.summary) + (f'\n{job.note}' if job.note else '') if job else ''
        QMessageBox.information(self, tr('Video exportado'), tr('Video generado correctamente:\n') + path + details)

    def export_failed(self, message):
        if self.export_dialog:
            self.export_dialog.close()
        QMessageBox.warning(self, tr('No se pudo exportar'), message)

    def export_cancelled(self):
        if self.export_dialog:
            self.export_dialog.close()
        self.statusBar().showMessage(tr('Exportación cancelada. El archivo anterior se conserva.'), 7000)

    def show_help(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(tr('Lyric Candle · Guía rápida'))
        dialog.resize(780, 680)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(guide_html(version_label(), is_portable(), str(data_dir()), bool(executable('ffmpeg'))))
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


def main():
    if sys.platform == 'win32':
        try:  # Own taskbar identity, so Windows shows our icon instead of Python's.
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('JAVCIF.LyricCandle')
        except (AttributeError, OSError):
            pass
    app = QApplication(sys.argv)
    app.setOrganizationName('JAVCIF')
    app.setApplicationName('LyricCandleAlpha')
    app.setWindowIcon(app_icon())
    set_language(resolve(app_settings().value('language', 'auto'), QLocale.system().uiLanguages()))
    # Qt's own texts (Yes/No/Save buttons, file and color dialogs) in the same language.
    qt_translator = QTranslator(app)
    if qt_translator.load(f'qtbase_{language()}', QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(qt_translator)
    log_dir = data_dir()
    logging.basicConfig(filename=log_dir / 'app.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    def handle_error(kind, value, tb):
        logging.error('Unhandled exception', exc_info=(kind, value, tb))
        QMessageBox.critical(None, tr('Lyric Candle · error'), tr('{0}\n\nSe guardó el detalle en:\n{1}').format(value, log_dir / "app.log"))
    sys.excepthook = handle_error
    window = MainWindow()
    window.show()
    code = app.exec()
    if window.restart_requested:
        # Same program and arguments: LyricCandle.exe when packaged, python main.py from source.
        arguments = sys.argv[1:] if getattr(sys, 'frozen', False) else sys.argv
        QProcess.startDetached(sys.executable, arguments)
    return code
