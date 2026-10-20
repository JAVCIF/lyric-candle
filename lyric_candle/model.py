"""Project model, validation, timing proposals and atomic persistence. No GUI dependency."""
from __future__ import annotations

import json
import math
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from .i18n import tr

VERSION = '0.2.6-alpha'
FORMAT = 'lyric-candle'
SCHEMA = 2


def time_text(value: float) -> str:
    ms = max(0, round(value * 1000))
    minutes, rest = divmod(ms, 60000)
    seconds, milli = divmod(rest, 1000)
    return f'{minutes:02}:{seconds:02}.{milli:03}'


def parse_time(value: str) -> float:
    parts = value.strip().replace(',', '.').split(':')
    if len(parts) > 3:
        raise ValueError(tr('Tiempo inválido; usa segundos o mm:ss.mmm.'))
    result = 0.0
    for part in parts:
        result = result * 60 + float(part)
    if not math.isfinite(result) or result < 0:
        raise ValueError(tr('El tiempo debe ser finito y mayor o igual que cero.'))
    return result


@dataclass
class Span:
    begin: int = 0
    end: int = 1
    start: float = 0.0  # Relative to cue.start, in seconds.
    finish: float = 0.4
    enabled: bool = True
    color: str = ''  # Empty means global default.
    lift: float | None = None
    scale: float | None = None


@dataclass
class Keyframe:
    time: float = 0.0  # Relative seconds within the cue.
    progress: float = 0.0  # Fraction, 0..1; equal values create a hold.


@dataclass
class Cue:
    uid: str = field(default_factory=lambda: uuid.uuid4().hex)
    start: float = 0.0
    end: float = 3.0
    original: str = ''
    translation: str = ''
    paint_start: float = 0.0  # Relative to start.
    paint_end: float | None = None
    original_spans: list[Span] = field(default_factory=list)
    translation_spans: list[Span] = field(default_factory=list)
    keyframes: list[Keyframe] = field(default_factory=list)
    use_keyframes: bool = True
    keyframe_scope: str = 'all'  # all / paint / emphasis; fades keep real time.
    # False while start/end are only a placeholder (imported lyrics, a new phrase). Marking or
    # editing either boundary confirms them. Provisional phrases never drive linked navigation.
    timed: bool = True

    @property
    def duration(self):
        return self.end - self.start

    def spans(self, track):
        return self.original_spans if track == 'original' else self.translation_spans


@dataclass
class Style:
    width: int = 1280
    height: int = 720
    fps: float = 30  # Presets 24/25/30/60, or the base video's rate (e.g. 23.976).
    layout: str = 'two'  # one / two
    position: str = 'left_split'
    primary: str = 'original'
    font: str = 'Segoe UI'
    size: int = 46
    secondary_size: int = 34
    margin: int = 48
    gap: int = 20
    fill: str = '#f1f4ff'
    painted: str = '#63b8ff'
    outline: str = '#17243f'
    outline_width: float = 2.5
    mode: str = 'advanced'  # repaint / fade / advanced
    repaint: bool = True
    fade: bool = True
    crossfade: bool = True
    fade_in: float = 0.16
    fade_out: float = 0.28
    effect_color: str = '#ffe49c'
    lift: float = 15.0
    scale: float = 1.22
    background: str = 'gradient'  # gradient / image / video
    background_color: str = '#101928'
    match_media: bool = False  # Canvas follows the base video's resolution and FPS.
    export_format: str = 'mp4'  # mp4 (H.264/AAC) / source (container and codecs of the base video)


