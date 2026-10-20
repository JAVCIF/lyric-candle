# Desarrollo

[English](DEVELOPMENT.en.md) · [Español](DEVELOPMENT.es.md) · [Inicio](../README.es.md)

## Entorno

La referencia es Python 3.12 de 64 bits; el instalador de Windows acepta 3.10–3.14. `requirements.txt` y `pyproject.toml` aceptan PySide6 `>=6.8,<6.11` (Python 3.14 usa la 6.10). CI prueba Python 3.12 en Linux y Windows, Python 3.14 con el PySide6 más nuevo permitido y Python 3.10 con PySide6 6.8.3, la pareja más antigua soportada. Sube el límite superior solo cuando la suite pase con la siguiente serie de Qt. FFmpeg/ffprobe son programas externos.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

El uso interactivo necesita una sesión gráfica. Las pruebas Linux usan `QT_QPA_PLATFORM=offscreen`; las de Windows usan el backend nativo `windows` para acceder a las fuentes reales del sistema. El runner Windows de CI ofrece una sesión de escritorio. El editor no requiere claves API ni un servicio en la nube.

## Estructura

| Ruta | Responsabilidad |
| --- | --- |
| `main.py` | Entrada de escritorio y diagnóstico de arranque |
| `lyric_candle/model.py` | Modelo, validación, relojes y guardado; fuente única de `VERSION` |
| `lyric_candle/render.py` | QPainter compartido por preview/exportación y anclajes fijos |
| `lyric_candle/app.py` | Ventana, edición, reproducción, historial, recuperación y exportación |
| `lyric_candle/widgets.py` | Preview, onda, curva, fuentes y botones numéricos |
| `lyric_candle/media.py` | FFmpeg, workers de onda/exportación/fotogramas y geometría |
| `lyric_candle/lyrics_import.py`, `dialogs.py` | Lectura de parejas y diálogo de importación |
| `lyric_candle/i18n.py`, `i18n_en.py`, `guide.py` | Idioma, traducciones y guía bilingüe |
| `lyric_candle/paths.py` | Ajustes y rutas instaladas/portables |
| `lyric_candle/assets/` | Logo SVG e iconos |
| `examples/` | Medios sintéticos y proyectos de ejemplo |
| `tests/` | Pruebas de modelo, render, UI y medios reales |
| `scripts/build_windows.py` | Empaquetado para CI/uso local sin pausas de BAT |
| `.github/workflows/` | Pruebas Linux/Windows y compilación portable |

## Modelo y tiempos

El proyecto es JSON UTF-8 con `format: "lyric-candle"`, `schema: 2` y un campo de versión. También se lee schema 1. Los campos opcionales nuevos usan valores predeterminados.

- `Project`: medio/imagen, duración, estilo, frases, cabezal guardado y `text_drafts` opcional.
- `Cue`: UID estable, original/traducción aplicados, inicio/final absolutos, intervalo relativo de repintado, marcas por pista y keyframes.
- Los rangos de marcas indexan puntos de código Unicode de Python. Las selecciones de Qt usan unidades UTF-16: se convierten al marcar. No se insertan separadores visibles en el texto guardado.
- Repintado y sílabas usan tiempos relativos a la frase. Los keyframes llevan segundos a un progreso que no retrocede; porcentajes iguales sostienen. Audio y desvanecimientos siguen el reloj real.
- Si la curva afecta al énfasis, los tiempos de sílabas son anclas del reloj de animación. Convierte al reloj real para buscar o ajustar ataques del audio.

`text_drafts` relaciona UID con campos `original` y/o `translation`. En la ventana, los borradores viven en los cuadros y `_text_drafts`; `project_with_drafts()` los incorpora a una copia al guardar. El texto aplicado y sus marcas permanecen separados. Exportar exige aplicar los pendientes. Cargar cuadros guardados no debe marcar falsamente cambios nuevos.

El guardado usa temporal hermano, flush y reemplazo. Las rutas relativas tienen respaldo absoluto. La recuperación usa archivos por ventana y bloqueos; se ofrecen solo sesiones huérfanas. Conserva esa separación entre instancias.

## Render y medios

Preview y exportación usan `Renderer`. No calcules anclajes a partir de límites animados: las dos líneas deben conservar alineación aunque sus longitudes difieran. El hover de fuentes usa un override temporal y no modifica el estilo guardado.

