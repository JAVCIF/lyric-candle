"""One fixed-layout painter for preview and exported frames."""
from __future__ import annotations
import math
from functools import lru_cache
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QImage, QLinearGradient,
                           QPainter, QPainterPath, QPen)
from .model import Project, Cue, animation_progress, animation_clock


@lru_cache(maxsize=1200)
def geometry(text, family, pixels, marked_ranges):
    font = QFont(family)
    font.setPixelSize(pixels)
    font.setWeight(QFont.Weight.DemiBold)
    # Disable kerning consistently so marking a boundary never shifts later letters.
    font.setKerning(False)
    fm = QFontMetricsF(font)
    parts = []
    pos = 0
    for index, (begin, end) in enumerate(marked_ranges):
        if begin > pos:
            parts.append((pos, begin, -1))
        parts.append((begin, end, index))
        pos = end
    if pos < len(text):
        parts.append((pos, len(text), -1))
    runs = []
    x = 0.0
    for begin, end, span_index in parts:
        fragment = text[begin:end]
        advance = fm.horizontalAdvance(fragment)
        path = QPainterPath()
        path.addText(QPointF(x, 0), font, fragment)
        runs.append((x, advance, span_index, path))
        x += advance
    return x, fm.ascent(), fm.descent(), runs


def clamp(value, low=0.0, high=1.0):
    return min(high, max(low, value))


def visibility(cue, t, style):
    fades = style.mode == 'fade' or (style.mode == 'advanced' and style.fade)
    tail = style.fade_out if fades and style.crossfade else 0
    if not cue.start <= t < cue.end + tail:
        return 0.0
    if not fades:
        return 1.0
    inside = (t - cue.start) / style.fade_in if style.fade_in > 0 else 1
    end = cue.end + tail
    outside = (end - t) / style.fade_out if style.fade_out > 0 else 1
    return clamp(min(inside, outside))


def line_positions(style, widths, ascents, descents):
    """Aligned anchors depend on layout and font metrics, never on animated bounds."""
    w, h, m = style.width, style.height, style.margin
    position = style.position
    if position.startswith('left'):
        xs = [m for _ in widths]
    elif position.startswith('right'):
        xs = [w - m - width for width in widths]
    else:
        xs = [(w - width) / 2 for width in widths]
    if len(widths) == 1:
        if position.endswith('top'):
            ys = [m + ascents[0]]
        elif position.endswith('bottom'):
            ys = [h - m - descents[0]]
        else:
            ys = [(h + ascents[0] - descents[0]) / 2]
    elif position.endswith('split'):
        ys = [m + ascents[0], h - m - descents[1]]
    else:
        total = sum(a + d for a, d in zip(ascents, descents)) + style.gap
        top = (h - total) / 2
        ys = [top + ascents[0], top + ascents[0] + descents[0] + style.gap + ascents[1]]
    return list(zip(xs, ys))