@dataclass
class Project:
    title: str = 'Mi video lyrics'
    duration: float = 12.0
    media: str = ''
    image: str = ''
    style: Style = field(default_factory=Style)
    cues: list[Cue] = field(default_factory=list)
    playhead: float = 0.0  # Saved view position; does not affect export duration.
    text_drafts: dict[str, dict[str, str]] = field(default_factory=dict)

    def problems(self):
        """Readable issues in the interface language."""
        return [text for _code, text in self.problem_items()]

    def problem_items(self):
        """(code, text) pairs. Code compares by kind, never by translated text:
        duration, cue_range, after_end, paint, keyframes, spans, span_time, span_scale."""
        issues = []

        def add(code, text):
            issues.append((code, text))
        track_names = {'original': tr('original'), 'translation': tr('traducción')}
        if not math.isfinite(self.duration) or self.duration <= 0:
            add('duration', tr('La duración del proyecto debe ser positiva.'))
        for i, cue in enumerate(self.cues, 1):
            if not all(math.isfinite(v) for v in (cue.start, cue.end)) or cue.start < 0 or cue.end <= cue.start:
                add('cue_range', tr('Frase {0}: el final debe ser mayor que el inicio.').format(i))
                continue
            if cue.end > self.duration + 0.001:
                add('after_end', tr('Frase {0}: termina después del proyecto.').format(i))
            paint_end = cue.duration if cue.paint_end is None else cue.paint_end
            if not (0 <= cue.paint_start < paint_end <= cue.duration + 0.001):
                add('paint', tr('Frase {0}: revisa el intervalo de repintado.').format(i))
            if cue.keyframe_scope not in ('all', 'paint', 'emphasis'):
                add('keyframes', tr('Frase {0}: destino de keyframes inválido.').format(i))
            previous_time, previous_progress = cue.paint_start, 0.0
            for point in cue.keyframes:
                if (not math.isfinite(point.time) or not math.isfinite(point.progress)
                        or not previous_time < point.time < paint_end
                        or not previous_progress <= point.progress <= 1):
                    add('keyframes', tr('Frase {0}: keyframes fuera del intervalo, repetidos o con avance decreciente.').format(i))
                    break
                previous_time, previous_progress = point.time, point.progress
            for track in ('original', 'translation'):
                text = getattr(cue, track)
                prev = 0
                for span in sorted(cue.spans(track), key=lambda s: s.begin):
                    if not (prev <= span.begin < span.end <= len(text)):
                        add('spans', tr('Frase {0}: marcas superpuestas o fuera del texto ({1}).').format(i, track_names[track]))
                    if not (0 <= span.start < span.finish <= cue.duration + 0.001):
                        add('span_time', tr('Frase {0}: tiempo de sílaba fuera de la frase ({1}).').format(i, track_names[track]))
                    if span.scale is not None and not (0.5 <= span.scale <= 3):
                        add('span_scale', tr('Frase {0}: escala de sílaba inválida.').format(i))
                    prev = span.end
        return issues

def clamp_cue(cue: Cue):
    cue.end = max(cue.start + 0.05, cue.end)
    cue.paint_start = min(max(0, cue.paint_start), cue.duration - 0.01)
    if cue.paint_end is not None:
        cue.paint_end = min(cue.duration, max(cue.paint_start + 0.01, cue.paint_end))
    for track in ('original', 'translation'):
        for s in cue.spans(track):
            s.start = min(max(0, s.start), cue.duration - 0.01)
            s.finish = min(cue.duration, max(s.start + 0.01, s.finish))


def retime_cue(cue: Cue, previous_duration: float):
    """Keep relative vocal anchors proportional when changing the phrase interval."""
    ratio = cue.duration / max(0.001, previous_duration)
    cue.paint_start *= ratio
    if cue.paint_end is not None:
        cue.paint_end *= ratio
    for point in cue.keyframes:
        point.time *= ratio
    for track in ('original', 'translation'):
        for span in cue.spans(track):
            span.start *= ratio
            span.finish *= ratio
    clamp_cue(cue)


def keyframe_points(cue: Cue):
    end = cue.duration if cue.paint_end is None else cue.paint_end
    return [(cue.paint_start, 0.0), *[(p.time, p.progress) for p in cue.keyframes], (end, 1.0)]


def animation_progress(cue: Cue, elapsed: float):
    end = cue.duration if cue.paint_end is None else cue.paint_end
    if not cue.use_keyframes or not cue.keyframes:
        return min(1.0, max(0.0, (elapsed-cue.paint_start)/max(.001, end-cue.paint_start)))
    points = keyframe_points(cue)
    if elapsed <= points[0][0]:
        return 0.0
    for (a, pa), (b, pb) in zip(points, points[1:]):
        if elapsed <= b:
            fraction = min(1.0, max(0.0, (elapsed-a)/max(1e-9, b-a)))
            return pa + (pb-pa)*fraction
    return 1.0


def animation_clock(cue: Cue, elapsed: float):
    """Virtual time drives emphasis; appearance/fade remain on the actual timeline."""
    end = cue.duration if cue.paint_end is None else cue.paint_end
    if not cue.use_keyframes or not cue.keyframes or elapsed < cue.paint_start or elapsed > end:
        return elapsed
    return cue.paint_start + animation_progress(cue, elapsed)*(end-cue.paint_start)


def animation_to_elapsed(cue: Cue, clock: float):
    """Earliest real instant at which a virtual anchor is reached, including holds."""
    end = cue.duration if cue.paint_end is None else cue.paint_end
    if not cue.use_keyframes or not cue.keyframes or not cue.paint_start <= clock <= end:
        return clock
    target = (clock-cue.paint_start)/max(.001, end-cue.paint_start)
    points = keyframe_points(cue)
    if target <= 0:
        return points[0][0]
    for (a, pa), (b, pb) in zip(points, points[1:]):
        if target <= pb:
            return a if pb == pa else a+(b-a)*(target-pa)/(pb-pa)
    return end


