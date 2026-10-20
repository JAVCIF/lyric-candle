# Changelog / Cambios

[English overview](README.md) · [Resumen en español](README.es.md)

## 1.0.0-beta — 2026-10-20

**English:** first beta. Export only the lyrics as ProRes 4444 with an alpha channel. PySide6 `>=6.8,<6.11` adds Python 3.14 support (tested on 3.10, 3.13 and 3.14). The main window is split into responsibility modules without behaviour changes; the repository root is tidied (notes in `docs/releases/`, guides in `docs/`, launchers in `scripts\windows\`); `pyproject.toml` and Ruff join CI, which also tests Python 3.14 and the oldest supported pair. 181 tests.

**Español:** primera beta. Exportar solo la letra en ProRes 4444 con canal alfa. PySide6 `>=6.8,<6.11` agrega Python 3.14 (probado en 3.10, 3.13 y 3.14). La ventana principal se divide en módulos por responsabilidad sin cambios de comportamiento; la raíz del repositorio se ordena (notas en `docs/releases/`, guías en `docs/`, lanzadores en `scripts\windows\`); `pyproject.toml` y Ruff se suman a CI, que además prueba Python 3.14 y la pareja más antigua soportada. 181 pruebas.

## 0.2.6-alpha — 2026-10-20

**English:** Ctrl+M always changes the line on screen: outside a marking sequence it uses the selected row, also when Link line ↔ time selected it. A ▶ marks the Ctrl+M target and every mark is confirmed in the status bar. Imported and new lines keep provisional times (dimmed, saved in the project) that automatic following ignores, so the first pass with linking enabled no longer jumps ahead. The target has one source shared by ▶ and Ctrl+M (no hidden target after opening/recovering a project), hand-picked provisional rows stay selected during playback, and a zoomed mark on the placeholder time confirms it. Each zoomed Ctrl+M/Ctrl+F is its own undo step. Undo/redo restore the marking sequence, deleting rows keeps it on the same phrases, and holding Ctrl+M/Ctrl+F no longer repeats. Repeated final Ctrl+F corrections keep the sequence closed. Twenty-two regression tests.

**Español:** Ctrl+M siempre cambia la frase en pantalla: fuera de una secuencia usa la fila seleccionada, también si la eligió «Vincular frase ↔ tiempo». Una ▶ marca el destino de Ctrl+M y cada marca se confirma en la barra de estado. La letra importada y las frases nuevas conservan tiempos provisionales (atenuados y guardados en el proyecto) que el seguimiento automático ignora, así la primera pasada con vinculación ya no salta. El destino tiene una sola fuente compartida por ▶ y Ctrl+M (sin destino oculto tras abrir o recuperar un proyecto), las filas provisionales elegidas a mano se conservan al reproducir y marcar con zoom el tiempo provisional lo confirma. Cada Ctrl+M/Ctrl+F con zoom es su propio paso de deshacer. Deshacer/rehacer restauran la secuencia de marcado, borrar filas la mantiene en las mismas frases y mantener pulsado Ctrl+M/Ctrl+F ya no repite. Repetir Ctrl+F al corregir el final conserva la secuencia cerrada. Veintidós regresiones.

## 0.2.5-alpha — 2026-10-20

**English:** fix start/end marking in Zoom line so only the selected phrase changes. Keep selection during zoomed seeking/playback; preserve the opposite boundary and undo/redo. Add eight regression tests. Adopt MIT and publish Windows portable ZIP and per-user installer with checksums, bilingual notes and automatic package smoke checks.

**Español:** corregir el marcado de inicio/final con Zoom frase para modificar solo la frase seleccionada. Mantener selección al buscar/reproducir con zoom, conservar el otro límite y deshacer/rehacer. Agregar ocho regresiones. Adoptar MIT y publicar portable ZIP e instalador por usuario con SHA-256, notas bilingües y comprobación automática de paquetes.

## 0.2.4-alpha — 2026-10-20

### English

- Preserve unapplied text from the current and other lines in saved projects and autosaves; restore drafts after reopening or recovery.
- Mark typed changes as unsaved, show a pending-text counter and require applying drafts before export.
- Normalize non-square pixels before paused-frame extraction and video export; handle missing SAR and narrow pixels.
- Read 90°/180°/270° rotation when adopting video dimensions; refresh a tracked canvas when opening older projects.
- Add 18 regression tests; the complete 146-test baseline passed on Linux with real exports.
- Prepare the public repository with English/Spanish documentation, synthetic demos, CI and Windows packaging.
- Release the player's media source on close so closed windows do not retain Windows file locks. Use native Windows fonts and current FFmpeg frame-sync options in cross-platform tests.

### Español

- Conservar los borradores de la frase actual y otras filas al guardar y autoguardar; recuperarlos al reabrir o restaurar la sesión.
- Marcar el texto escrito como cambio sin guardar, mostrar pendientes y pedir aplicarlos antes de exportar.
- Normalizar píxeles no cuadrados en el fotograma pausado y la exportación; contemplar SAR ausente y píxeles estrechos.
- Interpretar la rotación de 90°/180°/270° al adoptar resolución y actualizar lienzos vinculados de proyectos anteriores.
- Agregar 18 regresiones; la base completa de 146 pruebas pasó en Linux con exportaciones reales.
- Preparar el repositorio público con documentación bilingüe, demos sintéticas, CI y empaquetado para Windows.
- Liberar el medio del reproductor al cerrar para evitar bloqueos de archivos en Windows. Usar las fuentes nativas y opciones vigentes de sincronización FFmpeg en las pruebas multiplataforma.

## 0.2.3-alpha

**English:** improve sequential phrase marking, text drafts between rows, non-breaking spaces, syllable timing, grouped undo, waveform peaks, recovery per window, moved-media lookup, base-video canvas/export, keyframe axis locks, branding, UI language and portable settings.

**Español:** mejorar marcado consecutivo, borradores entre filas, espacios duros, tiempos de sílabas, deshacer agrupado, picos de onda, recuperación por ventana, búsqueda de medios movidos, lienzo/exportación del video base, bloqueos de ejes, identidad visual, idioma y ajustes portables.

## Earlier alphas / Alphas anteriores

| Version | English | Español |
| --- | --- | --- |
| 0.2.2 | Explicit −/+ numeric buttons | Botones numéricos −/+ explícitos |
| 0.2.1 | Font hover preview and paused saved-video frame | Prueba de fuentes y fotograma guardado en pausa |
| 0.2 | Linked phrase/time selection and animation keyframes | Selección vinculada y keyframes de animación |
| 0.1.x | Initial editor, paired TXT input, syllable marks and MP4 export | Editor inicial, TXT emparejado, marcas y exportación MP4 |

Detailed historical notes live in `docs/releases/` (0.2.4 and earlier in Spanish). / Las notas históricas detalladas están en `docs/releases/`.
