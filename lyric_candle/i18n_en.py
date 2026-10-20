"""English interface texts, keyed by the Spanish source text used in tr().

Keep placeholders ({0}, {1:.1f}…), leading/trailing spaces and line breaks identical.
tests/test_i18n.py checks that every tr() string in the code has an entry here.
"""

EN = {
    'Tiempo provisional: márcalo con Ctrl+M o edítalo para confirmarlo.': 'Provisional time: mark it with Ctrl+M or edit it to confirm it.',
    'Ctrl+M marcará esta frase.': 'Ctrl+M will mark this line.',
    'Frase {0}: inicio en {1}.': 'Line {0}: start at {1}.',
    'Frase {0}: final en {1}.': 'Line {0}: end at {1}.',
    'Mantiene seleccionada esta frase. Marcar inicio/final ajusta solo sus límites, sin avanzar.':
        'Keeps this line selected. Mark start/end adjusts only its boundaries, without advancing.',
    'Marcar inicio  [Ctrl+M]': 'Mark start  [Ctrl+M]',
    'Borradores de texto inválidos.': 'Invalid text drafts.',
    'Guardar conserva los borradores. Aplica el texto en la pestaña Frase para verlo y exportarlo.':
        'Save keeps drafts. Apply the text in the Line tab to preview and export it.',
    '{0} frase(s) con texto sin aplicar': '{0} line(s) with unapplied text',
    'Texto sin aplicar': 'Unapplied text',
    'Hay {0} frase(s) con texto sin aplicar. Revisa y aplica sus cambios antes de exportar. Guardar conserva los borradores para retomarlos después.':
        'There are {0} line(s) with unapplied text. Review and apply their changes before exporting. Save keeps drafts so you can resume later.',
    'Aplica los borradores de texto antes de exportar.': 'Apply text drafts before exporting.',
    # --- model / validation -------------------------------------------------------------
    'Tiempo inválido; usa segundos o mm:ss.mmm.': 'Invalid time; use seconds or mm:ss.mmm.',
    'El tiempo debe ser finito y mayor o igual que cero.': 'Time must be finite and zero or greater.',
    'original': 'original',
    'traducción': 'translation',
    'Selecciona uno o más caracteres completos.': 'Select one or more whole characters.',
    'La selección se cruza con una marca existente. Elimínala primero.':
        'The selection overlaps an existing mark. Remove that mark first.',
    'Al quitar |, el texto debe ser idéntico al de la frase. Conserva los espacios.':
        'Without the | marks, the text must match the line exactly. Keep the spaces.',
    'Este archivo no es un proyecto Lyric Candle compatible (schema 1 o 2).':
        'This file is not a compatible Lyric Candle project (schema 1 or 2).',
    'Posición guardada inválida.': 'Invalid saved position.',
    'Resolución inválida.': 'Invalid resolution.',
    'Configuración de proyecto inválida.': 'Invalid project settings.',
    'Tamaño de fuente inválido.': 'Invalid font size.',
    'La duración del proyecto debe ser positiva.': 'The project duration must be positive.',
    'Frase {0}: el final debe ser mayor que el inicio.': 'Line {0}: the end must be after the start.',
    'Frase {0}: termina después del proyecto.': 'Line {0}: ends after the project.',
    'Frase {0}: revisa el intervalo de repintado.': 'Line {0}: check the repaint interval.',
    'Frase {0}: destino de keyframes inválido.': 'Line {0}: invalid keyframe target.',
    'Frase {0}: keyframes fuera del intervalo, repetidos o con avance decreciente.':
        'Line {0}: keyframes outside the interval, repeated or with decreasing progress.',
    'Frase {0}: marcas superpuestas o fuera del texto ({1}).': 'Line {0}: overlapping marks or marks outside the text ({1}).',
    'Frase {0}: tiempo de sílaba fuera de la frase ({1}).': 'Line {0}: syllable time outside the line ({1}).',
    'Frase {0}: escala de sílaba inválida.': 'Line {0}: invalid syllable scale.',

    # --- lyrics import ------------------------------------------------------------------
    'Abre o pega un TXT con original y traducción alternados.':
        'Open or paste a TXT with alternating original and translation lines.',
    'Introduce al menos una frase original.': 'Enter at least one original line.',
    'Falta la letra o la duración del proyecto.': 'The lyrics or the project duration are missing.',
    'Amplía la duración del proyecto: hay demasiadas frases para ese intervalo.':
        'Increase the project duration: there are too many lines for that length.',
    'Original: {0} renglones. Traducción: {1}. Usa la misma cantidad, incluidos los vacíos intermedios.':
        'Original: {0} lines. Translation: {1}. Use the same number, including blank lines in between.',
    'El renglón {0} queda sin pareja. Cada original necesita su traducción en el siguiente renglón.':
        'Line {0} has no pair. Each original needs its translation on the next line.',
    'Bloque {0}, desde el renglón {1}: tiene {2} renglón(es); se esperan 2 (original y traducción). Corrige el bloque para evitar desplazar las parejas. Si faltan traducciones, utiliza «Dos columnas».':
        'Block {0}, from line {1}: it has {2} line(s); 2 are expected (original and translation). Fix the block so the pairs don\'t shift. If translations are missing, use "Two columns".',

    # --- media / export -----------------------------------------------------------------
    'El medio no tiene pista de video.': 'The media file has no video track.',
    'sin audio': 'no audio',
    'El contenedor {0} no se puede escribir; se usa MKV.': 'The {0} container can\'t be written; MKV is used.',
    'Esta compilación de FFmpeg no tiene un codificador compatible con ': 'This FFmpeg build has no encoder compatible with ',
    'FFmpeg no puede codificar {0}; se usa {1}.': 'FFmpeg can\'t encode {0}; {1} is used.',
    'ese códec': 'that codec',
    ' · audio {0} (copiado)': ' · audio {0} (copied)',
    'Forma de onda: instala FFmpeg o coloca ffmpeg.exe en tools/.': 'Waveform: install FFmpeg or put ffmpeg.exe in tools/.',
    'No se encontró FFmpeg. Coloca ffmpeg.exe y ffprobe.exe en tools/ o instálalos en PATH.':
        'FFmpeg was not found. Put ffmpeg.exe and ffprobe.exe in tools/ or install them on the PATH.',
    'El medio no existe. Vuelve a vincularlo con «Audio / video».': 'The media file doesn\'t exist. Link it again with "Audio / video".',
    'La imagen de fondo no se encuentra o no es compatible.': 'The background image is missing or not supported.',
    'El destino no puede ser el medio original.': 'The destination can\'t be the original media file.',
    'El destino no puede ser la imagen original.': 'The destination can\'t be the original image.',
    'El medio no tiene video; se exportó en MP4.': 'The media file has no video; it was exported as MP4.',
    'No se pudo decodificar el fotograma.': 'The frame could not be decoded.',
    'FFmpeg no está disponible para extraer el fotograma.': 'FFmpeg is not available to extract the frame.',
    'El medio no devolvió un fotograma de video.': 'The media file returned no video frame.',
    'No se pudo leer el audio: ': 'The audio could not be read: ',
    'Carga un video para utilizarlo como fondo.': 'Load a video to use it as the background.',
    'El fondo de video necesita ffprobe además de ffmpeg.': 'A video background needs ffprobe as well as ffmpeg.',
    'El medio cargado no tiene pista de video. Elige otro fondo.': 'The loaded media has no video track. Choose another background.',
    'Exportar como el video base necesita ffprobe además de ffmpeg.': 'Exporting like the base video needs ffprobe as well as ffmpeg.',
    'No se pudo decodificar el primer fotograma del video.': 'The first video frame could not be decoded.',
    'El video terminó con un error de decodificación.': 'The video ended with a decoding error.',

    # --- widgets ------------------------------------------------------------------------
    'Carga audio o video para ver la forma de onda.': 'Load audio or video to see the waveform.',
    'Elegir color': 'Choose color',
    'Clic: buscar. Arrastra los extremos de la frase seleccionada para ajustar sus tiempos.':
        'Click: seek. Drag the edges of the selected line to adjust its times.',
    'Doble clic: agregar keyframe. Arrastra un punto interior para moverlo. Clic en el gráfico: buscar ese instante.':
        'Double-click: add a keyframe. Drag an inner point to move it. Click the graph: seek to that moment.',
    'Disminuir': 'Decrease',
    'Aumentar': 'Increase',
    ' valor': ' value',

    # --- import dialog ------------------------------------------------------------------
    'Importar letra · original y traducción': 'Import lyrics · original and translation',
    'Carga tu letra y revisa las parejas antes de importar. Los tiempos se repartirán de forma provisional; después márcalos escuchando el audio.':
        'Load your lyrics and check the pairs before importing. Times are spread provisionally; then mark them while listening.',
    'Abrir TXT con original y traducción juntos…': 'Open TXT with original and translation together…',
    'Original de la primera frase\nTraducción de la primera frase\n\nOriginal de la segunda frase\nTraducción de la segunda frase':
        'Original of the first line\nTranslation of the first line\n\nOriginal of the second line\nTranslation of the second line',
    'Formato: original → traducción → línea vacía. También acepta parejas continuas sin líneas vacías. No modifica símbolos, puntuación ni espacios del texto.':
        'Format: original → translation → blank line. Continuous pairs without blank lines also work. Symbols, punctuation and spaces are kept as they are.',
    'TXT alternado': 'Alternating TXT',
    'Original: una frase por renglón': 'Original: one line per row',
    'Traducción: una frase por renglón (opcional)': 'Translation: one line per row (optional)',
    'Dos columnas': 'Two columns',
    'Reemplazar todas las frases actuales': 'Replace all current lines',
    'Importar parejas': 'Import pairs',
    'Abrir letra UTF-8': 'Open UTF-8 lyrics',
    'Texto (*.txt);;Todos los archivos (*)': 'Text (*.txt);;All files (*)',
    'Abrir TXT original': 'Open original TXT',
    'Abrir TXT traducción': 'Open translation TXT',
    'Original': 'Original',
    'Traducción': 'Translation',
    '{0} pareja(s) listas · tiempos provisionales, sin sincronizar con la canción.':
        '{0} pair(s) ready · provisional times, not yet synced to the song.',
    'Revisa la letra': 'Check the lyrics',
    'No se pudo leer': 'Could not read',

    # --- main window: transport and table ----------------------------------------------
    'Audio / video': 'Audio / video',
    'Todos': 'All',
    'Imágenes': 'Images',
    'Bucle': 'Loop',
    'Zoom frase': 'Zoom line',
    'Guías': 'Guides',
    'Vincular frase ↔ tiempo': 'Link line ↔ time',
    'Seleccionar una frase lleva el cabezal a su inicio. Buscar o reproducir selecciona la frase activa. En los huecos conserva la selección.':
        'Selecting a line moves the playhead to its start. Seeking or playing selects the active line. In gaps the selection is kept.',
    'FRASES': 'LINES',
    'FRASES · {0}': 'LINES · {0}',
    'Frase': 'Line',
    'Sílabas': 'Syllables',
    'Diseño': 'Design',
    'Efectos': 'Effects',
    'Keyframes': 'Keyframes',
    'Demo lista. Carga tu medio e importa la letra para comenzar.': 'Demo ready. Load your media and import the lyrics to begin.',
    'Marcar inicio y avanzar  [Ctrl+M]': 'Mark start and advance  [Ctrl+M]',
    'Marcar final  [Ctrl+F]': 'Mark end  [Ctrl+F]',
    'Repetir frase': 'Repeat line',
    'Lista → inicio de frase · Tiempo → frase activa': 'List → line start · Time → active line',
    '+ Frase': '+ Line',
    'Duplicar': 'Duplicate',
    'Eliminar': 'Delete',
    'Desplazar tiempos': 'Shift times',
    'Inicio': 'Start',
    'Final': 'End',
    'Pausar': 'Pause',
    'Reproducir': 'Play',
    '  [Espacio]': '  [Space]',

    # --- Line tab -----------------------------------------------------------------------
    'Frase seleccionada': 'Selected line',
    'Frase {0}': 'Line {0}',
    'Agrega una frase': 'Add a line',
    'Inicio (s)': 'Start (s)',
    'Final (s)': 'End (s)',
    'Repintar desde (+s)': 'Repaint from (+s)',
    'Hasta (+s)': 'Until (+s)',
    'Inicio y final son absolutos. El intervalo de repintado se cuenta desde el inicio de la frase.':
        'Start and end are absolute. The repaint interval is counted from the start of the line.',
    'Repintar durante toda la frase': 'Repaint over the whole line',
    'Aplicar cambios de texto': 'Apply text changes',
    'También puedes editar el texto en la tabla. Cambiar un texto elimina sus marcas de sílabas para evitar animar caracteres equivocados.':
        'You can also edit the text in the table. Changing a text removes its syllable marks so the wrong characters are never animated.',
    '⚠ Esta frase excede los márgenes. Reduce el tamaño, edita el texto o divídelo en otra frase.':
        '⚠ This line goes past the margins. Reduce the size, edit the text or split it into another line.',
    'La frase anterior conserva su texto sin aplicar. Vuelve a seleccionarla y pulsa «Aplicar cambios de texto».':
        'The previous line keeps its unapplied text. Select it again and press "Apply text changes".',
    'Aplica los cambios de texto para reanudar el seguimiento automático de frases.':
        'Apply the text changes to resume following lines automatically.',
    'El final debe ser mayor que el inicio.': 'The end must be after the start.',
    'Cambiar texto': 'Change text',
    'Este texto tiene marcas de sílabas. Cambiarlo eliminará sus marcas. ¿Continuar?':
        'This text has syllable marks. Changing it will remove them. Continue?',
    'Nueva frase': 'New line',
    'Segundos para todas las frases (negativo adelanta):': 'Seconds for all lines (negative moves them earlier):',
    'Desplazamiento inválido': 'Invalid shift',
    'Alguna frase quedaría antes de cero. Usa un desplazamiento menor.': 'Some line would start before zero. Use a smaller shift.',

    # --- Syllables tab ------------------------------------------------------------------
    'Ampliar editor de sílabas': 'Expand syllable editor',
    'Selecciona letras en el texto y pulsa «Marcar selección». Las marcas son rangos del texto; no agregan espacios visibles.':
        'Select letters in the text and press "Mark selection". Marks are ranges of the text; they don\'t add visible spaces.',
    'Marcar selección': 'Mark selection',
    'Repetir en frases': 'Repeat in lines',
    'Alternativa: vuel|ve a bri|llar': 'Alternative: shi|ning a|gain',
    'Crear marcas separadas con |': 'Create marks split with |',
    'Tiempos de animación relativos al inicio de la frase. Si usas keyframes para énfasis, la curva reprograma cuándo se alcanzan. Color, subida y escala vacíos heredan el estilo global. ✓ activa el énfasis.':
        'Animation times relative to the start of the line. If keyframes drive emphasis, the curve reschedules when they are reached. Empty color, lift and scale use the global style. ✓ turns emphasis on.',
    'Parte': 'Part',
    '+Inicio': '+Start',
    '+Fin': '+End',
    'Color': 'Color',
    'Subir': 'Lift',
    'Escala': 'Scale',
    'Estimar tiempos': 'Estimate timings',
    'Eliminar marcas': 'Delete marks',
    'Ajustar marcas a ataques del audio (±0.18 s)': 'Snap marks to audio attacks (±0.18 s)',
    'Color a selección': 'Color for selection',
    'Heredar global': 'Use global style',
    'Estimar reparte por texto. Ajustar al audio busca ataques cercanos: puede seguir instrumentos. No detecta voz ni separa sílabas. Doble clic en una parte: reproducir su momento.':
        'Estimate spreads times by text. Snapping looks for nearby attacks: it can follow instruments. It doesn\'t detect the voice or split syllables. Double-click a part to play its moment.',
    'Selecciona primero la sílaba o parte del texto en el recuadro superior.': 'First select the syllable or part of the text in the box above.',
    'Incluye el carácter completo junto con su acento.': 'Include the whole character together with its accent.',
    'La selección se cruza con una marca existente; elimínala primero.': 'The selection overlaps an existing mark; remove it first.',
    '{0} marca(s) creada(s). Revisa sus tiempos estimados.': '{0} mark(s) created. Check their estimated times.',
    'Conserva exactamente el texto y los espacios; agrega únicamente |.': 'Keep the text and spaces exactly; only add |.',
    'Marcas creadas con tiempos estimados; corrígelos escuchando.': 'Marks created with estimated times; fix them while listening.',
    'El intervalo debe quedar dentro de la frase y tener duración positiva.': 'The interval must stay inside the line and have a positive duration.',
    'Color inválido. Usa #RRGGBB o deja vacío para heredar.': 'Invalid color. Use #RRGGBB or leave it empty to use the global one.',
    'Subida: -100 a 160 px. Escala: 0.5 a 3.': 'Lift: -100 to 160 px. Scale: 0.5 to 3.',
    'Reparto estimado aplicado. No se ha analizado la voz.': 'Estimated timing applied. The voice was not analyzed.',
    'Audio pendiente': 'Audio pending',
    'Carga un medio y espera a que aparezca su forma de onda. Esta función necesita FFmpeg.':
        'Load a media file and wait for its waveform to appear. This feature needs FFmpeg.',
    'Ajuste orientativo': 'Approximate snapping',
    '{0} marca(s) ajustada(s) a ataques cercanos del audio.\nLos instrumentos también generan ataques: revisa escuchando.':
        '{0} mark(s) snapped to nearby audio attacks.\nInstruments also create attacks: check by ear.',
    'Sílabas · editor ampliado': 'Syllables · expanded editor',
    'Retroceder 0.1 s': 'Back 0.1 s',
    'Avanzar 0.1 s': 'Forward 0.1 s',
    'Bucle de la frase seleccionada': 'Loop the selected line',
    'Volver al editor principal': 'Back to the main editor',
    'Selecciona una o varias filas de sílabas (Ctrl / Shift).': 'Select one or more syllable rows (Ctrl / Shift).',
    'Color de énfasis para la selección': 'Emphasis color for the selection',

    # --- Design tab ---------------------------------------------------------------------
    'Distribución': 'Layout',
    'Una línea': 'One line',
    'Dos líneas': 'Two lines',
    'Posición': 'Position',
    'Texto principal': 'Main text',
    'Fuente': 'Font',
    'Pasa el mouse por una fuente para probarla. Clic para aplicar; Esc para cancelar.':
        'Hover over a font to try it. Click to apply; Esc to cancel.',
    'Vista previa: {0} · todavía sin aplicar': 'Preview: {0} · not applied yet',
    '⚠ Con esta fuente la frase excede los márgenes.': '⚠ With this font the line goes past the margins.',
    'Tamaño principal': 'Main size',
    'Tamaño secundario': 'Secondary size',
    'Margen (px)': 'Margin (px)',
    'Separación (px)': 'Spacing (px)',
    'Distancia vertical entre las dos líneas centradas.': 'Vertical distance between the two centered lines.',
    'Solo se usa con «Dos líneas» en posición «Centro». A izquierda/derecha cada línea va pegada a su margen (arriba y abajo).':
        'Only used with "Two lines" in the "Center" position. On the left/right each line sits on its own margin (top and bottom).',
    'Relleno inicial': 'Initial fill',
    'Relleno repintado': 'Repainted fill',
    'Contorno': 'Outline',
    'Grosor del contorno': 'Outline width',
    'Principal: arriba en dos líneas; secundario: abajo. Izquierda/derecha comparten margen; centrado comparte eje. Las animaciones nunca redistribuyen las letras.':
        'Main: on top with two lines; secondary: below. Left/right share a margin; centered lines share an axis. Animations never re-flow the letters.',
    'Superior izquierda': 'Top left',
    'Inferior izquierda': 'Bottom left',
    'Superior derecha': 'Top right',
    'Inferior derecha': 'Bottom right',
    'Centro': 'Center',
    'Izquierda · arriba / abajo': 'Left · top / bottom',
    'Derecha · arriba / abajo': 'Right · top / bottom',
    'Centro · principal arriba': 'Center · main on top',
    'Lienzo y fondo': 'Canvas and background',
    'Resolución': 'Resolution',
    'personalizada': 'custom',
    'FPS': 'FPS',
    'Duración (s)': 'Duration (s)',
    'Fondo': 'Background',
    'Degradado': 'Gradient',
    'Imagen': 'Image',
    'Video del medio': 'Media video',
    'Color base': 'Base color',
    'Elegir imagen de fondo': 'Choose background image',
    'Video base y exportación': 'Base video and export',
    'Usar resolución y FPS del video base': 'Use base video resolution and FPS',
    'El lienzo toma el tamaño y la velocidad de fotogramas del video cargado. Al cambiar de video se vuelven a leer.':
        'The canvas takes the size and frame rate of the loaded video. They are read again when you change the video.',
    'MP4 · H.264 + AAC': 'MP4 · H.264 + AAC',
    'Igual que el video base': 'Same as base video',
    '«Igual que el video base» usa su contenedor (AVI, MKV, MOV…), su códec de video, formato de píxel y bitrate, y copia su audio sin recodificar.':
        '"Same as base video" uses its container (AVI, MKV, MOV…), video codec, pixel format and bitrate, and copies its audio without re-encoding.',
    'Exportar como': 'Export as',
    'Sin medio': 'No media',
    'Medio: ': 'Media: ',
    'ninguno · reproducción de prueba sin audio': 'none · test playback without audio',
    'Sin medio. Carga un video para usar su resolución, FPS y formato.': 'No media. Load a video to use its resolution, FPS and format.',
    'Instala ffprobe para leer las propiedades del video base.': 'Install ffprobe to read the base video\'s properties.',
    'No se pudieron leer las propiedades del medio.': 'The media properties could not be read.',
    'Video base: ': 'Base video: ',
    '\nEl lienzo ({0}×{1} · {2} fps) no coincide con el video.': '\nThe canvas ({0}×{1} · {2} fps) doesn\'t match the video.',
    '\nLienzo ajustado a {0}×{1} (rotación, píxeles no cuadrados o límites de tamaño).':
        '\nCanvas adjusted to {0}×{1} (rotation, non-square pixels or size limits).',
    'No se pudo leer el video: ': 'The video could not be read: ',
    'Leer el video base necesita ffprobe (tools/ o PATH).': 'Reading the base video needs ffprobe (tools/ or PATH).',
    'Carga un video con «Audio / video» para usar su resolución y FPS.': 'Load a video with "Audio / video" to use its resolution and FPS.',
    'El video no informa su resolución.': 'The video doesn\'t report its resolution.',

    # --- Effects tab --------------------------------------------------------------------
    'Modo': 'Mode',
    '1 · Repintado': '1 · Repaint',
    '2 · Desvanecimiento': '2 · Fade',
    '3 · Avanzado por sílabas': '3 · Advanced by syllables',
    'Repintado conserva la frase hasta su salida. Desvanecimiento usa opacidad. Avanzado combina ambos con las partes marcadas en «Sílabas».':
        'Repaint keeps the line until it exits. Fade uses opacity. Advanced combines both with the parts marked in "Syllables".',
    'Repintar en modo avanzado': 'Repaint in advanced mode',
    'Desvanecer en modo avanzado': 'Fade in advanced mode',
    'Solapar la salida con la siguiente frase': 'Overlap the exit with the next line',
    'Entrada (s)': 'Fade in (s)',
    'Salida (s)': 'Fade out (s)',
    'Subida global (px)': 'Global lift (px)',
    'Escala global': 'Global scale',
    'Color de énfasis': 'Emphasis color',
    'Subida 0 y escala 1 desactivan el movimiento y el crecimiento. Cada marca puede sobrescribir estos valores. El énfasis regresa suavemente a la posición original.':
        'Lift 0 and scale 1 turn off movement and growth. Each mark can override these values. Emphasis eases back to the original position.',
    'Con solapado, la salida continúa después del final de la frase. Sin solapado, termina dentro de su intervalo. La duración del proyecto siempre recorta el resultado final.':
        'With overlap, the exit continues after the line ends. Without it, it finishes inside the line. The project duration always trims the final result.',
    'Abrir editor de sílabas': 'Open syllable editor',

    # --- Keyframes tab ------------------------------------------------------------------
    'Avance de la frase': 'Line progress',
    'Avance · frase {0}': 'Progress · line {0}',
    'Selecciona una frase': 'Select a line',
    'Selecciona una frase.': 'Select a line.',
    'Usar keyframes en esta frase': 'Use keyframes on this line',
    'Repintado y énfasis': 'Repaint and emphasis',
    'Solo repintado': 'Repaint only',
    'Solo énfasis': 'Emphasis only',
    'Eje horizontal: segundos desde el inicio. Eje vertical: avance. Dos puntos con el mismo % sostienen la animación; un tramo más inclinado la acelera. Entrada y salida conservan sus tiempos.':
        'Horizontal axis: seconds from the start. Vertical axis: progress. Two points with the same % hold the animation; a steeper segment speeds it up. Fade in and out keep their times.',
    'Bloquear tiempo (X)': 'Lock time (X)',
    'Arrastrar un punto solo cambia su avance (%).': 'Dragging a point only changes its progress (%).',
    'Bloquear avance (Y)': 'Lock progress (Y)',
    'Arrastrar un punto solo cambia su tiempo.': 'Dragging a point only changes its time.',
    'Cabezal {0:+.3f} s · avance {1:.1f}%': 'Playhead {0:+.3f} s · progress {1:.1f}%',
    '+ En el cabezal': '+ At playhead',
    'Sostener hasta aquí': 'Hold until here',
    '+Tiempo (s)': '+Time (s)',
    'Avance (%)': 'Progress (%)',
    'Extremo automático del intervalo de repintado.': 'Automatic end of the repaint interval.',
    'Eliminar puntos': 'Delete points',
    'Restablecer lineal': 'Reset to linear',
    'Los extremos 0% y 100% son automáticos: siguen «Repintar desde / Hasta» en Frase. Edita los puntos interiores en la tabla o arrástralos. Doble clic en el gráfico agrega un punto.':
        'The 0% and 100% ends are automatic: they follow "Repaint from / Until" in Line. Edit inner points in the table or drag them. Double-click the graph to add a point.',
    'Ejemplo: +1.0 s → 40%; +2.5 s → 40%; final +3.0 s → 100%. Sostiene entre 1.0 y 2.5 s y completa el resto en 0.5 s. La curva se comparte entre original y traducción.':
        'Example: +1.0 s → 40%; +2.5 s → 40%; end +3.0 s → 100%. It holds between 1.0 and 2.5 s and completes the rest in 0.5 s. The curve is shared by original and translation.',
    'Los tiempos deben ser únicos e interiores al intervalo. El avance debe ir de 0 a 100%, sin retroceder.':
        'Times must be unique and inside the interval. Progress must go from 0 to 100% without going back.',
    'Sitúa el cabezal dentro del intervalo de repintado de esta frase.': 'Place the playhead inside this line\'s repaint interval.',
    'Tiempo inválido o porcentaje fuera de 0 a 100.': 'Invalid time or a percentage outside 0 to 100.',

    # --- menus --------------------------------------------------------------------------
    'Proyecto': 'Project',
    'Nuevo': 'New',
    'Abrir': 'Open',
    'Guardar': 'Save',
    'Guardar como…': 'Save as…',
    'Importar letra': 'Import lyrics',
    'Exportar video': 'Export video',
    'Edición': 'Edit',
    'Deshacer': 'Undo',
    'Rehacer': 'Redo',
    'Marcar inicio y avanzar': 'Mark start and advance',
    'Marcar final': 'Mark end',
    'Opciones': 'Options',
    'Idioma': 'Language',
    'Automático (según el sistema)': 'Automatic (system)',
    'Abrir carpeta de datos (ajustes, autoguardado, registro)': 'Open data folder (settings, autosave, log)',
    'Ayuda': 'Help',
    'Guía rápida': 'Quick guide',
    'Cargar demo': 'Load demo',
    'Lyric Candle · Guía rápida': 'Lyric Candle · Quick guide',
    'Cerrar': 'Close',
    '{0}  ·  escuchar / marcar / animar': '{0}  ·  listen / mark / animate',
    '{0} ajuste(s) pendiente(s)': '{0} issue(s) to fix',

    # --- marking ------------------------------------------------------------------------
    'Todas las frases están iniciadas. Marca el final o selecciona una fila para volver a marcar.':
        'All lines have a start. Mark the end or select a row to mark again.',
    'Retrocede: la frase necesita al menos 0.05 s.': 'Go back: the line needs at least 0.05 s.',
    'La siguiente marca debe estar después de la anterior.': 'The next mark must come after the previous one.',
    'Última frase iniciada. Usa «Marcar final» al terminar.': 'Last line started. Use "Mark end" when it finishes.',
    'El final debe estar después del inicio.': 'The end must be after the start.',

    # --- media, files and recovery ------------------------------------------------------
    'Fotograma: ': 'Frame: ',
    'Preparando forma de onda…': 'Preparing waveform…',
    'Sin audio: puedes probar los efectos con el reloj de vista previa.': 'No audio: you can try the effects with the preview clock.',
    'Medio no encontrado. Vuelve a vincularlo con «Audio / video».': 'Media file not found. Link it again with "Audio / video".',
    'Cargar audio o video': 'Load audio or video',
    'Imagen de fondo': 'Background image',
    'Imagen no compatible': 'Unsupported image',
    'No se pudo leer esta imagen.': 'This image could not be read.',
    'Guardar proyecto': 'Save project',
    'Hay cambios sin guardar. ¿Quieres guardarlos?': 'There are unsaved changes. Do you want to save them?',
    'Abrir proyecto': 'Open project',
    'No se pudo abrir': 'Could not open',
    'el audio / video': 'the audio / video',
    'la imagen de fondo': 'the background image',
    'Archivo no encontrado': 'File not found',
    'No se encontró {0}:\n{1}\n\n¿Quieres buscarlo?': 'Could not find {0}:\n{1}\n\nDo you want to look for it?',
    'Buscar ': 'Find ',
    'Archivo vinculado. Guarda el proyecto para recordarlo.': 'File linked. Save the project to remember it.',
    'Mi-video.lyric.json': 'My-video.lyric.json',
    'Proyecto guardado en {0}. Los medios se vinculan; conserva sus archivos.':
        'Project saved at {0}. Media are linked; keep their files.',
    'No se pudo guardar': 'Could not save',
    'No se pudo crear el autoguardado. Guarda el proyecto manualmente.': 'The autosave could not be created. Save the project manually.',
    'Recuperar sesión': 'Recover session',
    'Hay un autoguardado de una sesión que se cerró inesperadamente ({0}). ¿Recuperarlo?':
        'There is an autosave from a session that closed unexpectedly ({0}). Recover it?',
    'No se pudo recuperar': 'Could not recover',
    '\n… y {0} más.': '\n… and {0} more.',
    'El proyecto tiene {0} ajuste(s) pendiente(s):\n\n{1}{2}\n\n¿Abrirlo de todos modos para corregirlo? La exportación seguirá bloqueada hasta resolverlos.':
        'The project has {0} issue(s) to fix:\n\n{1}{2}\n\nOpen it anyway to fix them? Exporting stays blocked until they are solved.',

    # --- export -------------------------------------------------------------------------
    'Ya hay una exportación en curso.': 'An export is already running.',
    'Hace falta FFmpeg': 'FFmpeg is needed',
    'Puedes editar y previsualizar. Para exportar, coloca ffmpeg.exe y ffprobe.exe en tools/ o instala FFmpeg en PATH.\n\nConsulta Ayuda → Guía rápida (F1).':
        'You can edit and preview. To export, put ffmpeg.exe and ffprobe.exe in tools/ or install FFmpeg on the PATH.\n\nSee Help → Quick guide (F1).',
    'Corrige los tiempos antes de exportar': 'Fix the timings before exporting',
    'Texto fuera de márgenes': 'Text outside the margins',
    'Hay frases que exceden los márgenes y pueden cortarse. ¿Exportar de todos modos?':
        'Some lines go past the margins and may be cut. Export anyway?',
    'Mi-video-lyrics': 'My-lyric-video',
    'Formato del video base': 'Base video format',
    'Para exportar como el video base hace falta ffprobe (junto a ffmpeg en tools/ o en PATH) y un medio legible.':
        'Exporting like the base video needs ffprobe (next to ffmpeg in tools/ or on the PATH) and a readable media file.',
    'Video {0} (*{1})': '{0} video (*{1})',
    'Generando video…': 'Rendering video…',
    'Cancelar': 'Cancel',
    'Exportar · Lyric Candle': 'Export · Lyric Candle',
    'Video exportado': 'Video exported',
    'Video generado correctamente:\n': 'Video created successfully:\n',
    '\n\nFormato: {0}': '\n\nFormat: {0}',
    'No se pudo exportar': 'Could not export',
    'Exportación cancelada. El archivo anterior se conserva.': 'Export cancelled. The previous file is kept.',
    'Exportación activa': 'Export running',
    'Cancela la exportación o espera a que termine antes de cerrar.': 'Cancel the export or wait for it to finish before closing.',
    ' · video': ' · video',

    # --- errors -------------------------------------------------------------------------
    'Lyric Candle · error': 'Lyric Candle · error',
    '{0}\n\nSe guardó el detalle en:\n{1}': '{0}\n\nDetails were saved to:\n{1}',
}
