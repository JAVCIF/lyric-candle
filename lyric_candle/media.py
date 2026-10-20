"""External media jobs; never block the GUI or overwrite a finished export on failure."""
from __future__ import annotations

import array
import copy
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from .i18n import tr
from .render import Renderer

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))


def tool_dirs():
    """tools/ next to the EXE (what LEEME describes) and inside the bundle or source tree."""
    dirs = []
    if getattr(sys, 'frozen', False):
        dirs.append(Path(sys.executable).resolve().parent / 'tools')
    dirs.append(ROOT / 'tools')
    return dirs


def executable(name):
    suffix = '.exe' if os.name == 'nt' else ''
    for folder in tool_dirs():
        local = folder / (name + suffix)
        if local.is_file():
            return str(local)
    return shutil.which(name)


def options():
    return {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}


def probe(path):
    tool = executable('ffprobe')
    if not tool:
        return None
    result = subprocess.run([tool, '-v', 'error', '-show_format', '-show_streams', '-of', 'json', path],
                            capture_output=True, timeout=30, check=False, **options())  # returncode checked below
    if result.returncode:
        raise ValueError(result.stderr.decode('utf-8', 'replace')[-1500:])
    return json.loads(result.stdout)


def stream_info(path):
    """Main video/audio streams and container of a media file, or None without ffprobe."""
    data = probe(path)
    if data is None:
        return None
    streams = data.get('streams', [])
    video = next((st for st in streams if st.get('codec_type') == 'video'
                  and not st.get('disposition', {}).get('attached_pic')), None)
    audio = next((st for st in streams if st.get('codec_type') == 'audio'), None)
    return {'video': video, 'audio': audio, 'format': data.get('format', {}), 'ext': Path(path).suffix.lower()}


def _ratio(text):
    try:
        value = Fraction(str(text).replace(':', '/'))
    except (ValueError, ZeroDivisionError):
        return None
    return value if value > 0 else None


def frame_rate(video):
    """Average rate (constant-rate files) or the stream's base rate, within 1..120 fps."""
    for key in ('avg_frame_rate', 'r_frame_rate'):
        rate = _ratio(video.get(key, ''))
        if rate and 1 <= rate <= 120:
            return round(float(rate), 6)
    return None


def fps_fraction(fps):
    """Exact NTSC-style rates for FFmpeg: 23.976024 -> 24000/1001."""
    return Fraction(fps).limit_denominator(1001)


def display_size(video):
    """Display dimensions: apply pixel aspect ratio before the stream's rotation."""
    width, height = int(video.get('width') or 0), int(video.get('height') or 0)
    if width <= 0 or height <= 0:
        return None
    sar = _ratio(video.get('sample_aspect_ratio', ''))
    if sar and sar != 1:
        width = width * sar
    rotation = next((item['rotation'] for item in video.get('side_data_list', []) if 'rotation' in item),
                    video.get('tags', {}).get('rotate', 0))
    try:
        quarter_turn = math.isclose(float(rotation) % 180, 90, abs_tol=.1)
    except (ValueError, TypeError):
        quarter_turn = False
    return (height, width) if quarter_turn else (width, height)


def canvas_size(video):
    """Display size (square pixels and orientation), fitted to the editor limits."""
    size = display_size(video)
    if size is None:
        return None
    width, height = size
    scale = min(1.0, 3840 / width, 2160 / height)
    scale = max(scale, 320 / width, 240 / height)

    def even(value, low, high):
        return min(high, max(low, int(round(float(value) * scale / 2)) * 2))
    return even(width, 320, 3840), even(height, 240, 2160)


# FFmpeg autorotates before these filters. Normalize SAR before fitting or exporting
# to PNG: QPainter works in square image pixels and ignores a PNG's physical pixel size.
# Use syntax supported by FFmpeg 6 as well as newer builds.
SQUARE_PIXELS = ("scale=w='max(2,round(iw*max(1,sar)/2)*2)':"
                 "h='max(2,round(ih/if(gt(sar,0),min(1,sar),1)/2)*2)',setsar=1")