Qt ya transforma la imagen de video. La extracción/exportación FFmpeg autorrota y normaliza SAR antes de ajustar el fondo. Evita aplicar dos veces esos cambios. El lienzo compuesto usa píxeles cuadrados. Las respuestas de workers incluyen generación de medio/búsqueda para descartar fotogramas antiguos.

Los procesos reciben listas de argumentos sin shell. Se recodifica el video y se toma el primer audio; el formato de origen copia ese audio. Cancelar debe interrumpir lecturas/escrituras de tuberías; el destino anterior se conserva hasta terminar correctamente.

## Pruebas

```sh
python -m unittest discover -s tests -v
python -m unittest discover -s tests -p test_stability.py -v
```

Instala FFmpeg/ffprobe para evitar omisiones de medios. La base 0.2.4 tiene 146 pruebas. CI instala las herramientas y ejecuta Python 3.12 en Linux y Windows. [Verificación](VERIFICATION.es.md) registra la base local; Actions conserva por separado sus ejecuciones remotas.

Revisa el registro completo para detectar excepciones de slots Qt además del estado unittest. Los avisos de dispositivo de audio ausente/decodificación por CPU son posibles sin pantalla. Las pruebas no verifican audio audible ni todos los códecs del usuario.

## Español e inglés

Envuelve literales españoles con `tr('literal')` y agrega su entrada inglesa en `i18n_en.EN`. Aplica datos después con `.format(...)`. Conserva campos, espacios de borde y saltos de línea. Las pruebas verifican cobertura y UI inglesa. La guía HTML tiene ambas versiones en `guide.py`.

## Compilar en Windows

Desde el entorno activado:

```powershell
python -m pip install -r requirements.txt
python -m pip install "pyinstaller>=6.11,<7"
python scripts/build_windows.py --portable --zip
```

Se crean `dist/LyricCandle/` y `dist/Lyric-Candle-1.0.0-beta-Windows-x64.zip`; la versión se lee del modelo. `--portable` agrega `portable.txt`, `--zip` comprime y escribe SHA-256. Sin `--portable` se mantiene el almacenamiento instalado. Se incluyen documentación y avisos.

`scripts\windows\CREAR_EXE.bat` sigue disponible como alternativa interactiva. Distribuye toda la carpeta, incluido `_internal`. FFmpeg no se incluye: agrégalo a `tools/` junto al EXE o usa PATH. PyInstaller solo hace falta para construir. El arranque, audio, HiDPI y medios deben probarse además en Windows.

El workflow compila con pushes a `main`, pull requests y ejecución manual; los artefactos duran 30 días y no son Releases. Ese workflow tiene permiso de lectura; el workflow separado Release publica las versiones probadas.

## Antes de una versión

1. Actualiza `model.VERSION`, ambos README y los cambios/documentación bilingües.
2. Ejecuta la suite completa con FFmpeg e inspecciona el registro.
3. Compila Windows y prueba la carpeta extraída completa en un equipo de destino.
4. Comprueba fuentes, fotograma pausado, marcado/vinculación, borradores/recuperación y exportación con audio.
5. Registra el entorno probado y los límites pendientes; etiqueta/publica el commit revisado.

Evita subir entornos, ejecutables, binarios FFmpeg, registros, ajustes, recuperaciones o medios/proyectos personales. Usa demos sintéticas o material compartible. El proyecto usa la [licencia MIT](../LICENSE); consulta [componentes externos](../THIRD_PARTY.md).

## Installer and release / Instalador y publicación

En Windows instala Inno Setup 6 o posterior. Después del portable ejecuta `python scripts/build_installer.py` y `python scripts/check_windows_packages.py`. Se genera `dist/Lyric-Candle-1.0.0-beta-Setup-x64.exe` y su SHA-256. El instalador excluye `portable.txt` y `data/`, instala para el usuario sin administrador y conserva ajustes/proyectos al desinstalar. El comprobador extrae el ZIP, abre ambos EXE con `--smoke-test`, instala y desinstala en silencio. Este indicador abre la ventana y la cierra tras un segundo; no evalúa audio audible.

El workflow Windows build comprueba y conserva ambos paquetes durante 30 días. Release se ejecuta tras Tests exitoso en un push a main: usa exactamente el SHA probado, vuelve a construir/comprobar ambos paquetes y crea `v<VERSION>` con las notas de `docs/releases/<VERSION>.md`. Las versiones alpha son prereleases. No reemplaza releases existentes. Para publicar una versión nueva actualiza VERSION y agrega sus notas bilingües. Solo ese trabajo tiene permiso contents:write.
