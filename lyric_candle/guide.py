"""Quick guide (Help → Quick guide) in Spanish and English, written for the packaged app:
installed (data in the user's AppData) or portable (portable.txt next to the EXE)."""
from __future__ import annotations
from html import escape

from .i18n import language

STYLE = '''<style>
body { color:#e3eaf6; font-size:13px; }
h1 { color:#c5e8ff; font-size:20px; margin:0 0 4px 0; }
h2 { color:#9ed6fa; font-size:15px; margin:18px 0 6px 0; }
p, li { line-height:140%; }
.muted { color:#93a8c5; }
.box { background:#162236; border:1px solid #2c405d; padding:8px; }
kbd, code { color:#ffe49c; font-family:Consolas,'DejaVu Sans Mono',monospace; }
td { padding:3px 14px 3px 0; }
</style>'''

ES = '''
<h1>Lyric Candle {version}</h1>
<p class="muted">Editor de video lyrics: escucha, marca y anima. Original y traducción, por frase y por sílaba.</p>

<h2>Antes de empezar: FFmpeg</h2>
<p>Coloca <code>ffmpeg.exe</code> y <code>ffprobe.exe</code> en la carpeta <code>tools</code> junto a
<code>LyricCandle.exe</code> (créala si no existe), o instálalos en el PATH. Se necesitan para exportar,
dibujar la forma de onda, ajustar marcas al audio y leer las propiedades de un video.
Sin FFmpeg puedes editar y previsualizar igualmente. Estado actual: <b>{ffmpeg}</b>.</p>

<h2>1 · Medio y letra</h2>
<ol>
<li><b>Audio / video</b>: carga una canción o un video. Si es video, se ofrece como fondo.</li>
<li><b>Importar letra</b>: TXT alternado (original, traducción, línea vacía) o dos columnas.
Revisa las parejas en la vista previa; los tiempos iniciales son provisionales.</li>
</ol>

<h2>2 · Marcar tiempos escuchando</h2>
<ol>
<li>Selecciona la primera frase y reproduce desde un poco antes (<kbd>Espacio</kbd>).</li>
<li>Pulsa <kbd>Ctrl+M</kbd> cuando empiece cada frase: marca su inicio y cierra la anterior.</li>
<li>Después de la última, pulsa <kbd>Ctrl+F</kbd> cuando termine de cantarse.</li>
<li>Corrige en la tabla (segundos o <code>mm:ss.mmm</code>) o arrastrando los bordes en la forma de onda.</li>
</ol>
<p><b>Vincular frase ↔ tiempo</b> mueve el cabezal al elegir una frase y selecciona la frase activa al reproducir;
mientras marcas con Ctrl+M muestra la frase que viene. <b>Zoom frase</b>, <b>Bucle</b>, <b>Repetir frase</b>
y la velocidad 0.5× / 0.75× ayudan a afinar (la exportación siempre sale a velocidad normal).</p>

<p>Con <b>Zoom frase</b> activo, la selección queda fija: <kbd>Ctrl+M</kbd> ajusta solo su inicio y <kbd>Ctrl+F</kbd> solo su final, sin avanzar. Desactívalo para marcar frases consecutivas.</p>

<h2>3 · Sílabas y efectos</h2>
<ul>
<li>En <b>Sílabas</b>, selecciona letras y pulsa <b>Marcar selección</b>, o escribe el texto con <code>|</code>
entre partes (<code>vuel|ve a bri|llar</code>). <b>Repetir en frases</b> marca la misma parte en toda la canción.</li>
<li><b>Estimar tiempos</b> reparte por texto; <b>Ajustar a ataques del audio</b> acerca cada marca al golpe más cercano
(puede seguir instrumentos: verifica escuchando). Doble clic en <b>Parte</b> reproduce desde ahí.</li>
<li>En <b>Efectos</b>: 1 · Repintado, 2 · Desvanecimiento o 3 · Avanzado (énfasis por sílaba con color, subida y escala).</li>
<li>En <b>Keyframes</b> defines cuándo llega cada frase a cada % de su animación: sostener una vocal, acelerar el final…
<b>Bloquear tiempo (X)</b> o <b>Bloquear avance (Y)</b> limitan el arrastre de los puntos.</li>
</ul>

<h2>4 · Diseño y video base</h2>
<ul>
<li>Una o dos líneas, posición, fuente (pasa el mouse por la lista para probarla), tamaños, colores y contorno.
<b>Separación</b> solo se usa con dos líneas centradas.</li>
<li><b>Usar resolución y FPS del video base</b> ajusta el lienzo al video cargado (también 23.976 o 29.97 fps).</li>
<li>El fondo puede ser degradado, imagen o el propio video.</li>
</ul>

<h2>5 · Guardar y exportar</h2>
<ul>
<li><b>Guardar</b> crea un <code>.lyric.json</code>. Los medios se vinculan, no se copian: puedes mover el proyecto solo,
junto con sus medios o con el medio a su lado; si no lo encuentra, al abrir te pide buscarlo.</li>
<li>El texto sin aplicar también se guarda y autoguarda como borrador. Al reabrir puedes retomarlo en <b>Frase</b>.
El contador de arriba indica cuántas frases están pendientes; aplica sus cambios antes de exportar.</li>
<li><b>Exportar video</b>: MP4 (H.264 + AAC) o <b>Igual que el video base</b> (mismo contenedor, códec, formato de píxel y
bitrate; el audio se copia). Los problemas de tiempos se señalan arriba a la derecha y bloquean la exportación.</li>
</ul>

<h2>Atajos</h2>
<table>
<tr><td><kbd>Espacio</kbd></td><td>Reproducir / pausar (fuera de los campos de texto)</td></tr>
<tr><td><kbd>Ctrl+M</kbd> · <kbd>Ctrl+F</kbd></td><td>Marcar inicio y avanzar · marcar final</td></tr>
<tr><td><kbd>Ctrl+Z</kbd> · <kbd>Ctrl+Y</kbd></td><td>Deshacer · rehacer</td></tr>
<tr><td><kbd>Ctrl+N</kbd> · <kbd>Ctrl+O</kbd> · <kbd>Ctrl+S</kbd> · <kbd>Ctrl+Shift+S</kbd></td><td>Nuevo · abrir · guardar · guardar como</td></tr>
<tr><td><kbd>Ctrl+I</kbd> · <kbd>Ctrl+E</kbd></td><td>Importar letra · exportar video</td></tr>
</table>

<h2>Instalada o portable</h2>
<div class="box">
<p>Modo actual: <b>{mode}</b><br>Ajustes, autoguardado y registro: <code>{data}</code></p>
</div>
<ul>
<li><b>Instalada</b> (predeterminado): los datos quedan en tu carpeta de usuario y no se mezclan con el programa.</li>
<li><b>Portable</b>: crea un archivo vacío <code>portable.txt</code> junto a <code>LyricCandle.exe</code>. Desde el siguiente
inicio todo se guarda en la carpeta <code>data</code> al lado, para llevar el programa en una memoria USB.</li>
<li>El autoguardado ocurre cada 20 s tras un cambio. Si el programa se cierra inesperadamente, al abrirlo te ofrece recuperar
la sesión. <b>Opciones → Abrir carpeta de datos</b> lleva a esa carpeta.</li>
<li><b>Opciones → Idioma</b>: automático (según Windows), español o inglés. Se aplica al reiniciar.</li>
</ul>

<h2>Límites de esta alpha</h2>
<p class="muted">No reconoce el canto ni divide sílabas automáticamente: el flujo es marcar escuchando y refinar.
Un medio por proyecto. Las fuentes dependen del equipo (para japonés, usa una fuente con esos caracteres).
Sin importación de SRT, ASS o LRC todavía. Más detalles en LEEME.md.</p>
'''

