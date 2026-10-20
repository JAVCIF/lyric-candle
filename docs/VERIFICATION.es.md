# Verificación · 1.0.0-beta

## 1.0.0-beta

La suite completa pasó **181 pruebas sin omisiones** (unos 15 segundos por ejecución) con FFmpeg/ffprobe 6.1.1 en Linux y Qt sin pantalla, en tres entornos:

| Python | PySide6 | Resultado |
|---|---|---|
| 3.14.6 | 6.10.3 | 181 aprobadas |
| 3.13 | 6.8.3 | 181 aprobadas |
| 3.10.20 | 6.8.3 | 181 aprobadas |

También pasan Ruff (`ruff check .`, configurado en `pyproject.toml`) y la comprobación de enlaces de la documentación. Nuevo en esta beta: cinco pruebas de ProRes 4444 con alfa que decodifican el `.mov` exportado y comprueban transparencia, códec, perfil, formato de píxel y ausencia de audio. La división de la ventana principal se validó ejecutando la suite sin cambios sobre los nuevos módulos. El empaquetado, la instalación en Windows y la reproducción audible los cubren los jobs de Windows en CI y debes comprobarlos en tu equipo.

## Base de la Alpha 0.2.4

**146 pruebas aprobadas, sin omisiones**, ejecutando la suite completa con Python 3.12, PySide6 6.8.3 y FFmpeg/ffprobe 6.1.1 en Linux con Qt sin pantalla. Duración de la ejecución: aproximadamente 13 segundos.

Comando: `python -m unittest discover -s tests -v` (con `QT_QPA_PLATFORM=offscreen` y `LYRIC_CANDLE_LANG=es` en este entorno). En Windows puedes usar `scripts\windows\PROBAR.bat`.

## Regresiones nuevas (18 pruebas)

- Texto sin aplicar: activa el estado modificado y el aviso de cierre; cancelar conserva el texto y guardar al salir lo escribe como borrador.
- Guardar/reabrir conserva borradores de varias frases, texto vacío, saltos de línea, espacios duros y Unicode. La carga no marca falsamente el proyecto como modificado.
- Autoguardado y recuperación restituyen los borradores. Aplicar una frase conserva los demás borradores; cambios de tiempo/diseño y deshacer/rehacer no los borran.
- Exportar con texto pendiente lleva a la frase para revisarlo, sin abrir el selector de destino. El worker también rechaza proyectos guardados que todavía contienen borradores.
- Video 720×480 con SAR 32:27: fotograma pausado y salida de 854×480 sin las barras laterales que introducía la versión anterior. Se probaron MP4 y «Igual que el video base».
- Rotaciones 90°, -90° y 180°: exportación con dimensiones de visualización y posición de colores asimétricos correctas, para detectar giros repetidos o ignorados.
- Combinación de rotación y SAR: lienzo y exportación de 480×854 sin deformación ni barras añadidas.
- Relación de píxel desconocida y SAR 1:2: la imagen no se comprime ni colapsa.
- Reapertura pausada en el tiempo guardado: proporciones correctas con extracción FFmpeg y con la alternativa de Qt. Los proyectos antiguos con seguimiento del video base corrigen su lienzo.
- Compatibilidad con proyectos sin el nuevo campo de borradores y rechazo de borradores mal estructurados.

## Cobertura conservada (128 pruebas)

Se repitieron las pruebas anteriores: modelo y render, importación de letras, marcas y keyframes, vinculación de frase/tiempo, controles −/+, fuentes con hover y cancelación, restauración de video pausado, texto sin aplicar ante cambios de fila, espacios duros, historial, forma de onda, recuperación por instancia, rutas movidas, idioma inglés, guía, modo portable, icono y reproducción.

La suite incluye exportación real MP4 y AVI MPEG-4/XVID a 24000/1001 fps con audio copiado. Se revisó el registro de la ejecución completa: no hubo excepciones de Python ni pruebas omitidas. Los avisos de audio ausente, decodificación por CPU y el medio inválido creado por una prueba son esperados en este entorno.

## Pendiente en Windows

Instalación y arranque por BAT, reproducción audible, tus medios/códecs reales y la compilación opcional con PyInstaller. Este paquete incluye código fuente y lanzadores; no incluye un EXE precompilado. No se verificó salida física de audio en el entorno de pruebas.
