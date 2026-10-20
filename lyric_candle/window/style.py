"""Design and Effects tabs: layout, fonts, canvas, base video and export format."""
from __future__ import annotations

import subprocess
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QPushButton,
    QVBoxLayout,
)

from .. import media as media_tools
from ..i18n import tr
from ..media import canvas_size, describe_source, frame_rate, stream_info
from ..widgets import ColorButton, HoverFontComboBox, StepSpinBox
from .common import FPS_PRESETS, RESOLUTIONS, fps_text


class StyleMixin:
    """Mixin for MainWindow: design and Effects tabs: layout, fonts, canvas, base video and export format."""

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
        if not media or not Path(media).is_file() or not media_tools.executable('ffprobe'):
            return None
        try:
            key = (media, Path(media).stat().st_mtime)
        except OSError:
            return None
        if self._media_info[0] != key:
            try:
                self._media_info = (key, stream_info(media))
            except (OSError, ValueError, subprocess.SubprocessError) as exc:  # Unreadable file or ffprobe failure.
                self._media_info = (key, None)
                if not quiet:
                    self.statusBar().showMessage(tr('No se pudo leer el video: ') + str(exc)[:200], 9000)
        return self._media_info[1]

    def base_video_canvas(self):
        """(width, height, fps) of the base video for the canvas, or None with a message."""
        if not media_tools.executable('ffprobe'):
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
        elif not media_tools.executable('ffprobe'):
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
