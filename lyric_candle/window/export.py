"""Video export dialogs and the background export job."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog

from .. import media as media_tools
from ..i18n import tr
from ..media import CONTAINER_NAMES, SOURCE_CONTAINERS, ExportWorker


class ExportMixin:
    """Mixin for MainWindow: video export dialogs and the background export job."""

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
        if not media_tools.executable('ffmpeg'):
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