class Renderer:
    def __init__(self):
        self.image_path = None
        self.background_image = QImage()

    def draw(self, p: QPainter, project: Project, t: float, video=None):
        s = project.style
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(0, 0, s.width, s.height)
        p.fillRect(rect, QColor(s.background_color))
        if s.background == 'image':
            if self.image_path != project.image:
                self.image_path = project.image
                self.background_image = QImage(project.image) if project.image else QImage()
            self.draw_fit(p, rect, self.background_image)
        elif s.background == 'video' and video is not None and not video.isNull():
            self.draw_fit(p, rect, video)
        else:
            gradient = QLinearGradient(0, 0, s.width, s.height)
            gradient.setColorAt(0, QColor(s.background_color))
            gradient.setColorAt(0.65, QColor('#192d49'))
            gradient.setColorAt(1, QColor('#342b49'))
            p.fillRect(rect, gradient)
        for cue in project.cues:
            opacity = visibility(cue, t, s)
            if opacity:
                self.draw_cue(p, project, cue, t, opacity)

    @staticmethod
    def draw_fit(p, rect, img):
        if img.isNull():
            return
        size = img.size().scaled(rect.size().toSize(), Qt.AspectRatioMode.KeepAspectRatio)
        target = QRectF((rect.width() - size.width()) / 2, (rect.height() - size.height()) / 2,
                        size.width(), size.height())
        p.drawImage(target, img)

    def cue_geometry(self, project, cue):
        s = project.style
        tracks = [s.primary]
        if s.layout == 'two':
            tracks.append('translation' if s.primary == 'original' else 'original')
        result = []
        for i, track in enumerate(tracks):
            spans = cue.spans(track)
            g = geometry(getattr(cue, track), s.font, s.size if i == 0 else s.secondary_size,
                         tuple((span.begin, span.end) for span in spans))
            result.append((track, spans, g))
        positions = line_positions(s, [a[2][0] for a in result], [a[2][1] for a in result],
                                   [a[2][2] for a in result])
        return result, positions

    def overflow(self, project, cue):
        result, positions = self.cue_geometry(project, cue)
        return any(g[0] > project.style.width - 2 * project.style.margin
                   for _, _, g in result)

    def draw_cue(self, p, project, cue, t, opacity):
        s = project.style
        result, positions = self.cue_geometry(project, cue)
        elapsed = t - cue.start
        paint_end = cue.duration if cue.paint_end is None else cue.paint_end
        progress = (animation_progress(cue, elapsed) if cue.keyframe_scope in ('all', 'paint') else
                    clamp((elapsed - cue.paint_start) / max(0.001, paint_end - cue.paint_start)))
        emphasis_time = animation_clock(cue, elapsed) if cue.keyframe_scope in ('all', 'emphasis') else elapsed
        repaint = s.mode == 'repaint' or (s.mode == 'advanced' and s.repaint)
        for (_, spans, g), (x, y) in zip(result, positions):
            width, ascent, descent, runs = g
            p.save()
            p.translate(x, y)
            p.setOpacity(opacity)
            for run_x, run_width, span_index, path in runs:
                span = spans[span_index] if span_index >= 0 else None
                active = bool(s.mode == 'advanced' and span and span.enabled and span.start <= emphasis_time < span.finish)
                fill = QColor(s.fill)
                p.save()
                if active:
                    phase = clamp((emphasis_time - span.start) / max(0.001, span.finish - span.start))
                    envelope = math.sin(math.pi * phase) ** 0.7
                    lift = span.lift if span.lift is not None else s.lift
                    scale_to = span.scale if span.scale is not None else s.scale
                    scale = 1 + (scale_to - 1) * envelope
                    center = run_x + run_width / 2
                    p.translate(center, -lift * envelope)
                    p.scale(scale, scale)
                    p.translate(-center, 0)
                    fill = QColor(span.color or s.effect_color)
                pen = QPen(QColor(s.outline), s.outline_width,
                           Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                # Paint fills first; stroke last so repaint never covers its inner edge.
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(fill)
                p.drawPath(path)
                if repaint and not active:
                    if s.mode == 'advanced' and span and span.enabled:
                        # Repaint follows the configured clock independently of emphasis.
                        paint_time = animation_clock(cue, elapsed) if cue.keyframe_scope in ('all', 'paint') else elapsed
                        local = clamp((paint_time - span.start) / max(0.001, span.finish - span.start))
                        boundary = run_x + local * run_width
                    else:
                        boundary = width * progress
                    # Clip the entire fill path, not the outline; completed runs include overhang.
                    clip_right = boundary if boundary < run_x + run_width else run_x + run_width + 20
                    p.save()
                    p.setClipRect(QRectF(run_x - 20, -ascent - 30,
                                        max(0, clip_right - run_x + 20), ascent + descent + 60))
                    if boundary <= run_x:
                        p.setClipRect(QRectF(0, 0, 0, 0))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(s.painted))
                    p.drawPath(path)
                    p.restore()
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(path)
                p.restore()
            p.restore()

    def frame(self, project, t, video=None):
        image = QImage(project.style.width, project.style.height, QImage.Format.Format_RGBA8888)
        image.fill(QColor('black'))
        p = QPainter(image)
        self.draw(p, project, t, video)
        p.end()
        return image
