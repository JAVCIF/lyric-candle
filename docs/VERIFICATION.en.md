# Verification · 0.2.4-alpha

[English](VERIFICATION.en.md) · [Español](../VERIFICACION.md) · [Home](../README.md)

The full local baseline passed **146 tests with no skips** in about 13 seconds, using Python 3.12, PySide6 6.8.3 and FFmpeg/ffprobe 6.1.1 on Linux with Qt offscreen.

```sh
python -m unittest discover -s tests -v
```

Use `PROBAR.bat` on Windows after installation. Media tests may skip when FFmpeg is absent; install both tools for complete coverage. GitHub Actions results are independent of this recorded local baseline and are visible in the repository's Actions tab.

## 18 stabilization regressions

- Typing sets unsaved state; canceling close retains text; saving on close persists it as a draft.
- Save/reopen restores current/other-row drafts, empty text, newlines, non-breaking spaces and Unicode without replacing applied lyrics or deleting marks.
- Autosave/recovery restores drafts. Applying one keeps others; timing/style changes and undo/redo do not erase pending text.
- Export directs the user to pending text before asking for a destination. The worker rejects saved projects with unapplied drafts too.
- A 720×480 SAR 32:27 video produces a square-pixel 854×480 still and export without introduced side bars; both default MP4 and source-format export are tested.
- Asymmetric colored clips at 90°, -90° and 180° check display dimensions and actual orientation, catching ignored or double rotations.
- Rotation combined with non-square pixels exports 480×854 without added bars. Unknown SAR and SAR 1:2 also retain the image.
- Paused reopening restores the saved time/aspect via FFmpeg extraction and Qt's fallback; older tracked canvases are corrected.
- Old projects without the draft field remain compatible; malformed draft structures are rejected.

## Retained coverage: 128 tests

Model/rendering, paired TXT import, Unicode ranges, keyframes, linked navigation, marking, numeric −/+ controls, font hover/search/Esc/commit, paused-video restore, text edits across row changes, undo grouping, waveform peaks, per-window recovery, moved paths, base-video settings, English UI/dictionary, guide, portable mode, branding and transport controls.

Real export tests include MP4 with audio and AVI MPEG-4/XVID at 24000/1001 FPS with copied audio. The full local log had no Python exceptions or skipped tests. Missing-audio-device/CPU-decoder notices and an intentionally invalid test media file are expected.

## Manual checks still required

Windows BAT startup, audible output, personal codec combinations, high-DPI behavior and running a packaged EXE on a target machine. A passing packaging workflow shows the EXE was built; it does not establish these manual checks. No physical audio output was available for local verification. macOS packaging has not been tested or supplied.
