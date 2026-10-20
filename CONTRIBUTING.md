# Contributing / Contribuir

## English

For bugs, include the app version, OS, Python or Windows artifact source, FFmpeg/ffprobe versions, reproducible steps, expected/actual behavior and relevant logs. A minimal project with synthetic/shareable media is most useful. Remove personal paths and unrelated content before attaching it.

Use a focused branch/PR. Explain the user-visible behavior changed and validation performed. Follow the [development guide](docs/DEVELOPMENT.en.md), run the full suite with FFmpeg and add a regression for timing, persistence or rendering changes. Maintain both UI languages and corresponding documentation. For translations, preserve formatting placeholders and newline counts.

Keep compiled files, local environments, logs, settings, recovery files and personal media out of commits. Architecture matters: preview and export share a renderer; text anchors stay fixed; drafts stay separate from applied text; media results must reject stale requests.

The project is alpha and has no selected project license yet. Discuss substantial proposed contributions with the maintainer before investing in a large change.

## Español

Al reportar un error, incluye versión, sistema, origen del Python/artefacto de Windows, versiones FFmpeg/ffprobe, pasos, resultado esperado/real y registros relevantes. Un proyecto mínimo con medios sintéticos o compartibles ayuda a reproducirlo. Quita rutas personales y contenido ajeno al caso.

Usa una rama/PR con alcance concreto. Explica el comportamiento que cambió y cómo se comprobó. Sigue la [guía de desarrollo](docs/DEVELOPMENT.es.md), ejecuta la suite completa con FFmpeg y agrega regresiones para cambios de tiempos, persistencia o render. Mantén ambos idiomas y su documentación. En traducciones conserva los campos de formato y saltos de línea.

No incluyas compilados, entornos, registros, ajustes, recuperaciones ni medios personales. Conserva el renderer compartido, anclajes fijos, borradores separados del texto aplicado y descarte de respuestas antiguas de medios.

El proyecto es alpha y su licencia está pendiente de elegir. Comenta las contribuciones grandes con el mantenedor antes de invertir en un cambio extenso.
