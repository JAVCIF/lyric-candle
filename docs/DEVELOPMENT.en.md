# Development

[English](DEVELOPMENT.en.md) · [Español](DEVELOPMENT.es.md) · [Home](../README.md)

## Environment

Use 64-bit Python 3.12 for the reference environment. The Windows installer accepts 3.10–3.13. `requirements.txt` pins PySide6 6.8.3; FFmpeg/ffprobe are external programs, not Python dependencies.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Qt needs a desktop session for interactive use. Linux tests select `QT_QPA_PLATFORM=offscreen`; Windows tests use the native `windows` backend so the real system font database is available. The Windows CI runner supplies a desktop session. No API keys or cloud service are required by the editor.

## Repository map

| Path | Responsibility |
| --- | --- |
| `main.py` | Desktop entry point and startup diagnostics |
| `lyric_candle/model.py` | Dataclasses, validation, time mapping, project persistence; authoritative `VERSION` |
| `lyric_candle/render.py` | Shared QPainter rendering, fixed text anchors and cached text paths |
| `lyric_candle/app.py` | Qt window, editor state, playback, undo, recovery and export orchestration |
| `lyric_candle/widgets.py` | Preview, waveform, keyframe graph, font audition and explicit numeric buttons |
| `lyric_candle/media.py` | FFmpeg probing, waveform/export/still workers and display geometry |
| `lyric_candle/lyrics_import.py`, `dialogs.py` | Paired lyric parsing and import UI |
| `lyric_candle/i18n.py`, `i18n_en.py`, `guide.py` | Language selection, English dictionary and bilingual built-in guide |
| `lyric_candle/paths.py` | Installed/portable settings and data paths |
| `lyric_candle/assets/` | SVG source logo, window/taskbar icons |
| `examples/` | Synthetic sample media and editable projects |
| `tests/` | Model, rendering, UI and real media regression tests |
| `scripts/build_windows.py` | CI/local Windows packaging without interactive BAT prompts |
| `.github/workflows/` | Linux/Windows tests and portable Windows build |

## Data and timing conventions

Projects are UTF-8 JSON with `format: "lyric-candle"`, `schema: 2` and a version field. The loader also accepts schema 1. Dataclass fields are filtered when reading; optional new fields use defaults.

- A `Project` contains media/image references, duration, style, cues, saved playhead and optional `text_drafts`.
- A `Cue` has a stable UID, applied original/translation, absolute start/end, relative repaint interval, separate syllable ranges per track and animation keyframes.
- Span ranges index Python Unicode code points. Qt text selection uses UTF-16 units; conversion occurs at the editor boundary. Marking does not insert visible separators into stored lyrics.
- Span and repaint times are relative to the cue start. Keyframes map elapsed seconds to monotonic progress. Repeated progress values create holds; fades and audio remain on real time.
- When keyframes drive emphasis, syllable times are animation-clock anchors. Convert between animation and real clocks when seeking or snapping to audio.

`text_drafts` maps cue UID to a dictionary containing `original` and/or `translation` strings. In a live window, drafts live in text editors and `_text_drafts`; `project_with_drafts()` creates a persistence snapshot. Applied text and its marks remain separate. Export requires applying drafts. Opening drafts must not falsely mark a clean saved project as modified.

Saving writes a sibling temporary file, flushes it and replaces the destination. Relative asset paths are accompanied by absolute fallbacks. Per-window recovery files use locks; only orphaned sessions are offered. Do not replace this with one global recovery filename.

## Rendering and media

Preview/export share `Renderer`. Keep text layout independent of animated bounds: different language lengths must retain their fixed anchors. Font hover uses a temporary preview override rather than mutating the saved style.

Qt's video-frame image already applies its display transformation. FFmpeg extraction/export separately autorotate and normalize sample aspect ratio before fitting the background. Do not apply rotation/SAR twice. The composed canvas uses square pixels. Worker results carry source/seek generations to reject stale frames after fast seeks or source changes.