def retime_keyframes(cue: Cue, old_start: float, old_end: float):
    """Preserve the curve's proportions when moving the repaint window."""
    new_end = cue.duration if cue.paint_end is None else cue.paint_end
    for point in cue.keyframes:
        point.time = cue.paint_start+(point.time-old_start)*(new_end-cue.paint_start)/max(.001, old_end-old_start)


def add_span(cue: Cue, track: str, begin: int, end: int) -> Span:
    if not 0 <= begin < end <= len(getattr(cue, track)):
        raise ValueError(tr('Selecciona uno o más caracteres completos.'))
    if any(begin < s.end and end > s.begin for s in cue.spans(track)):
        raise ValueError(tr('La selección se cruza con una marca existente. Elimínala primero.'))
    span = Span(begin, end)
    span.start, span.finish = estimate_span(cue, track, begin, end)
    cue.spans(track).append(span)
    cue.spans(track).sort(key=lambda s: s.begin)
    return span


def split_spans(cue: Cue, track: str, marked: str):
    """Pipes mark boundaries; plain text must remain byte-for-byte equivalent."""
    if marked.replace('|', '') != getattr(cue, track):
        raise ValueError(tr('Al quitar |, el texto debe ser idéntico al de la frase. Conserva los espacios.'))
    result = []
    pos = 0
    for part in marked.split('|'):
        if part.strip():
            result.append(Span(pos, pos + len(part)))
        pos += len(part)
    cue.spans(track)[:] = result
    propose_spans(cue, track)


def estimate_span(cue: Cue, track: str, begin: int, end: int):
    """Text-position weighted estimate inside the repaint interval, so a new mark is
    emphasized when the repaint sweep reaches it. Does not analyze or align vocals."""
    text = getattr(cue, track)
    weights = [1.0 if c.isalnum() else 0.2 for c in text]
    total = sum(weights) or 1
    low = cue.paint_start
    high = cue.duration if cue.paint_end is None else cue.paint_end
    start = low + (high - low) * sum(weights[:begin]) / total
    finish = max(start + 0.005, low + (high - low) * sum(weights[:end]) / total)
    return start, min(finish, cue.duration)


def propose_spans(cue: Cue, track: str):
    """Text-position weighted estimate. Does not analyze or claim to align vocals."""
    for span in cue.spans(track):
        span.start, span.finish = estimate_span(cue, track, span.begin, span.end)


def snap_spans_to_audio(cue: Cue, track: str, peaks, audio_duration, radius=0.18):
    """Nudge existing anchors toward nearby amplitude attacks, never infer lyrics.

    Span times live on the animation clock. When keyframes drive emphasis, convert them
    to real time before comparing with the audio, and back afterwards."""
    if not peaks or audio_duration <= 0 or max(peaks) <= 0:
        return 0
    curve = cue.use_keyframes and cue.keyframes and cue.keyframe_scope in ('all', 'emphasis')
    to_real = (lambda v: animation_to_elapsed(cue, v)) if curve else (lambda v: v)
    to_clock = (lambda r: animation_clock(cue, r)) if curve else (lambda r: r)
    dt = audio_duration / len(peaks)
    changed = 0
    previous = -1.0  # Real time of the previous snapped anchor.
    for span in sorted(cue.spans(track), key=lambda s: s.begin):
        if not span.enabled:
            continue
        real_start = to_real(span.start)
        absolute = cue.start + real_start
        left = max(1, int((absolute - radius) / dt))
        right = min(len(peaks) - 1, int((absolute + radius) / dt))
        candidates = []
        for i in range(left, right + 1):
            rel = i * dt - cue.start
            if not max(0, previous + .005) <= rel < cue.duration - .01:
                continue
            attack = peaks[i] - sum(peaks[max(0, i-3):i]) / min(i, 3)
            if attack > 0:
                proximity = 1 - .6 * abs(i * dt - absolute) / radius
                candidates.append((attack * proximity, rel))
        if candidates:
            target_real = max(candidates)[1]
            target = to_clock(target_real)
            length = span.finish - span.start
            if abs(span.start - target) > .001:
                changed += 1
            span.start = min(target, cue.duration - .01)
            span.finish = min(cue.duration, span.start + length)
            real_start = target_real
        previous = real_start
    return changed


def to_dict(project: Project, base: Path | None = None):
    data = asdict(project)
    data.update(format=FORMAT, schema=SCHEMA, app_version=VERSION)
    if base:
        for name in ('media', 'image'):
            value = data[name]
            if value:
                # The absolute path lets a project file moved on its own find its media.
                data[name + '_absolute'] = str(Path(value).resolve())
                try:
                    data[name] = os.path.relpath(value, base)
                except ValueError:  # Different Windows drive.
                    pass
    return data