@lru_cache(maxsize=4)
def available_encoders(tool):
    result = subprocess.run([tool, '-hide_banner', '-encoders'], capture_output=True, timeout=30,
                            check=False, **options())  # An empty listing simply offers fewer encoders.
    names, listing = set(), False
    for line in result.stdout.decode('utf-8', 'replace').splitlines():
        if line.strip().startswith('------'):
            listing = True
        elif listing and len(line.split()) >= 2:
            names.add(line.split()[1])
    return frozenset(names)


VIDEO_ENCODERS = {
    'h264': ('libx264',), 'hevc': ('libx265',), 'mpeg4': ('mpeg4', 'libxvid'), 'msmpeg4v3': ('msmpeg4',),
    'msmpeg4v2': ('msmpeg4v2',), 'mpeg2video': ('mpeg2video',), 'mpeg1video': ('mpeg1video',),
    'vp9': ('libvpx-vp9',), 'vp8': ('libvpx',), 'av1': ('libsvtav1', 'libaom-av1'), 'mjpeg': ('mjpeg',),
    'prores': ('prores_ks',), 'wmv2': ('wmv2',), 'wmv1': ('wmv1',), 'flv1': ('flv',), 'theora': ('libtheora',),
    'ffv1': ('ffv1',), 'huffyuv': ('huffyuv',), 'utvideo': ('utvideo',), 'qtrle': ('qtrle',), 'png': ('png',)}
CONTAINER_FALLBACK = {'.webm': ('libvpx-vp9', 'libvpx'), '.avi': ('mpeg4',), '.wmv': ('wmv2',),
                      '.flv': ('flv',), '.mpg': ('mpeg2video',), '.mpeg': ('mpeg2video',), '.ogv': ('libtheora',)}
SOURCE_CONTAINERS = ('.mp4', '.m4v', '.mov', '.mkv', '.avi', '.webm', '.wmv', '.flv', '.mpg', '.mpeg', '.ogv')
SAFE_PIXEL_FORMATS = ('yuv420p', 'yuvj420p', 'yuv422p', 'yuv444p', 'yuv420p10le', 'yuv422p10le', 'yuv444p10le')
CONTAINER_NAMES = {'.mp4': 'MP4', '.m4v': 'MP4', '.mov': 'MOV', '.mkv': 'MKV', '.avi': 'AVI', '.webm': 'WebM',
                   '.wmv': 'WMV', '.flv': 'FLV', '.mpg': 'MPEG', '.mpeg': 'MPEG', '.ogv': 'OGV'}


def describe_source(info):
    """One line for the editor: container, size, rate and codecs of the base video."""
    video, audio = info.get('video'), info.get('audio')
    if not video:
        return tr('El medio no tiene pista de video.')
    parts = [CONTAINER_NAMES.get(info['ext'], info['ext'].lstrip('.').upper() or '?'),
             f"{video.get('width')}×{video.get('height')}"]
    rate = frame_rate(video)
    if rate:
        parts.append(f'{rate:.3f}'.rstrip('0').rstrip('.') + ' fps')
    tag = video.get('codec_tag_string', '')
    codec = video.get('codec_name', '?') + (f' ({tag})' if re.fullmatch(r'[0-9A-Za-z]{4}', tag or '') else '')
    parts.append(codec)
    parts.append(audio.get('codec_name', '?') if audio else tr('sin audio'))
    return ' · '.join(parts)


