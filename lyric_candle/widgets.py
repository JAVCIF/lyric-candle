from __future__ import annotations
import math
from pathlib import Path
from dataclasses import replace
from PySide6.QtCore import Qt, QRectF, Signal, QPointF, QEvent, QTimer, QSize
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import (QColor, QPainter, QPen, QLinearGradient, QCursor, QIcon, QPixmap,
                           QPainterPath, QFont, QFontMetricsF)
from PySide6.QtWidgets import (QWidget, QPushButton, QColorDialog, QFontComboBox, QCompleter,
                              QListView, QSpinBox, QDoubleSpinBox, QAbstractSpinBox, QToolButton)
from .render import Renderer
from .model import time_text
from .i18n import tr


LOGO_PATH = Path(__file__).resolve().parent / 'assets' / 'logo.svg'


def logo_pixmap(size, ratio=1.0):
    """The Lyric Candle badge rendered from its SVG at a given logical size."""
    pixmap = QPixmap(round(size * ratio), round(size * ratio))
    pixmap.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(str(LOGO_PATH))
    if renderer.isValid():
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(p, QRectF(0, 0, pixmap.width(), pixmap.height()))
        p.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def app_icon():
    """Window/taskbar icon with pre-rendered sizes (no SVG icon plugin needed)."""
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(logo_pixmap(size))
    return icon


class BrandMark(QWidget):
    """In-app wordmark, adapted from Sonic Candle's header: the name, the same white candle,
    and instead of a fading signal a line of karaoke words. Words behind the flame are
    repainted, the current one is lifted in the emphasis color, the rest wait unlit."""
    TEXT = 'Lyric Candle'
    WORDS = (13, 21, 9, 17, 24, 11, 19)  # Word widths at 31 px, like Sonic's blocks.
    CURRENT = 2  # Words before this index are repainted; this one is emphasized.

    def __init__(self, pixel_size=26, parent=None):
        super().__init__(parent)
        self.pixel_size = pixel_size
        self.text_color = QColor('#eaf3ff')
        self.painted = QColor('#63b8ff')
        self.current = QColor('#ffe49c')
        self.unlit = QColor('#3e5675')
        self.setToolTip('Lyric Candle')
        self.setAccessibleName('Lyric Candle')
        self.setFixedSize(self.sizeHint())

    def changeEvent(self, event):
        # The stylesheet font arrives after construction: re-measure when it changes.
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self.setFixedSize(self.sizeHint())
        super().changeEvent(event)

    def brand_font(self):
        # Start from the widget's resolved font (the app stylesheet sets the family), so the
        # measured width matches the drawn text.
        font = QFont(QWidget.font(self))
        font.setPixelSize(self.pixel_size)
        font.setBold(True)
        return font

    def k(self):
        return self.pixel_size / 31  # Sonic Candle draws its candle for a 31 px font.

    def baseline(self, metrics):
        # Room above the text for the flame, which rises 48 px (at 31 px) over the baseline.
        return max(metrics.ascent(), 48 * self.k()) + 2

    def sizeHint(self):
        metrics = QFontMetricsF(self.brand_font())
        k = self.k()
        words = sum(self.WORDS) * k + 5 * k * (len(self.WORDS) - 1)
        width = metrics.horizontalAdvance(self.TEXT) + 12 * k + 16 * k + words + 4
        return QSize(int(math.ceil(width)), int(math.ceil(self.baseline(metrics) + metrics.descent() + 2)))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        k = self.k()
        font = self.brand_font()
        metrics = QFontMetricsF(font)
        baseline = self.baseline(metrics)
        p.setFont(font)
        p.setPen(self.text_color)
        p.drawText(QPointF(0, baseline), self.TEXT)
        x = metrics.horizontalAdvance(self.TEXT) + 12 * k
        # Candle and flame: Sonic Candle's geometry, scaled.
        top = baseline - 25 * k
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.text_color)
        p.drawRoundedRect(QRectF(x, top, 9 * k, 26 * k), 1 * k, 1 * k)
        flame = QPainterPath(QPointF(x + 4.5 * k, top - 5 * k))
        flame.cubicTo(x - 1 * k, top - 12 * k, x + 8 * k, top - 16 * k, x + 6 * k, top - 23 * k)
        flame.cubicTo(x + 14 * k, top - 14 * k, x + 12 * k, top - 7 * k, x + 4.5 * k, top - 5 * k)
        p.drawPath(flame)
        # Karaoke words along the baseline.
        word_x = x + 16 * k
        line_y = baseline - 1 * k
        for index, width in enumerate(self.WORDS):
            w = width * k
            if index < self.CURRENT:
                color, rect = self.painted, QRectF(word_x, line_y - 5 * k, w, 6 * k)
            elif index == self.CURRENT:  # Emphasis: lifted and slightly larger.
                color, rect = self.current, QRectF(word_x - 1.5 * k, line_y - 14 * k, w + 3 * k, 8 * k)
            else:
                color, rect = self.unlit, QRectF(word_x, line_y - 5 * k, w, 6 * k)
            p.setBrush(color)
            p.drawRoundedRect(rect, 2 * k, 2 * k)
            word_x += w + 5 * k
        p.end()


