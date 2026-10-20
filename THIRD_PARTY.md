# Third-party acknowledgements / Componentes externos

Lyric Candle's own code uses the [MIT license](LICENSE). This notice identifies dependencies; it does not replace their license texts. / El código propio de Lyric Candle usa la [licencia MIT](LICENSE). Este aviso identifica dependencias y no sustituye sus licencias.

| Component | Use / Uso | Upstream information / Información original |
| --- | --- | --- |
| Python | Runtime / Ejecución | [Python license](https://docs.python.org/3/license.html) |
| Qt / PySide6 6.8.3 | UI, painting, multimedia / Interfaz, dibujo y multimedia | [Qt for Python licensing](https://doc.qt.io/qtforpython-6/licenses.html) · license files shipped with installed Qt/PySide6 packages / licencias incluidas en sus paquetes |
| FFmpeg / ffprobe | Optional external media processing / Procesamiento externo opcional | [FFmpeg legal information](https://ffmpeg.org/legal.html); the selected binary's configuration and licenses apply / consulta la configuración y licencias del binario usado |
| PyInstaller | Windows build tool; not a source runtime dependency / Herramienta de compilación | [PyInstaller license](https://pyinstaller.org/en/stable/license.html) |

FFmpeg executables are not distributed here or in the Windows build artifact. System fonts are referenced, not bundled. Windows packages include the LGPL 3, GPL 3 and LGPL 2.1 texts in `docs/licenses/`. PySide6/Qt are dynamically loaded shared libraries in `_internal`; replacements must be binary-compatible. Source and component-specific terms: [PySide6 6.8.3](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.8.3-src/) and [Qt 6.8.3 sources](https://download.qt.io/official_releases/qt/6.8/6.8.3/submodules/). / No se distribuyen ejecutables FFmpeg. Las fuentes del sistema se referencian, no se incluyen. Los paquetes incluyen LGPL 3, GPL 3 y LGPL 2.1 en `docs/licenses/`. PySide6/Qt se cargan dinámicamente desde `_internal`; cualquier reemplazo debe ser compatible con sus binarios. Las fuentes originales y condiciones de cada componente están enlazadas arriba.

The synthetic demo audio/video and sample lyric text were created for this project. The Lyric Candle artwork is adapted from the author's Sonic Candle identity. / El audio/video sintético y la letra de las demos se crearon para el proyecto. La identidad de Lyric Candle adapta la de Sonic Candle del autor.