def source_settings(info, encoders):
    """Container and encoder options that reproduce the base video's format.

    Video is re-encoded (the lyrics are drawn on it) with the same codec, pixel format and
    bitrate when this FFmpeg can; audio is copied untouched. Returns ext, args, summary, note."""
    video, audio, fmt = info['video'], info.get('audio'), info.get('format', {})
    ext = info['ext'] if info['ext'] in SOURCE_CONTAINERS else '.mkv'
    note = '' if ext == info['ext'] else tr('El contenedor {0} no se puede escribir; se usa MKV.').format(info["ext"] or "?")
    codec = video.get('codec_name', '')
    wanted = VIDEO_ENCODERS.get(codec, ())
    encoder = next((name for name in wanted if name in encoders), None)
    if encoder is None:
        encoder = next((name for name in CONTAINER_FALLBACK.get(ext, ('libx264', 'mpeg4')) if name in encoders), None)
        if encoder is None:
            raise ValueError(tr('Esta compilación de FFmpeg no tiene un codificador compatible con ') + ext)
        note = (note + ' ' if note else '') + tr('FFmpeg no puede codificar {0}; se usa {1}.').format(codec or tr('ese códec'), encoder)
    args = ['-c:v', encoder]
    bitrate = int(video.get('bit_rate') or 0)
    if not bitrate and fmt.get('bit_rate'):
        bitrate = int(fmt['bit_rate']) - int((audio or {}).get('bit_rate') or 0)
    if bitrate > 50_000:
        args += ['-b:v', str(bitrate)]
    elif encoder in ('libx264', 'libx265'):
        args += ['-crf', '19' if encoder == 'libx264' else '23', '-preset', 'veryfast']
    elif encoder in ('libvpx-vp9', 'libvpx'):
        args += ['-crf', '32', '-b:v', '0']
    elif encoder in ('mpeg4', 'msmpeg4', 'msmpeg4v2', 'mpeg2video', 'mpeg1video', 'mjpeg'):
        args += ['-q:v', '3']
    pixel_format = video.get('pix_fmt', '')
    args += ['-pix_fmt', pixel_format if pixel_format in SAFE_PIXEL_FORMATS else 'yuv420p']
    tag = video.get('codec_tag_string', '')
    if ext == '.avi' and encoder in wanted and re.fullmatch(r'[0-9A-Za-z]{4}', tag or ''):
        args += ['-vtag', tag]  # Keep XVID/DIVX/etc. so players treat it like the original.
    audio_args = ['-c:a', 'copy'] if audio else []
    summary = f'{CONTAINER_NAMES.get(ext, ext)} · {encoder}' + (tr(' · audio {0} (copiado)').format(audio.get("codec_name")) if audio else '')
    return {'ext': ext, 'video_args': args, 'audio_args': audio_args, 'summary': summary, 'note': note}


class WaveWorker(QThread):
    ready = Signal(object, float)
    failed = Signal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        self.process = None

    def cancel(self):
        self.requestInterruption()
        if self.process and self.process.poll() is None:
            self.process.kill()

    def run(self):
        try:
            if self.isInterruptionRequested():
                return
            tool = executable('ffmpeg')
            if not tool:
                raise RuntimeError(tr('Forma de onda: instala FFmpeg o coloca ffmpeg.exe en tools/.'))
            self.process = subprocess.Popen([tool, '-v', 'error', '-i', self.path, '-vn', '-ac', '1',
                                             '-ar', '1000', '-f', 'f32le', 'pipe:1'],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **options())
            if self.isInterruptionRequested():
                self.process.kill()
            output, errors = self.process.communicate(timeout=180)
            if self.isInterruptionRequested():
                return
            if self.process.returncode:
                raise RuntimeError(tr('No se pudo leer el audio: ') + errors.decode('utf-8', 'replace')[-300:])
            values = array.array('f')
            values.frombytes(output)
            if os.sys.byteorder != 'little':
                values.byteswap()
            step = max(1, math.ceil(len(values) / 12000))
            peaks = [max((abs(v) for v in values[i:i+step]), default=0) for i in range(0, len(values), step)]
            self.ready.emit(peaks, len(values) / 1000)
        except Exception as exc:  # noqa: BLE001 - thread boundary: report any failure to the UI.
            if self.process and self.process.poll() is None:
                self.process.kill()
                self.process.communicate()
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))


