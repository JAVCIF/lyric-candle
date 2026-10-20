# Estructura

- `main.py`: entrada con diagnóstico de errores de arranque.
- `lyric_candle/model.py`: proyecto, validación, persistencia atómica, marcas por rangos Unicode y estimaciones de tiempos.
- `lyric_candle/render.py`: composición QPainter sobre posiciones fijas. Compartida por preview/exportación; cachea los trazados de texto.
- `lyric_candle/media.py`: onda y exportación en QThread; FFmpeg mediante argumentos, sin shell. Imagen/video conservan proporciones. Exportación temporal y reemplazo al terminar.
- `lyric_candle/app.py`: editor Qt, reproducción Qt Multimedia, controles, historial, autoguardado y recuperación.
- `lyric_candle/widgets.py`: preview, colores y forma de onda con edición de extremos.
- `lyric_candle/dialogs.py`: importación de textos emparejados.
- `tests/test_alpha.py`: pruebas de modelo, UI y exportación real.

Los tiempos de frase son absolutos. Los de repintado y sílabas son relativos. Cada marca almacena rangos de caracteres del texto original sin modificarlo. Un campo individual vacío hereda la configuración global.

El formato `.lyric.json` es JSON UTF-8 con `format: lyric-candle` y `schema: 2` (lectura compatible con schema 1). Las rutas de recursos se guardan relativas cuando es posible. Los proyectos pueden conservar borradores que excedan la duración actual: la UI lo indica y la exportación exige corregirlo.

Documentación consultada para las integraciones:
- Qt QVideoSink: https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QVideoSink.html
- FFmpeg: https://ffmpeg.org/ffmpeg.html y https://ffmpeg.org/ffmpeg-formats.html

Lyric Candle se mantiene como proyecto independiente de Sonic Candle. La documentación del repositorio está en español e inglés.

Alpha 0.2.4: `Project.text_drafts` es un campo opcional del schema 2, indexado por UID de frase y pista. En el editor, los borradores viven en los cuadros y en `_text_drafts`; `project_with_drafts()` los incorpora a una copia para guardar/autoguardar. No se mezclan con el texto aplicado, las marcas ni las instantáneas de deshacer. La carga valida su estructura y descarta referencias a frases que ya no existen. Exportar requiere aplicar los borradores.

Geometría de video: el tamaño de visualización aplica SAR antes de la rotación. FFmpeg autorrota y el filtro compartido `SQUARE_PIXELS` normaliza SAR antes de producir el PNG pausado o ajustar el fondo exportado. Qt 6.8 ya transforma SAR/orientación en `QVideoFrame.toImage()`, por lo que esa imagen no se transforma de nuevo. El encoder declara SAR 1:1 para el lienzo compuesto. La sintaxis del filtro funciona en FFmpeg 6.1.

La curva usa Keyframe(time, progress), con tiempo relativo y progreso entre 0 y 1. Incluye extremos implícitos del intervalo de repintado, interpolación lineal y progreso no decreciente. El reloj virtual anima sílabas; visibilidad y desvanecimiento permanecen en el reloj real. La navegación vinculada distingue selección manual de seguimiento para evitar realimentación y proteger el estado de Ctrl+M.

Alpha 0.2.1: el hover usa una copia superficial de la configuración de la vista previa, sin alterar el proyecto exportable. El campo playhead guarda la posición de vista dentro del schema 2. Las respuestas de extracción de fotogramas llevan una generación de medio y un número de solicitud para descartar respuestas tardías. La búsqueda pendiente se reaplica al recibir LoadedMedia para evitar que un 0 transitorio sustituya la posición guardada.

Versión: el número vive solo en `VERSION` (`lyric_candle/model.py`); el encabezado y los proyectos guardados lo toman de ahí. Al publicar una versión, actualiza también el título de `docs/USER_GUIDE.es.md`, agrega sus notas bilingües en `docs/releases/x.y.z.md` (el workflow de release las usa) y resume el cambio en `CHANGELOG.md`.

Logo: `lyric_candle/assets/logo.svg` es la fuente (solo funciones SVG Tiny, para que Qt lo dibuje igual). `logo.ico` (16–256 px) y `logo-256.png` se generaron a partir de él; si cambias el SVG, vuelve a generarlos. En Windows, `main()` fija un AppUserModelID propio para que la barra de tareas muestre este icono y no el de Python.

Idioma: el texto fuente está en español y se envuelve en `tr()` (`lyric_candle/i18n.py`); la versión inglesa vive en `lyric_candle/i18n_en.py`, con la misma clave. Para textos con datos usa `tr('Frase {0}').format(n)`, nunca f-strings dentro de `tr()`. `tests/test_i18n.py` falla si un texto no tiene traducción, si cambian los marcadores `{}` o si queda español visible en la ventana en inglés. La variable `LYRIC_CANDLE_LANG=es|en` fuerza el idioma (las pruebas usan `es`). Los problemas de `Project.problem_items()` llevan un código estable; compara por código, no por texto.

Rutas: `lyric_candle/paths.py` decide la carpeta de datos (instalada o portable con `portable.txt`) y crea los `QSettings` (INI en modo portable).
