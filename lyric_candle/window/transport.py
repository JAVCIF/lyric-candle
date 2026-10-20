"""Playback clock, Qt Multimedia player, video frames, waveform loading."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer, QVideoSink
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLineEdit,
    QPlainTextEdit,
)

from .. import media as media_tools
from ..i18n import tr
from ..media import StillFrameWorker, WaveWorker
from ..model import time_text


class TransportMixin:
    """Mixin for MainWindow: playback clock, Qt Multimedia player, video frames, waveform loading."""

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
        self.update_mark_target()

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
            if not media_tools.executable('ffmpeg') and not self.is_playing():
                self.still_timer.start(0)
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self._pending_player_seek = None
            if self._warming_video:
                self.finish_video_prime()

    def video_available(self, available):
        if available and not self.is_playing() and not media_tools.executable('ffmpeg'):
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
        if not media_tools.executable('ffmpeg'):
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