class ExportWorker(QThread):
    progress = Signal(int)
    done = Signal(str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, project, destination, parent=None):
        super().__init__(parent)
        self.project = copy.deepcopy(project)
        self.destination = Path(destination)
        self.processes = []
        self.summary = 'MP4 · H.264 · AAC'
        self.note = ''

    def cancel(self):
        self.requestInterruption()
        # Unblocks both pipe writes and decoder reads if the user cancels.
        for proc in tuple(self.processes):
            if proc.poll() is None:
                try:
                    proc.kill()
                except OSError:
                    pass

    @staticmethod
    def read_exact(stream, count):
        pieces, size = [], 0
        while size < count:
            part = stream.read(count - size)
            if not part:
                break
            pieces.append(part)
            size += len(part)
        return b''.join(pieces)

    def run(self):
        temp = None
        errorlog = tempfile.TemporaryFile()
        decoderlog = tempfile.TemporaryFile()
        encoder = decoder = None
        try:
            project = self.project
            s = project.style
            if project.text_drafts:
                raise ValueError(tr('Aplica los borradores de texto antes de exportar.'))
            problems = project.problems()
            if problems:
                raise ValueError('\n'.join(problems[:12]))
            ffmpeg = executable('ffmpeg')
            if not ffmpeg:
                raise ValueError(tr('No se encontró FFmpeg. Coloca ffmpeg.exe y ffprobe.exe en tools/ o instálalos en PATH.'))
            if project.media and not Path(project.media).is_file():
                raise ValueError(tr('El medio no existe. Vuelve a vincularlo con «Audio / video».'))
            if s.background == 'image' and (not project.image or QImage(project.image).isNull()):
                raise ValueError(tr('La imagen de fondo no se encuentra o no es compatible.'))
            if project.media and self.destination.resolve() == Path(project.media).resolve():
                raise ValueError(tr('El destino no puede ser el medio original.'))
            if project.image and self.destination.resolve() == Path(project.image).resolve():
                raise ValueError(tr('El destino no puede ser la imagen original.'))
            if s.background == 'video':
                if not project.media:
                    raise ValueError(tr('Carga un video para utilizarlo como fondo.'))
                metadata = probe(project.media)
                if metadata is None:
                    raise ValueError(tr('El fondo de video necesita ffprobe además de ffmpeg.'))
                if not any(st.get('codec_type') == 'video' for st in metadata.get('streams', [])):
                    raise ValueError(tr('El medio cargado no tiene pista de video. Elige otro fondo.'))
                vf = (f'fps={fps_fraction(s.fps)},{SQUARE_PIXELS},'
                      f'scale={s.width}:{s.height}:force_original_aspect_ratio=decrease,'
                      f'pad={s.width}:{s.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=rgba')
                decoder = subprocess.Popen([ffmpeg, '-v', 'error', '-i', project.media, '-an', '-vf', vf,
                                            '-f', 'rawvideo', '-pix_fmt', 'rgba', 'pipe:1'],
                                           stdout=subprocess.PIPE, stderr=decoderlog, **options())
                self.processes.append(decoder)
            settings = None
            if s.export_format == 'source' and project.media:
                info = stream_info(project.media)
                if info is None:
                    raise ValueError(tr('Exportar como el video base necesita ffprobe además de ffmpeg.'))
                if info['video'] is None:
                    self.note = tr('El medio no tiene video; se exportó en MP4.')
                else:
                    settings = source_settings(info, available_encoders(ffmpeg))
                    self.summary, self.note = settings['summary'], settings['note']
            fd, tmp_name = tempfile.mkstemp(prefix='lyric-candle-', suffix=self.destination.suffix or '.mp4',
                                            dir=self.destination.parent)
            os.close(fd)
            temp = Path(tmp_name)
            cmd = [ffmpeg, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba',
                   '-video_size', f'{s.width}x{s.height}', '-framerate', str(fps_fraction(s.fps)), '-i', 'pipe:0']
            if project.media:
                cmd += ['-i', project.media, '-map', '0:v:0', '-map', '1:a:0?']
            cmd += ['-vf', 'setsar=1']  # The composed RGBA canvas always has square pixels.
            if settings:
                cmd += settings['video_args'] + settings['audio_args']
            else:
                cmd += ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p']
                if project.media:
                    cmd += ['-c:a', 'aac', '-b:a', '192k', '-af', 'apad']
            cmd += ['-t', str(project.duration)]
            if temp.suffix.lower() in ('.mp4', '.m4v', '.mov'):
                cmd += ['-movflags', '+faststart']
            cmd += [str(temp)]
            encoder = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                       stderr=errorlog, **options())
            self.processes.append(encoder)
            renderer = Renderer()
            frame_count = math.ceil(project.duration * s.fps)
            video = None
            last_percent = -1
            for frame_index in range(frame_count):
                if self.isInterruptionRequested():
                    raise InterruptedError()
                if decoder:
                    data = self.read_exact(decoder.stdout, s.width * s.height * 4)
                    if len(data) == s.width * s.height * 4:
                        video = QImage(data, s.width, s.height, s.width * 4, QImage.Format.Format_RGBA8888).copy()
                    elif video is None:
                        raise ValueError(tr('No se pudo decodificar el primer fotograma del video.'))
                    elif data or (decoder.poll() is not None and decoder.returncode != 0):
                        raise ValueError(tr('El video terminó con un error de decodificación.'))
                image = renderer.frame(project, frame_index / s.fps, video)
                encoder.stdin.write(bytes(image.constBits()))
                percent = int((frame_index + 1) * 99 / frame_count)
                if percent != last_percent:
                    self.progress.emit(percent)
                    last_percent = percent
            encoder.stdin.close()
            encoder.wait(timeout=90)
            if encoder.returncode:
                errorlog.seek(0)
                raise RuntimeError(errorlog.read().decode('utf-8', 'replace')[-3000:])
            if self.isInterruptionRequested():
                raise InterruptedError()
            os.replace(temp, self.destination)
            self.progress.emit(100)
            self.done.emit(str(self.destination))
        except InterruptedError:
            self.cancelled.emit()
        except Exception as exc:  # noqa: BLE001 - thread boundary: report any failure to the UI.
            if self.isInterruptionRequested():
                self.cancelled.emit()
            else:
                errorlog.seek(0)
                details = errorlog.read().decode('utf-8', 'replace')[-2000:]
                self.failed.emit(str(exc) + ('\n' + details if details else ''))
        finally:
            for proc in self.processes:
                if proc.poll() is None:
                    proc.kill()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                for stream in (proc.stdin, proc.stdout):
                    if stream:
                        try:
                            stream.close()
                        except OSError:
                            pass
            if temp and temp.exists():
                temp.unlink(missing_ok=True)
            errorlog.close()
            decoderlog.close()