def transport_icon(kind, color='#eaf3ff', size=18):
    """Vector play/pause glyph drawn at 1x and 2x, so it stays sharp on HiDPI screens."""
    icon = QIcon()
    for ratio in (1, 2):
        pixmap = QPixmap(size * ratio, size * ratio)
        pixmap.setDevicePixelRatio(ratio)
        pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        s = float(size)
        if kind == 'play':
            # Slightly right of centre: a triangle looks centred when its mass is.
            path = QPainterPath(QPointF(s * .30, s * .17))
            path.lineTo(s * .84, s * .50)
            path.lineTo(s * .30, s * .83)
            path.closeSubpath()
            p.drawPath(path)
        else:
            for x in (.22, .58):
                p.drawRoundedRect(QRectF(s * x, s * .18, s * .20, s * .64), s * .05, s * .05)
        p.end()
        icon.addPixmap(pixmap)
    return icon


class _ExplicitStepButtons:
    """Keep Qt's numeric editor, with real buttons independent of native spin arrows."""
    def _setup_steps(self):
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setMinimumHeight(30)
        self.setMinimumWidth(105)
        self.setStyleSheet('QSpinBox, QDoubleSpinBox { padding-right:62px; }')
        self.minus_button = QToolButton(self)
        self.plus_button = QToolButton(self)
        for button, text, name, direction in ((self.minus_button, '−', tr('Disminuir'), -1),
                                               (self.plus_button, '+', tr('Aumentar'), 1)):
            button.setText(text)
            button.setToolTip(name)
            button.setAccessibleName(name + tr(' valor'))
            button.setObjectName('stepMinus' if direction < 0 else 'stepPlus')
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setAutoRepeat(True)
            button.setAutoRepeatDelay(450)
            button.setAutoRepeatInterval(90)
            button.setStyleSheet('''QToolButton { background:#253b57; color:#eaf3ff;
                border:1px solid #476080; border-radius:3px; padding:0;
                font-size:16px; font-weight:600; }
                QToolButton:hover { background:#345776; }
                QToolButton:pressed { background:#42739d; }
                QToolButton:disabled { background:#1b293b; color:#61758c; border-color:#2e4057; }''')
            button.clicked.connect(lambda checked=False, d=direction: self._step_clicked(d))
        self.valueChanged.connect(self._update_steps)
        self._layout_steps()
        self._update_steps()

    def _step_clicked(self, direction):
        if self.isEnabled() and not self.isReadOnly():
            self.interpretText()
            self.stepBy(direction)
            self._update_steps()

    def _layout_steps(self):
        if not hasattr(self, 'plus_button'):
            return
        height = max(18, self.height()-6)
        self.plus_button.setGeometry(self.width()-29, 3, 26, height)
        self.minus_button.setGeometry(self.width()-58, 3, 26, height)
        self.minus_button.raise_()
        self.plus_button.raise_()

    def _update_steps(self, *_):
        if not hasattr(self, 'plus_button'):
            return
        flags = self.stepEnabled()
        self.plus_button.setEnabled(not self.isReadOnly() and bool(flags & QAbstractSpinBox.StepEnabledFlag.StepUpEnabled))
        self.minus_button.setEnabled(not self.isReadOnly() and bool(flags & QAbstractSpinBox.StepEnabledFlag.StepDownEnabled))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_steps()

    def setRange(self, minimum, maximum):
        super().setRange(minimum, maximum)
        self._update_steps()

    def setMinimum(self, minimum):
        super().setMinimum(minimum)
        self._update_steps()

    def setMaximum(self, maximum):
        super().setMaximum(maximum)
        self._update_steps()

    def setReadOnly(self, read_only):
        super().setReadOnly(read_only)
        self._update_steps()


