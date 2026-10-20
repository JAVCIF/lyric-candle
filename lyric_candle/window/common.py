"""Theme, file filters and small helpers shared by the window modules."""
from __future__ import annotations

from ..i18n import tr
from ..model import VERSION

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
