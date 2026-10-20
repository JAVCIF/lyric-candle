# User guide · Lyric Candle 0.2.4-alpha

[English](USER_GUIDE.en.md) · [Español](../LEEME.md) · [Home](../README.md)

## Installation and demo

On Windows, install 64-bit Python 3.12, extract the source and run `INSTALAR.bat`, then `INICIAR.bat`. The dependency is pinned in `requirements.txt`. Alternatively, use a successful Windows workflow's portable artifact and run `LyricCandle.exe` from its extracted folder.

The app opens a 12-second demo with original text and synthetic audio. `examples/Demo.lyric.json` is editable, `Demo.wav` contains the beat, and `Demo.mp4` is an exported example. It has no singing: use it to understand the clock and effects. `Demo-Keyframes.lyric.json` demonstrates a hold, and `Demo-Video-Pausado.lyric.json` demonstrates reopening a paused video. The latter uses already-burned-in lyrics; those pixels cannot be edited as text.

For waveform generation, export, audio-attack suggestions and video probing, put `ffmpeg.exe` and `ffprobe.exe` in `tools/` beside the executable or source entry point, or install them on PATH. Get a build with H.264 (`libx264`) and AAC encoding from the links at [ffmpeg.org](https://ffmpeg.org/download.html). Restart the app after changing PATH. These binaries are not bundled.

## Media and canvas

Start with **New**, then **Audio / video**. Each project uses one media file: a song or a video with its own audio. There is no separate background-video/audio mixer.

In **Design**, choose a gradient, image or video background. Media fit the canvas without cropping; unused space is filled around them. Set resolution, FPS and project duration. Font sizes and margins remain pixel values when resolution changes, so review them afterward.

**Use base video resolution and FPS** adopts display dimensions, considering non-square pixels and right-angle rotation. Common fractional rates such as 23.976 and 29.97 are accepted. This locks the resolution/FPS controls until you uncheck it; changing video reads them again. The editor retains its limits of even dimensions from 320×240 to 3840×2160 and 1–120 FPS. Older projects with this option enabled refresh their canvas on opening; save to keep corrections.

## Import original lyrics and translation

**Import lyrics** has a preview and two input formats:

- **Alternating TXT:** original line, translated line, then an optional blank separator. Consecutive pairs without separators also work. Incomplete pairs or blocks with extra lines stop import and identify the problem so translations are not silently shifted.
- **Two columns:** paste one phrase per row in each column, or open two UTF-8 text files. Use the same row count, including intermediate empty translations. The entire translation column may be empty.

The importer preserves punctuation and symbols; it does not detect languages or sung timing. Proposed phrases have provisional intervals spread across the duration. Confirm the pair preview before importing. If you append rather than replace, existing phrases remain; inspect overlapping intervals.

### Text layout

| Layout | Positions | Sizes |
| --- | --- | --- |
| One line | Top/bottom left, top/bottom right, center | Primary size |
| Two lines | Left or right split between top/bottom; centered stack | Primary and secondary sizes |

Choose which language is primary. In two-line mode it is above the secondary line. Left/right lines share their respective margin; centered lines share the same axis even when their lengths differ. **Spacing** applies only to two centered lines. Text is not automatically wrapped: split an overlong phrase, edit it or reduce its size when the margin warning appears.

## Mark timing by ear

1. Select the first phrase and play from before its start.
2. Press **Ctrl+M** when each phrase begins. This starts it, closes the previous phrase and prepares the next row.
3. After starting the last phrase, press **Ctrl+F** when it ends.
4. Correct starts/ends in the table or Line tab, or drag the selected phrase's waveform edges.

The table accepts seconds or `mm:ss.mmm`. Line start/end are absolute; repaint and syllable times are relative to the phrase start. The waveform shows an edge's proposed time while dragging. Slow playback, **Loop**, **Repeat line** and **Zoom line** help refine timing; exported audio always runs at normal speed.

Selecting a row resets the marking sequence to that row. **Mark end** applies to the last phrase started in a sequence, or the selected phrase if the sequence was reset.

### Link line ↔ time

When checked, manually choosing a row seeks to its start. Seeking or playback selects the active row while preserving the exact playhead time. Gaps keep the current selection. For overlaps, the selected phrase stays selected while active; otherwise the latest-starting active phrase wins.

During Ctrl+M marking, the panel follows the phrase that will start next; Ctrl+F or manual row selection restores normal following. Unapplied text temporarily blocks automatic selection changes to protect editing. Uncheck linking to inspect a row independently of playback.

## Effects and syllable emphasis

In **Effects**, choose:

1. **Repaint:** sweep a new fill color over the text while keeping the outline unchanged. Repaint start/end delimit the sweep.
2. **Fade:** animate visibility at the start/end of each phrase. Zero duration is an instant change.
3. **Advanced:** combine repaint and/or fades with marked fragments that change color, rise and scale. These options are independent.

Emphasis does not rearrange the line: fragments keep their base anchors. Lift `0` disables movement; scale `1` keeps the original size. **Overlap fade-out** extends the outgoing phrase past its end, allowing overlap with the next. Otherwise fade-out occurs inside the phrase interval. Leave room in the project duration for the last fade to finish.

### Create marks

In **Syllables**, select the original or translation track. Their marks are independent.

- Select characters and click **Mark selection**.
- Or insert `|` boundaries in the alternate field, then create marks. Example: `shi|ning a|gain`. Removing the pipes must leave exactly the stored text, including spaces. Every nonempty part becomes a mark; disable parts you do not want to emphasize.
- **Repeat in lines** marks exact matches of the selected fragment across the same track. Existing overlapping marks are skipped; new times are estimates.

Marks must not overlap within a track. Edit relative **+Start / +End** to hold or shorten an emphasis. Double-click **Part** to play from that fragment's first real onset. Double-click **Color** for its selector. Empty color/lift/scale cells inherit the global settings; filled cells override them. Use Ctrl/Shift row selection for bulk colors or to restore global inheritance. **Expand syllable editor** opens a larger view with preview and playback.

### Timing assistance

**Estimate timings** spreads marks by text-position weights within the repaint interval. **Snap marks to audio attacks** searches for nearby amplitude increases within about ±0.18 seconds, respects order and keyframe clocks, and approximately retains each mark's duration.

Neither tool detects the voice. Drums and instruments also create attacks. Start with approximate timing, use the suggestions and verify by listening.

## Keyframes: holds and accelerations

Select a phrase and open **Keyframes**. The horizontal axis is relative seconds; the vertical axis is animation progress. Choose whether the curve drives repaint, emphasis or both.

1. Enable keyframes for the phrase.
2. Seek where a hold should begin and add a point at the playhead. Edit its progress if needed.
3. Seek to the end of the held note and use **Hold until here**, repeating the previous point's progress.
4. Add/drag further points to control the remaining progression. Double-click the graph to add a point.
5. Use **Lock time (X)** or **Lock progress (Y)** to move only the other axis.

For a repaint interval from 0 to 4 seconds:

| Relative time | Progress |
| --- | --- |
| 0.0 s | 0% (automatic) |
| 1.0 s | 40% |
| 3.0 s | 40% |
| 4.0 s | 100% (automatic) |

This reaches 40% in one second, holds for two seconds and completes the rest in the final second. Interpolation is linear, times must be distinct and progress cannot decrease. The endpoints follow **Repaint from / Until**; reset removes interior points. You can disable a curve without deleting it.

The curve is shared by both language lines, while their syllable marks remain independent. When it drives emphasis, syllable times are animation-clock times; the app maps them to playback time, including for double-click seeking. Fades, phrase visibility and audio use real time. Changing phrase duration scales its marks and points; changing the repaint interval redistributes keyframes proportionally inside that interval.

## Fonts and saved video frames

Open **Design → Font**, or type to search. Hovering a font previews it temporarily. Click or confirm to apply; Esc or leaving the popup ends audition. Audition does not change the saved project or add undo steps. Saving/export uses the confirmed font. Fonts must be installed; choose a suitable font for Japanese or other required characters.

Save preserves the playhead. Reopening restores it with playback stopped and prepares its video frame in the background. Paused seeks also update the image; stale extraction results are discarded. FFmpeg provides still extraction, with Qt's muted decoder priming as fallback. Older files without a saved playhead open at zero. Burned-in text in the background remains part of the video.

## Save, drafts and recovery

**Apply text changes** commits the Line tab's edits. Changing a text with syllable marks asks before clearing that track's marks. Direct table editing commits when the cell is confirmed.

Since 0.2.4, typing marks the project as modified. **Save** and the 20-second autosave preserve unapplied drafts from the current and other rows, separately from applied lyrics and marks. They reappear in the text boxes after reopening or recovery. The header counts pending lines. Apply them before export; the preview uses applied text. Closing with unsaved changes offers Save, Discard or Cancel.

Projects are UTF-8 `.lyric.json` files. Media are linked rather than embedded. The loader tries paths relative to the project, their saved absolute location, then a same-named file beside the project. If necessary it offers to relink missing assets. Moving a project does not install its fonts.

Each window has its own recovery file and lock. At startup, autosaves from unexpectedly closed sessions can be recovered; a live window's recovery is not offered. **Undo/redo** covers applied edits, timing and design; unapplied boxes retain their edits. Use 0.2.4 or newer when resaving projects with text drafts: older versions do not preserve that field.

## Export

- **MP4 · H.264 + AAC** is the default.
- **Same as base video** attempts its container, video codec, pixel format and bitrate and copies its first audio stream. Video is re-encoded because lyrics must be drawn into frames. Unsupported encoders/containers use the implemented compatible fallback when available, with a note after export; arbitrary combinations may still fail.
- Use **Use base video resolution and FPS** as well if the output should match the video's display canvas and rate.

Resolve pending text drafts and timing issues first. Projects with fixable timing problems can be opened for correction, but cannot export until fixed. An overflow warning allows you to review text that might be clipped. Preview and export share the same text renderer; guides are not exported.

Export writes a temporary file and replaces the destination only on success. Cancel or errors preserve an existing destination. The app refuses to overwrite its source media or background image. Keep the whole Windows application folder together; FFmpeg is still an external dependency of a packaged build.

## Shortcuts

| Shortcut | Action |
| --- | --- |
| Space | Play/pause outside text editors and font search |
| Ctrl+M / Ctrl+F | Mark start and advance / mark end |
| Ctrl+N / Ctrl+O | New / open project |
| Ctrl+S / Ctrl+Shift+S | Save / save as |
| Ctrl+I / Ctrl+E | Import lyrics / export video |
| Ctrl+Z / Ctrl+Y | Undo / redo |
| F1 | Quick guide |

## Language and portable settings

Spanish Windows UI selects Spanish; other system languages select English. **Options → Language** lets you pick automatic, Spanish or English, applied after restart. `LYRIC_CANDLE_LANG=es` or `en` overrides selection for diagnostics/tests.

Installed mode stores settings/recovery/logs in the user's application data location. To use portable mode, create `portable.txt` beside the executable (or `main.py`); the next start stores data in the adjacent `data/` folder. If it cannot write there, it falls back to installed storage. **Options → Open data folder** opens the actual location. The CI Windows artifact includes the marker.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Source launcher does not start | Run `INSTALAR.bat` again, then `DIAGNOSTICO.bat`; use 64-bit supported Python. |
| EXE fails after copying | Restore the complete extracted folder, including `_internal`; the EXE alone is insufficient. |
| Export/waveform unavailable | Verify both FFmpeg tools in `tools/` or PATH; the default encoder needs `libx264` and AAC. |
| Media missing after moving a project | Relink the file offered on open and save again. |
| Unexpected glyphs or different text width | Install the same font and ensure it includes the required characters. |
| A new text edit is absent from preview | Apply it in the Line tab; a saved draft is deliberately separate from applied text. |
| Lyrics exceed margins | Reduce size/margin, edit the phrase, or divide it into separate phrases. |
| Playback/codec problem | Read the media error in the status bar and try a common codec; export and playback use different decoding paths. |
| Startup error | Inspect `Lyric-Candle-startup-error.log` in your user folder. Runtime errors use `app.log` in the data folder. |

When reporting a bug, include the version, OS, Python or packaged-build source, FFmpeg version, steps and a small reproducible project. Use synthetic or shareable media rather than personal production files.