Export passes subprocess argument lists without a shell. Video is re-encoded, first audio is mapped, and the source-format option copies audio. Keep cancellation able to interrupt pipe reads/writes, and preserve an existing destination until successful replacement.

## Run tests

```sh
python -m unittest discover -s tests -v
```

Install both external FFmpeg tools to run media tests; otherwise they may be skipped. The 0.2.4 baseline is 146 tests. CI installs the tools and runs the suite on Linux and Windows with Python 3.12. [Verification](VERIFICATION.en.md) describes what the local baseline actually tested; GitHub Actions records remote runs separately.

For a focused timing/video regression:

```sh
python -m unittest discover -s tests -p test_stability.py -v
```

Read the entire test log for Qt slot exceptions as well as the unittest exit status. Audio-device/CPU-decoder notices can be expected in headless environments. Automated tests do not confirm audible playback or every user's codec combination.

## English and Spanish text

Spanish is the source text wrapped in `tr('literal')`; add the matching English entry in `i18n_en.EN`. Format data afterward with `.format(...)`. Keep format fields, leading/trailing whitespace and newline counts consistent. Tests check dictionary coverage and the English UI. Help HTML is maintained in both languages in `guide.py`.

## Building on Windows

From an activated source environment:

```powershell
python -m pip install -r requirements.txt
python -m pip install "pyinstaller>=6.11,<7"
python scripts/build_windows.py --portable --zip
```

The script creates `dist/LyricCandle/` and `dist/Lyric-Candle-0.2.6-alpha-Windows-x64.zip`, with the version read from the model. Omit `--portable` to keep installed-mode storage; a portable build adds `portable.txt` beside the EXE. `--zip` also writes a SHA-256 checksum. Documentation and notices accompany the executable.

`scripts\windows\CREAR_EXE.bat` remains an interactive alternative. Always distribute the entire generated folder, including `_internal`. FFmpeg binaries are not bundled: place them in `tools/` beside the EXE or use PATH. PyInstaller is build-time only. A packaged application still needs manual startup, audio, high-DPI and media checks on Windows.

The Windows workflow builds on pushes to `main`, pull requests and manual dispatch. Artifacts are retained for 30 days; they are build outputs, not published releases. The build workflow has read-only repository permission; the separate Release workflow publishes tested versions.

## Before a release

1. Update `model.VERSION` and both README versions; maintain bilingual changelog/user documentation.
2. Run the complete suite with FFmpeg and inspect logs.
3. Build Windows and check the full extracted folder on a target machine.
4. Check font audition, paused saved-video frame, timing/linking, drafts/recovery and export with audio.
5. Record the actual tested environment and any remaining limits. Tag/publish only the reviewed commit.

Avoid committing environments, built executables, FFmpeg binaries, logs, settings, recovery files or personal media/projects. Public examples should be synthetic or explicitly shareable. The project uses the [MIT license](../LICENSE); see [third-party acknowledgements](../THIRD_PARTY.md).

## Installer and release / Instalador y publicación

On Windows install Inno Setup 6 or later. After building the portable app run `python scripts/build_installer.py` and `python scripts/check_windows_packages.py`. This creates `dist/Lyric-Candle-0.2.6-alpha-Setup-x64.exe` and its SHA-256. Setup excludes `portable.txt` and `data/`, installs per user without administrator rights, and preserves user settings/projects on uninstall. The checker extracts the ZIP, opens both EXEs with `--smoke-test`, installs silently and uninstalls. This flag opens the window and closes it after one second; it does not assess audible playback.

Windows build checks and retains both packages for 30 days. Release runs after successful Tests on a main push: it checks out that exact tested SHA, rebuilds/checks both packages and creates `v<VERSION>` using `docs/releases/<VERSION>.md`. Alpha versions are prereleases. Existing releases are never replaced. To publish a new version update VERSION and add bilingual notes. Only that job has contents:write permission.