EN = '''
<h1>Lyric Candle {version}</h1>
<p class="muted">Lyric video editor: listen, mark and animate. Original and translation, per line and per syllable.</p>

<h2>Before you start: FFmpeg</h2>
<p>Put <code>ffmpeg.exe</code> and <code>ffprobe.exe</code> in the <code>tools</code> folder next to
<code>LyricCandle.exe</code> (create it if needed), or install them on the PATH. They are needed to export,
draw the waveform, snap marks to the audio and read a video's properties.
You can still edit and preview without FFmpeg. Current status: <b>{ffmpeg}</b>.</p>

<h2>1 · Media and lyrics</h2>
<ol>
<li><b>Audio / video</b>: load a song or a video. A video is also offered as the background.</li>
<li><b>Import lyrics</b>: alternating TXT (original, translation, blank line) or two columns.
Check the pairs in the preview; the first timings are provisional.</li>
</ol>

<h2>2 · Timing by ear</h2>
<ol>
<li>Select the first line and play from a little earlier (<kbd>Space</kbd>).</li>
<li>Press <kbd>Ctrl+M</kbd> when each line starts: it marks its start and closes the previous one.</li>
<li>After the last line, press <kbd>Ctrl+F</kbd> when it stops being sung.</li>
<li>Fix times in the table (seconds or <code>mm:ss.mmm</code>) or drag the edges on the waveform.</li>
</ol>
<p><b>Link line ↔ time</b> moves the playhead when you pick a line and selects the active line during playback;
while marking with Ctrl+M it shows the next line. <b>Zoom line</b>, <b>Loop</b>, <b>Repeat line</b>
and 0.5× / 0.75× speed help you fine-tune (exports always play at normal speed).</p>

<p>With <b>Zoom line</b> enabled, selection stays fixed: <kbd>Ctrl+M</kbd> adjusts only its start and <kbd>Ctrl+F</kbd> only its end, without advancing. Turn zoom off for sequential marking.</p>

<h2>3 · Syllables and effects</h2>
<ul>
<li>In <b>Syllables</b>, select letters and press <b>Mark selection</b>, or type the text with <code>|</code>
between parts (<code>shi|ning a|gain</code>). <b>Repeat in lines</b> marks the same part across the song.</li>
<li><b>Estimate timings</b> spreads them by text; <b>Snap marks to audio attacks</b> moves each mark to the nearest hit
(it can follow instruments: check by ear). Double-click a <b>Part</b> to play from there.</li>
<li>In <b>Effects</b>: 1 · Repaint, 2 · Fade or 3 · Advanced (per-syllable emphasis with color, lift and scale).</li>
<li>In <b>Keyframes</b> you decide when a line reaches each % of its animation: hold a vowel, speed up the end…
<b>Lock time (X)</b> or <b>Lock progress (Y)</b> restrict how points are dragged.</li>
</ul>

<h2>4 · Design and base video</h2>
<ul>
<li>One or two lines, position, font (hover over the list to try it), sizes, colors and outline.
<b>Spacing</b> only applies to two centered lines.</li>
<li><b>Use base video resolution and FPS</b> matches the canvas to the loaded video (23.976 or 29.97 fps too).</li>
<li>The background can be a gradient, an image or the video itself.</li>
</ul>

<h2>5 · Save and export</h2>
<ul>
<li><b>Save</b> creates a <code>.lyric.json</code>. Media are linked, not copied: you can move the project alone,
together with its media, or with the media next to it; if a file can't be found, you'll be asked to locate it.</li>
<li>Unapplied text is also saved and autosaved as a draft. Reopen it in the <b>Line</b> tab to resume editing.
The counter at the top shows pending lines; apply their changes before exporting.</li>
<li><b>Export video</b>: MP4 (H.264 + AAC) or <b>Same as base video</b> (same container, codec, pixel format and bitrate;
audio is copied). Timing problems are flagged at the top right and block the export.</li>
</ul>

<h2>Shortcuts</h2>
<table>
<tr><td><kbd>Space</kbd></td><td>Play / pause (outside text fields)</td></tr>
<tr><td><kbd>Ctrl+M</kbd> · <kbd>Ctrl+F</kbd></td><td>Mark start and advance · mark end</td></tr>
<tr><td><kbd>Ctrl+Z</kbd> · <kbd>Ctrl+Y</kbd></td><td>Undo · redo</td></tr>
<tr><td><kbd>Ctrl+N</kbd> · <kbd>Ctrl+O</kbd> · <kbd>Ctrl+S</kbd> · <kbd>Ctrl+Shift+S</kbd></td><td>New · open · save · save as</td></tr>
<tr><td><kbd>Ctrl+I</kbd> · <kbd>Ctrl+E</kbd></td><td>Import lyrics · export video</td></tr>
</table>

<h2>Installed or portable</h2>
<div class="box">
<p>Current mode: <b>{mode}</b><br>Settings, autosaves and log: <code>{data}</code></p>
</div>
<ul>
<li><b>Installed</b> (default): data stays in your user folder, apart from the program.</li>
<li><b>Portable</b>: create an empty <code>portable.txt</code> file next to <code>LyricCandle.exe</code>. From the next start,
everything is stored in the <code>data</code> folder beside it, so the program can travel on a USB drive.</li>
<li>Autosave runs every 20 s after a change. If the program closes unexpectedly, it offers to recover the session on the
next start. <b>Options → Open data folder</b> takes you there.</li>
<li><b>Options → Language</b>: automatic (from Windows), Spanish or English. Applied after a restart.</li>
</ul>

<h2>Limits of this alpha</h2>
<p class="muted">It doesn't recognize singing or split syllables automatically: the workflow is to mark by ear and refine.
One media file per project. Fonts depend on the computer (for Japanese, use a font that has those characters).
No SRT, ASS or LRC import yet. More details in LEEME.md.</p>
'''


def guide_html(version: str, portable: bool, data: str, ffmpeg: bool) -> str:
    english = language() == 'en'
    text = EN if english else ES
    if english:
        mode = 'portable (portable.txt found)' if portable else 'installed'
        status = 'found' if ffmpeg else 'not found'
    else:
        mode = 'portable (se encontró portable.txt)' if portable else 'instalada'
        status = 'encontrado' if ffmpeg else 'no encontrado'
    return STYLE + text.format(version=escape(version), mode=escape(mode), data=escape(data), ffmpeg=status)
