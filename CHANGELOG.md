# Changelog / Cambios

[English overview](README.md) · [Resumen en español](README.es.md)

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

Detailed historical notes are retained in `CAMBIOS-*.md` (Spanish). / Las notas históricas detalladas se conservan en `CAMBIOS-*.md`.