def locate_asset(stored: str, absolute: str, base: Path) -> str:
    """Relative to the project (both moved together), then the absolute path at save time
    (only the project moved), then a file with the same name next to the project."""
    candidates = [base / stored]
    if absolute:
        candidates.append(Path(absolute))
    candidates.append(base / Path(stored.replace('\\', '/')).name)
    for candidate in candidates:
        try:
            if candidate.is_file():
                return str(candidate.resolve())
        except OSError:
            continue
    return str(candidates[0].resolve())


class ProjectIssues(ValueError):
    """The file is a valid project, but its timings or marks need review."""
    def __init__(self, issues):
        super().__init__('\n'.join(issues[:12]))
        self.issues = issues


POSITIONS = {'one': ('left_top', 'left_bottom', 'right_top', 'right_bottom', 'center'),
             'two': ('left_split', 'right_split', 'center')}


def _filtered(cls, data):
    allowed = {f.name for f in fields(cls)}
    return {k: v for k, v in data.items() if k in allowed}


def from_dict(data, base: Path | None = None, strict=True):
    """strict=False opens projects whose timings need review; structure is always checked."""
    if data.get('format') != FORMAT or data.get('schema') not in (1, 2):
        raise ValueError(tr('Este archivo no es un proyecto Lyric Candle compatible (schema 1 o 2).'))
    params = _filtered(Project, data)
    params['style'] = Style(**_filtered(Style, data.get('style', {})))
    params['cues'] = []
    for item in data.get('cues', []):
        cp = _filtered(Cue, item)
        for key in ('original_spans', 'translation_spans'):
            cp[key] = [Span(**_filtered(Span, s)) for s in item.get(key, [])]
        cp['keyframes'] = [Keyframe(**_filtered(Keyframe, p)) for p in item.get('keyframes', [])]
        cp['timed'] = bool(cp.get('timed', True))
        params['cues'].append(Cue(**cp))
    for key in ('media', 'image'):
        if params.get(key) and base:
            params[key] = locate_asset(params[key], str(data.get(key + '_absolute') or ''), base)
    project = Project(**params)
    if not isinstance(project.text_drafts, dict) or any(
            not isinstance(uid, str) or not isinstance(tracks, dict) or any(
                track not in ('original', 'translation') or not isinstance(text, str)
                for track, text in tracks.items())
            for uid, tracks in project.text_drafts.items()):
        raise ValueError(tr('Borradores de texto inválidos.'))
    cue_ids = {cue.uid for cue in project.cues}
    project.text_drafts = {uid: tracks for uid, tracks in project.text_drafts.items() if uid in cue_ids}
    if not isinstance(project.playhead, (int, float)) or not math.isfinite(project.playhead) or project.playhead < 0:
        raise ValueError(tr('Posición guardada inválida.'))
    project.playhead = min(project.playhead, project.duration)
    s = project.style
    if s.width < 320 or s.height < 240 or s.width > 3840 or s.height > 2160 or s.width % 2 or s.height % 2:
        raise ValueError(tr('Resolución inválida.'))
    if (isinstance(s.fps, bool) or not isinstance(s.fps, (int, float)) or not math.isfinite(s.fps)
            or not 1 <= s.fps <= 120 or s.layout not in ('one', 'two') or s.mode not in ('repaint', 'fade', 'advanced')):
        raise ValueError(tr('Configuración de proyecto inválida.'))
    if s.export_format not in ('mp4', 'source'):
        s.export_format = 'mp4'
    s.match_media = bool(s.match_media)
    if not (8 <= s.size <= 180 and 8 <= s.secondary_size <= 180):
        raise ValueError(tr('Tamaño de fuente inválido.'))
    # Hand-edited or older files: map values the editor cannot show to the nearest valid ones.
    if s.primary not in ('original', 'translation'):
        s.primary = 'original'
    if s.position not in POSITIONS[s.layout]:
        side = next((x for x in ('left', 'right') if str(s.position).startswith(x)), '')
        s.position = (side + ('_top' if s.layout == 'one' else '_split')) if side else 'center'
    # A saved draft may contain phrases beyond a shortened project duration.
    # Preserve that work and let the editor flag it; export still validates all issues.
    issues = [text for code, text in project.problem_items() if code != 'after_end']
    if issues and strict:
        raise ProjectIssues(issues)
    return project


def load(path, strict=True):
    path = Path(path)
    return from_dict(json.loads(path.read_text(encoding='utf-8')), path.parent, strict)


def save(project, path, relative=True):
    """Write through a sibling temporary file; an interrupted write keeps the old save."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = to_dict(project, path.parent if relative else None)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
