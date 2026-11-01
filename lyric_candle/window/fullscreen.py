"""Full-screen preview: the preview widget moves to a full-screen window and back."""
from __future__ import annotations

from PySide6.QtGui import QColor

from ..i18n import tr
from ..widgets import FullscreenView, Preview


class FullscreenMixin:
    """Mixin for MainWindow: full-screen preview with Space to play/pause and Esc to return."""

    fullscreen_view = None

    def is_fullscreen_preview(self):
        return self.fullscreen_view is not None

    def toggle_fullscreen_preview(self):
        if self.is_fullscreen_preview():
            self.exit_fullscreen_preview()
        else:
            self.enter_fullscreen_preview()

    def enter_fullscreen_preview(self):
        if self.is_fullscreen_preview():
            return
        if self.area_button.isChecked():
            self.area_button.setChecked(False)  # The draw tool belongs to the editor view.
        view = FullscreenView()
        self.fullscreen_view = view
        self.space_shortcut.setEnabled(False)
        self._preview_slot = self.preview_layout.indexOf(self.preview)
        view.box.addWidget(self.preview)  # Reparents: playback keeps drawing into the same widget.
        self.preview.guides = False
        self.preview.backdrop = QColor('#000000')
        view.togglePlay.connect(self.toggle_play)
        view.exitRequested.connect(self.exit_fullscreen_preview)
        screen = self.screen()
        if screen is not None:
            view.setGeometry(screen.geometry())
        view.showFullScreen()
        view.activateWindow()
        self.preview.setFocus()
        view.show_hint(tr('Espacio: reproducir / pausar · Esc: salir'))
        self.fullscreen_button.setChecked(True)

    def exit_fullscreen_preview(self):
        view = self.fullscreen_view
        if view is None:
            return
        self.fullscreen_view = None  # First: closing the view asks for this again.
        self.space_shortcut.setEnabled(True)  # tick() disables it again while a text field has focus.
        self.preview_layout.insertWidget(max(0, self._preview_slot), self.preview, 5)
        self.preview.guides = self.guides.isChecked()
        self.preview.backdrop = QColor(Preview.BACKDROP)
        self.preview.show()
        self.preview.update()
        view.hide()
        view.deleteLater()
        self.fullscreen_button.setChecked(False)
        self.activateWindow()
        self.preview.setFocus()
