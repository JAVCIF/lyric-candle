"""Media and project files: new/open/save, relinking, import, autosave and recovery."""
from __future__ import annotations

import logging
import time
from pathlib import Path

from PySide6.QtCore import QLockFile
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from ..dialogs import ImportDialog
from ..i18n import tr
from ..media import ROOT
from ..model import Project, ProjectIssues, load, save, time_text
from .common import image_filter, media_filter


class ProjectMixin:
    """Mixin for MainWindow: media and project files: new/open/save, relinking, import, autosave and recovery."""

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
        self.reset_marking()
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
        self.reset_marking()
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
            self.reset_marking()
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
                self.reset_marking()
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