class StillFrameWorker(QThread):
    """Extract one paused video frame, independently of QMediaPlayer's playback state."""
    ready = Signal(object)
    failed = Signal(str)

    def __init__(self, path, position, parent=None):
        super().__init__(parent)
        self.path = path
        self.position = max(0, position)
        self.process = None

    def cancel(self):
        self.requestInterruption()
        if self.process and self.process.poll() is None:
            try:
                self.process.kill()
            except OSError:
                pass

    def decode(self, tool, seek_args):
        if self.isInterruptionRequested():
            return QImage()
        cmd = [tool, '-nostdin', '-v', 'error', *seek_args, '-i', self.path,
               '-map', '0:v:0', '-frames:v', '1', '-an', '-vf', SQUARE_PIXELS, '-threads', '1',
               '-f', 'image2pipe', '-vcodec', 'png', 'pipe:1']
        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **options())
        if self.isInterruptionRequested():
            self.process.kill()
        output, errors = self.process.communicate(timeout=30)
        if self.isInterruptionRequested():
            return QImage()
        if self.process.returncode:
            raise RuntimeError(errors.decode('utf-8', 'replace')[-1000:] or tr('No se pudo decodificar el fotograma.'))
        return QImage.fromData(output)

    def run(self):
        try:
            if self.isInterruptionRequested():
                return
            tool = executable('ffmpeg')
            if not tool:
                raise RuntimeError(tr('FFmpeg no está disponible para extraer el fotograma.'))
            image = self.decode(tool, ['-ss', f'{self.position:.6f}'])
            if image.isNull() and not self.isInterruptionRequested():
                # Seeking exactly to EOF has no frame; retain the final visible picture.
                image = self.decode(tool, ['-sseof', '-0.1'])
            if self.isInterruptionRequested():
                return
            if image.isNull():
                raise RuntimeError(tr('El medio no devolvió un fotograma de video.'))
            self.ready.emit(image)
        except Exception as exc:  # noqa: BLE001 - thread boundary: report any failure to the UI.
            if self.process and self.process.poll() is None:
                self.process.kill()
                self.process.communicate()
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