class StepSpinBox(_ExplicitStepButtons, QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_steps()


class StepDoubleSpinBox(_ExplicitStepButtons, QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_steps()


class ColorButton(QPushButton):
    changed = Signal(str)

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = color
        self.setMinimumWidth(100)
        self.clicked.connect(self.choose)
        self.set_color(color)

    def set_color(self, value):
        self.color = value
        self.setText(value.upper())
        c = QColor(value)
        fg = '#111827' if c.lightnessF() > 0.55 else '#ffffff'
        self.setStyleSheet(f'background:{value}; color:{fg}; border:1px solid #61728d; padding:5px; border-radius:5px;')

    def choose(self):
        c = QColorDialog.getColor(QColor(self.color), self, tr('Elegir color'))
        if c.isValid():
            self.set_color(c.name())
            self.changed.emit(c.name())


class HoverFontComboBox(QFontComboBox):
    fontHovered = Signal(str)
    fontCommitted = Signal(str)
    previewEnded = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.popup_open = False
        self.completion_open = False
        self._typed_dirty = False
        self._completion_popup = None
        self._font_popup_window = None
        self._last_hover = ''
        self.view().setMouseTracking(True)
        self.view().installEventFilter(self)
        self.view().viewport().setMouseTracking(True)
        self.view().viewport().installEventFilter(self)
        self._font_popup_window = self.view().window()
        self._font_popup_window.installEventFilter(self)
        self.highlighted.connect(self._hover_index)
        self.activated.connect(self._commit_index)
        if self.lineEdit():
            self.lineEdit().textEdited.connect(lambda: setattr(self, '_typed_dirty', True))
            self.lineEdit().editingFinished.connect(self._commit_typed)
        if self.completer():
            self.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            if self.completer().popup() is None:
                self.completer().setPopup(QListView(self))
            self._completion_popup = self.completer().popup()
            self._completion_popup.setMouseTracking(True)
            self._completion_popup.viewport().setMouseTracking(True)
            self._completion_popup.viewport().installEventFilter(self)
            self.completer().highlighted[str].connect(self._completion_hover)
            self.completer().activated[str].connect(self._completion_commit)
            self._completion_popup.installEventFilter(self)

    def preview_open(self):
        return self.popup_open or self.completion_open

    def _completion_hover(self, family):
        if self.findText(family, Qt.MatchFlag.MatchExactly) >= 0:
            self.fontHovered.emit(family)

    def _completion_commit(self, family):
        index = self.findText(family, Qt.MatchFlag.MatchExactly)
        if index >= 0:
            self._commit_index(index)

    def _hover_index(self, index):
        family = self.itemText(index)
        if self.popup_open and family and family != self._last_hover:
            self._last_hover = family
            self.fontHovered.emit(family)

    def _commit_index(self, index):
        self._typed_dirty = False
        family = self.itemText(index)
        if family:
            self.fontCommitted.emit(family)

    def _commit_typed(self):
        if not self.popup_open and self._typed_dirty:
            self._typed_dirty = False
            index = self.findText(self.currentText(), Qt.MatchFlag.MatchExactly)
            if index >= 0:
                self._commit_index(index)

    def showPopup(self):
        self.popup_open = True
        self._last_hover = ''
        super().showPopup()
        QTimer.singleShot(0, self._preview_under_pointer)

    def _preview_under_pointer(self):
        if self.popup_open:
            viewport = self.view().viewport()
            pos = viewport.mapFromGlobal(QCursor.pos())
            if viewport.rect().contains(pos):
                index = self.view().indexAt(pos)
                if index.isValid():
                    self._hover_index(index.row())

    def hidePopup(self):
        super().hidePopup()
        self.popup_open = False
        self._typed_dirty = False
        self._last_hover = ''
        self.previewEnded.emit()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            if self.popup_open:
                self.hidePopup()
                event.accept()
                return True
        if watched is self._font_popup_window and event.type() == QEvent.Type.Hide:
            self.popup_open = False
            self._typed_dirty = False
            self._last_hover = ''
            self.previewEnded.emit()
        if watched is self._completion_popup:
            if event.type() == QEvent.Type.Show:
                self.completion_open = True
            elif event.type() == QEvent.Type.Hide:
                self.completion_open = False
                self._typed_dirty = False
                self._last_hover = ''
                self.previewEnded.emit()
        if self._completion_popup is not None and watched is self._completion_popup.viewport():
            if event.type() == QEvent.Type.MouseMove:
                index = self._completion_popup.indexAt(event.position().toPoint())
                if index.isValid():
                    self._completion_hover(str(index.data(Qt.ItemDataRole.DisplayRole)))
            elif event.type() == QEvent.Type.Leave:
                self.previewEnded.emit()
        if watched is self.view().viewport():
            if event.type() == QEvent.Type.MouseMove:
                index = self.view().indexAt(event.position().toPoint())
                if index.isValid():
                    self._hover_index(index.row())
            elif event.type() == QEvent.Type.Leave:
                self._last_hover = ''
                self.previewEnded.emit()
        return super().eventFilter(watched, event)


class Preview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.time = 0
        self.video = None
        self.font_override = ''
        self.renderer = Renderer()
        self.guides = True
        self.setMinimumSize(360, 200)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def effective_project(self):
        if self.project is not None and self.font_override:
            return replace(self.project, style=replace(self.project.style, font=self.font_override))
        return self.project

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor('#080e18'))
        if self.project is None:
            return
        project = self.effective_project()
        s = project.style
        scale = min(self.width() / s.width, self.height() / s.height)
        dx = (self.width() - s.width * scale) / 2
        dy = (self.height() - s.height * scale) / 2
        p.translate(dx, dy)
        p.scale(scale, scale)
        p.setClipRect(QRectF(0, 0, s.width, s.height))
        self.renderer.draw(p, project, self.time, self.video)
        if self.guides:
            pen = QPen(QColor(180, 205, 240, 65), 1 / scale, Qt.PenStyle.DashLine)
            p.setPen(pen)
            m = s.margin
            p.drawRect(QRectF(m, m, s.width - 2 * m, s.height - 2 * m))
            p.drawLine(QPointF(s.width / 2, m), QPointF(s.width / 2, s.height - m))
        p.end()

    def mousePressEvent(self, event):
        self.setFocus()
        super().mousePressEvent(event)


class Waveform(QWidget):
    seek = Signal(float)
    edge_moved = Signal(str, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.peaks = []
        self.audio_duration = 0
        self.position = 0
        self.selected = -1
        self.zoom = False
        self.dragging = None
        self.drag_time = None
        self.hint = tr('Carga audio o video para ver la forma de onda.')
        self.setMinimumHeight(105)
        self.setMaximumHeight(145)
        self.setMouseTracking(True)
        self.setToolTip(tr('Clic: buscar. Arrastra los extremos de la frase seleccionada para ajustar sus tiempos.'))

    def range(self):
        duration = self.project.duration if self.project else 12
        if self.zoom and self.project and 0 <= self.selected < len(self.project.cues):
            cue = self.project.cues[self.selected]
            return max(0, cue.start - 1.5), min(duration, cue.end + 1.5)
        return 0, duration

    def x_time(self, x):
        lo, hi = self.range()
        return max(lo, min(hi, lo + x / max(1, self.width()) * (hi - lo)))

    def time_x(self, t):
        lo, hi = self.range()
        return (t - lo) / max(0.001, hi - lo) * self.width()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor('#101b2b'))
        lo, hi = self.range()
        mid = (self.height() + 20) / 2
        if self.project:
            for i, cue in enumerate(self.project.cues):
                a, b = self.time_x(cue.start), self.time_x(cue.end)
                if b < 0 or a > self.width():
                    continue
                selected = i == self.selected
                p.fillRect(QRectF(a, 23, b-a, self.height()-23), QColor(99, 184, 255, 38 if selected else 9))
                # Provisional (unmarked) phrases: dashed boundaries.
                p.setPen(QPen(QColor('#ffe49c' if selected else '#3e5675'), 2 if selected else 1,
                              Qt.PenStyle.SolidLine if cue.timed else Qt.PenStyle.DashLine))
                p.drawLine(QPointF(a, 23), QPointF(a, self.height()))
                if selected:
                    p.drawLine(QPointF(b, 23), QPointF(b, self.height()))
        if self.peaks and self.audio_duration:
            norm = max(max(self.peaks), 0.001)
            p.setPen(QPen(QColor('#6ba8c3'), 1))
            count = len(self.peaks)
            for x in range(0, self.width(), 2):
                # Each 2 px column shows the loudest peak in its time range, so short
                # attacks stay visible when a long song is zoomed out.
                t0 = lo + x / max(1, self.width()) * (hi - lo)
                t1 = lo + (x + 2) / max(1, self.width()) * (hi - lo)
                first = max(0, int(t0 / self.audio_duration * count))
                last = min(count, max(first + 1, int(math.ceil(t1 / self.audio_duration * count))))
                peak = max(self.peaks[first:last]) / norm if first < count else 0
                extent = peak * (self.height() - 32) * 0.43
                p.drawLine(QPointF(x, mid - extent), QPointF(x, mid + extent))
        else:
            p.setPen(QColor('#8295af'))
            p.drawText(QRectF(12, 40, self.width()-24, 36), Qt.AlignmentFlag.AlignCenter, self.hint)
        p.setPen(QColor('#93a5bf'))
        for i in range(7):
            t = lo + (hi - lo) * i / 6
            x = self.width() * i / 6
            p.drawText(QRectF(max(2, min(self.width()-78, x)), 2, 78, 20), time_text(t))
        x = self.time_x(self.position)
        p.setPen(QPen(QColor('#f6be6c'), 2))
        p.drawLine(QPointF(x, 22), QPointF(x, self.height()))
        if self.dragging in ('start', 'end') and self.drag_time is not None:
            # Live preview of the edge being dragged; applied on release.
            x = self.time_x(self.drag_time)
            p.setPen(QPen(QColor('#ffe49c'), 2, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(x, 23), QPointF(x, self.height()))
            label = QRectF(min(max(2, x + 4), self.width() - 80), self.height() - 22, 78, 18)
            p.fillRect(label, QColor(16, 27, 43, 220))
            p.setPen(QColor('#ffe49c'))
            p.drawText(label, Qt.AlignmentFlag.AlignCenter, time_text(self.drag_time))
        p.end()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        x = event.position().x()
        if self.project and 0 <= self.selected < len(self.project.cues):
            cue = self.project.cues[self.selected]
            for name, t in (('start', cue.start), ('end', cue.end)):
                if abs(x - self.time_x(t)) < 9:
                    self.dragging = name
                    self.drag_time = t
                    self.update()
                    return
        self.dragging = 'seek'
        self.seek.emit(self.x_time(x))

    def mouseMoveEvent(self, event):
        if self.dragging == 'seek':
            self.seek.emit(self.x_time(event.position().x()))
        elif self.dragging:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            self.drag_time = self.x_time(event.position().x())
            self.update()

    def mouseReleaseEvent(self, event):
        if self.dragging and self.dragging != 'seek':
            self.edge_moved.emit(self.dragging, self.x_time(event.position().x()))
        self.dragging = None
        self.drag_time = None
        self.unsetCursor()
        self.update()


class KeyframeCurve(QWidget):
    add_requested = Signal(float, float)
    moved = Signal(int, float, float)
    seek_requested = Signal(float)
    editing_started = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cue = None
        self.elapsed = 0.0
        self.drag_index = None
        self.drag_value = None
        self.drag_origin = None
        self.lock_time = False  # Dragging keeps each point's time (X).
        self.lock_progress = False  # Dragging keeps each point's progress (Y).
        self.setMinimumHeight(180)
        self.setMaximumHeight(260)
        self.setToolTip(tr('Doble clic: agregar keyframe. Arrastra un punto interior para moverlo. Clic en el gráfico: buscar ese instante.'))

    def plot_rect(self):
        return QRectF(38, 12, max(1, self.width()-52), max(1, self.height()-42))

    def point_xy(self, t, progress):
        from .model import keyframe_points
        points = keyframe_points(self.cue)
        a, b = points[0][0], points[-1][0]
        rect = self.plot_rect()
        return QPointF(rect.left()+(t-a)/max(.001, b-a)*rect.width(), rect.bottom()-progress*rect.height())

    def point_value(self, pos):
        from .model import keyframe_points
        points = keyframe_points(self.cue)
        a, b = points[0][0], points[-1][0]
        rect = self.plot_rect()
        fraction = min(1, max(0, (pos.x()-rect.left())/rect.width()))
        progress = min(1, max(0, (rect.bottom()-pos.y())/rect.height()))
        return a+fraction*(b-a), progress

    def paintEvent(self, event):
        from .model import keyframe_points, animation_progress
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor('#101b2b'))
        rect = self.plot_rect()
        p.setPen(QColor('#344b69'))
        for i in range(5):
            y = rect.bottom()-i/4*rect.height()
            p.setPen(QColor('#344b69'))
            p.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            p.setPen(QColor('#93a8c5'))
            p.drawText(QRectF(1, y-9, 34, 18), Qt.AlignmentFlag.AlignRight, str(i*25)+'%')
        if not self.cue:
            p.end()
            return
        points = keyframe_points(self.cue)
        if self.drag_index is not None and self.drag_value:
            points[self.drag_index+1] = self.drag_value
        p.setPen(QPen(QColor('#82c9ff' if self.cue.use_keyframes else '#66758b'), 2))
        for a, b in zip(points, points[1:]):
            p.drawLine(self.point_xy(*a), self.point_xy(*b))
        p.setBrush(QColor('#ffe49c'))
        p.setPen(Qt.PenStyle.NoPen)
        for i, point in enumerate(points):
            p.setBrush(QColor('#ffe49c' if 0 < i < len(points)-1 else '#7285a0'))
            p.drawEllipse(self.point_xy(*point), 5, 5)
        for i in range(4):
            t = points[0][0]+i/3*(points[-1][0]-points[0][0])
            x = rect.left()+i/3*rect.width()
            p.setPen(QColor('#93a8c5'))
            p.drawText(QRectF(max(0, min(self.width()-70, x-30)), rect.bottom()+5, 70, 20),
                       Qt.AlignmentFlag.AlignCenter, f'{t:.2f}s')
        if points[0][0] <= self.elapsed <= points[-1][0]:
            xy = self.point_xy(self.elapsed, animation_progress(self.cue, self.elapsed))
            p.setPen(QPen(QColor('#f6be6c'), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(xy.x(), rect.top()), QPointF(xy.x(), rect.bottom()))
            p.setBrush(QColor('#f6be6c'))
            p.drawEllipse(xy, 4, 4)
        p.end()

    def mousePressEvent(self, event):
        if not self.cue or event.button() != Qt.MouseButton.LeftButton:
            return
        for i, point in enumerate(self.cue.keyframes):
            xy = self.point_xy(point.time, point.progress)
            if (xy-event.position()).manhattanLength() < 13:
                self.editing_started.emit()
                self.drag_index = i
                self.drag_origin = self.drag_value = (point.time, point.progress)
                if self.lock_time != self.lock_progress:
                    self.setCursor(Qt.CursorShape.SizeVerCursor if self.lock_time else Qt.CursorShape.SizeHorCursor)
                return
        if self.plot_rect().contains(event.position()):
            self.seek_requested.emit(self.point_value(event.position())[0])

    def mouseMoveEvent(self, event):
        if self.drag_index is not None:
            time, progress = self.point_value(event.position())
            if self.lock_time:
                time = self.drag_origin[0]
            if self.lock_progress:
                progress = self.drag_origin[1]
            self.drag_value = (time, progress)
            self.update()

    def mouseReleaseEvent(self, event):
        if self.drag_index is not None:
            index, value, origin = self.drag_index, self.drag_value, self.drag_origin
            self.drag_index = self.drag_value = self.drag_origin = None
            self.unsetCursor()
            # A click without movement must not add an undo step.
            if value and (abs(value[0]-origin[0]) > 1e-6 or abs(value[1]-origin[1]) > 1e-6):
                self.moved.emit(index, *value)
            self.update()

    def mouseDoubleClickEvent(self, event):
        if self.cue and self.plot_rect().contains(event.position()):
            self.drag_index = None
            self.drag_value = None
            self.add_requested.emit(*self.point_value(event.position()))
