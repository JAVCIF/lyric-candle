# Lyric Candle — Alpha 0.2.6

Editor de escritorio para crear video lyrics con una o dos líneas, traducción, repintado, desvanecimiento y énfasis por sílabas. Proyecto independiente de Sonic Candle. Interfaz en español e inglés.

[Inicio en español](../README.es.md) · [English user guide](USER_GUIDE.en.md) · [Desarrollo](DEVELOPMENT.es.md)

La 0.2.4 protege el texto sin aplicar guardándolo como borrador, corrige la exportación y vista pausada de videos con píxeles no cuadrados, y reconoce la orientación del video al adoptar su resolución. Puedes abrir tus proyectos anteriores.

## Abrir en Windows

1. Extrae **toda** la carpeta del ZIP. No ejecutes los archivos desde dentro del ZIP.
2. Necesitas **Python 3.10–3.13 de 64 bits**. Se recomienda Python 3.12, disponible en https://www.python.org/downloads/windows/ . Si usas el instalador, incluye el lanzador `py`.
3. Ejecuta **scripts\windows\INSTALAR.bat**. Crea un entorno `.venv` dentro de la carpeta y descarga la dependencia PySide6. La primera instalación requiere internet.
4. Ejecuta **scripts\windows\INICIAR.bat**. La aplicación abre una demo de 12 segundos.
5. Si no abre, ejecuta **scripts\windows\DIAGNOSTICO.bat** y conserva el mensaje. Los errores de arranque también se escriben en `Lyric-Candle-startup-error.log` dentro de tu carpeta de usuario.

Este paquete contiene **código fuente y lanzadores**, no un EXE precompilado. `scripts\windows\CREAR_EXE.bat` permite intentar la compilación en Windows con PyInstaller; ese proceso no se ejecutó aquí. Distribuye la carpeta que genere, completa.

### FFmpeg: exportación y forma de onda

La edición y vista previa pueden abrir sin FFmpeg instalado por separado. Para generar MP4, dibujar la forma de onda y ajustar marcas a ataques del audio:

- Coloca **ffmpeg.exe y ffprobe.exe** dentro de `tools/`, o instálalos en el PATH.
- Si compilaste el EXE con `scripts\windows\CREAR_EXE.bat`, usa la carpeta `tools\` junto a `LyricCandle.exe` (créala si no existe).
- Descarga y enlaces a compilaciones: https://ffmpeg.org/download.html . Necesitas una compilación con `libx264` y AAC.
- No se incluyen binarios de FFmpeg. Si acabas de modificar PATH, vuelve a abrir la aplicación.

En Linux/macOS: crea un entorno de Python, instala `requirements.txt` y ejecuta `python main.py`. El paquete y sus scripts están orientados a Windows; las pruebas automatizadas se ejecutaron en Linux sin pantalla.

## Probar sin preparar archivos

Al abrir encontrarás tres frases de ejemplo, con marcas independientes en ambos textos. La letra y el audio de demo son originales de este paquete. El audio es un ritmo sintético **sin voz**; sirve para probar el reloj y los efectos, no para validar reconocimiento de canto.

- `examples/Demo.mp4`: muestra del resultado exportado, reproducible fuera de la aplicación.
- `examples/Demo.lyric.json`: proyecto editable.
- `examples/Demo.wav`: audio de prueba.

Reproduce y cambia los modos en **Efectos**. En **Sílabas**, selecciona una fila y modifica su color, subida o escala. «Ampliar editor de sílabas» abre una ventana con vista previa y controles de reproducción.

## Crear tu video

### 1. Medio, fondo y lienzo

Pulsa **Nuevo**, después **Audio / video**. Se usa un único medio: audio, o un video con su propio audio. Si eliges video, su imagen también se ofrece como fondo.

En **Diseño** elige fondo degradado, imagen o video del medio. Las imágenes y videos se ajustan conservando su proporción, con espacio libre cuando hace falta. Define resolución, FPS y duración. El cambio de resolución conserva los tamaños en píxeles: revisa fuente y márgenes después de cambiarla.

### 2. Original y traducción

Pulsa **Importar letra**. Ahora hay dos formatos, ambos con vista previa antes de confirmar:

- **TXT alternado** (opción inicial): abre tu archivo completo o pégalo. Cada bloque contiene original, traducción y una línea vacía. También se aceptan parejas consecutivas sin separadores. El importador conserva símbolos y puntuación; no adivina el idioma. Si un bloque queda incompleto o tiene más de dos renglones, detiene la importación e indica dónde revisarlo para evitar correr todas las parejas siguientes.
- **Dos columnas**: pega una frase por renglón en cada columna, o abre dos TXT UTF-8 separados. Ambas columnas deben tener la misma cantidad de renglones; puedes dejar vacía toda la traducción. Usa este formato si algunas frases no tienen traducción.

La vista previa muestra las parejas y su cantidad. Confirma con **Importar parejas**. Los tiempos siguen siendo provisionales hasta sincronizar con el audio.

La importación propone intervalos iguales a lo largo del proyecto. Son un punto de partida. También puedes agregar, duplicar y eliminar frases desde la tabla. Importar sin reemplazar conserva las frases anteriores y agrega otras con sus intervalos estimados; revisa los posibles solapamientos.

Distribuciones:

- **Una línea:** superior/inferior izquierda, superior/inferior derecha o centro. Puedes mostrar original o traducción como principal. Solo se usa el tamaño principal.
- **Dos líneas:** izquierda o derecha con una arriba y otra abajo; o ambas en el centro, con la principal encima. Tamaños principal/secundario independientes.
- Izquierda comparte margen izquierdo; derecha comparte margen derecho; centro comparte eje. Las longitudes diferentes no alteran esos anclajes.

La frase nunca se divide automáticamente en renglones. Si no cabe, aparece un aviso. Reduce su tamaño o repártela en frases distintas. Las guías de márgenes solo aparecen en el editor; no se exportan.

### 3. Marcar tiempos escuchando

1. Selecciona la primera fila de la tabla.
2. Reproduce desde antes de la primera frase.
3. Pulsa **Ctrl+M** al comenzar cada frase. Marca su inicio y prepara la siguiente; la nueva marca también cierra la frase anterior.
4. Después de iniciar la última frase, pulsa **Ctrl+F** al terminar de cantarla.
5. Corrige los tiempos en la tabla o en la pestaña **Frase**. Se admiten segundos o `mm:ss.mmm` en la tabla.

Seleccionar una fila reinicia el marcado desde esa fila. «Marcar final» se aplica a la última iniciada en una secuencia de marcado; si seleccionaste otra fila, se aplica a la selección.

Haz clic en la forma de onda para buscar. Arrastra cerca del borde de inicio/final de la frase seleccionada y suelta para aplicar el cambio. «Zoom frase» amplía esa región y mantiene fija la selección. Mientras está activo, Ctrl+M ajusta solo el inicio y Ctrl+F solo el final de esa frase, sin avanzar ni cerrar otras filas. El límite opuesto se conserva y las marcas/keyframes se reajustan. Desactívalo para el marcado secuencial. «Repetir frase» y «Bucle» facilitan escucharla varias veces. Puedes bajar la reproducción a 0.5× o 0.75×; la exportación siempre sale a velocidad normal.

**Qué frase cambia Ctrl+M**: siempre lo indica ▶ en la columna #, y cada marca se confirma en la barra de estado («Frase 3: inicio en 00:09.000.»). Fuera de una secuencia de marcado, Ctrl+M actúa sobre la fila seleccionada, también si la eligió «Vincular frase ↔ tiempo». Durante una secuencia continúa con la siguiente frase.

**Tiempos provisionales.** La letra importada y las frases nuevas empiezan con tiempos de relleno: en la tabla se ven atenuados y en cursiva, y en la onda con bordes discontinuos. «Vincular frase ↔ tiempo» los ignora: en la primera pasada la selección no salta a frases que todavía no se cantan, y elegir esas filas no mueve el cabezal. Marcar o editar su inicio o final las confirma. Los proyectos de versiones anteriores cuentan como ya sincronizados.

En la pestaña **Frase**, el intervalo de repintado se expresa en segundos **desde su inicio**. Al cambiar la duración de una frase, sus marcas y su intervalo de repintado se reescalan proporcionalmente. «Desplazar tiempos» mueve todas las frases conservando sus intervalos internos.

### 4. Elegir los efectos

- **1 · Repintado:** relleno inicial y relleno repintado; el color del contorno se mantiene. El relleno avanza por la frase durante el intervalo indicado. El texto permanece hasta su final.
- **2 · Desvanecimiento:** entrada y salida por opacidad. Cero segundos permite una entrada o salida inmediata.
- **3 · Avanzado:** combina repintado y/o desvanecimiento con énfasis en las unidades que marques. Las unidades pueden subir, crecer y cambiar de color mientras están activas, y después regresan a su posición/tamaño originales.

El énfasis no redistribuye el texto: cada fragmento conserva su posición base. Subida `0` desactiva el desplazamiento; escala `1` conserva el tamaño.

«Solapar la salida» prolonga el desvanecimiento después del final de la frase, permitiendo su coexistencia con la siguiente. Sin esa opción, se desvanece dentro del intervalo. El video se recorta a la duración del proyecto: deja tiempo al final si quieres ver la última salida completa.

### 5. Marcar sílabas, palabras o fragmentos

En **Sílabas**, elige original o traducción. Tienen marcas independientes aunque compartan el intervalo de frase.

- Selecciona las letras en el recuadro y pulsa **Marcar selección**.
- O añade `|` entre las partes en el campo alternativo y pulsa **Crear marcas separadas con |**. Ejemplo: `Vuelve a bri|llar`. Al quitar los separadores, el texto debe quedar exactamente igual, incluidos los espacios. Cada parte no vacía se convierte en una marca; desactiva su casilla si no quieres enfatizarla.
- Las marcas no pueden superponerse dentro del mismo texto. Elimina la anterior si quieres sustituirla por otra selección.
- **Repetir en frases** marca las coincidencias exactas del texto seleccionado en todas las frases del mismo idioma. Omite las que ya se cruzan con otra marca. Sus tiempos son estimaciones, no tiempos vocales copiados.

La tabla usa tiempos relativos al inicio de la frase. Edita `+Inicio` y `+Fin` para sostener una vocal o acortar un acento. Doble clic en la columna **Parte** reproduce desde su inicio.

El color global se configura en **Efectos**. Las celdas de color/subida/escala vacías heredan el global. Puedes sobrescribir cada marca; selecciona varias filas con Ctrl/Shift y usa **Color a selección**. «Heredar global» borra sus ajustes individuales. El color de énfasis se usa mientras el efecto está activo; al terminar vuelve al relleno que corresponda.

### 6. Asistencia automática disponible

Hay dos ayudas distintas, ambas corregibles:

1. **Estimar tiempos:** reparte las marcas según su posición y longitud de texto dentro del intervalo de repintado. No separa sílabas ni escucha la voz.
2. **Ajustar marcas a ataques del audio:** mueve sus inicios hacia aumentos de amplitud cercanos, dentro de ±0.18 s. Conserva aproximadamente su duración y el orden de las marcas. Necesita que la forma de onda esté lista. **Puede seguir batería o instrumentos en vez del canto.** Úsalo después de aproximar los tiempos y verifica escuchando.

No hay reconocimiento automático de letras cantadas ni alineación vocal con IA en esta alpha. El flujo principal es marcar escuchando y refinar.

### 7. Guardar y exportar

- Pulsa **Aplicar cambios de texto** después de editar los cuadros de la pestaña Frase. Cambiar un texto con marcas pide confirmación y elimina únicamente las marcas de ese texto. La edición directa en la tabla se aplica al confirmar la celda.
- **Guardar** conserva texto, tiempos, colores, marcas y diseño en `.lyric.json`. Los medios se vinculan; no se incrustan. Desde la 0.2.3 se guarda la ruta relativa y la absoluta: puedes mover solo el `.lyric.json`, o el proyecto junto con sus medios, o dejar el medio junto al proyecto. Si aun así no aparece, al abrir se ofrece buscarlo.
- Hay deshacer/rehacer y autoguardado cada 20 segundos después de un cambio, incluso al escribir texto sin aplicar. Desde la 0.2.4, **Guardar también conserva esos borradores**, de la frase actual y de otras filas. Al reabrir o recuperar la sesión reaparecen en la pestaña Frase; el texto aplicado y las marcas se mantienen intactos hasta que pulses Aplicar. El contador de la cabecera indica cuántas frases tienen texto pendiente. Si cierras con cambios sin guardar, se pregunta si quieres guardarlos.
- Antes de exportar, aplica los borradores pendientes. Si queda alguno, la app te lleva a una de esas frases para revisarlo. La vista previa muestra el texto aplicado.
- **Exportar video** genera por defecto MP4 con H.264 y, cuando hay audio, AAC. Usa la misma composición que la vista previa. No incluye las guías.
- En **Diseño → Video base y exportación**, «Exportar como: Igual que el video base» usa el contenedor (AVI, MKV, MOV, WebM…), el códec de video, el formato de píxel y el bitrate del video cargado, y copia su audio sin recodificar. Si FFmpeg no puede escribir ese códec o contenedor, usa uno compatible y lo indica al terminar.
- Puedes cancelar una exportación. Se escribe primero a un temporal: un fallo o cancelación conserva el archivo anterior.

Los videos con píxeles no cuadrados se convierten a píxeles cuadrados antes de ajustar el fondo al lienzo. La resolución del video base toma en cuenta la rotación de 90°, 180° o 270°. Al abrir un proyecto que ya tenía «Usar resolución y FPS del video base» activado, se vuelven a leer esas propiedades para corregir un tamaño antiguo; guarda el proyecto para conservarlo. Se mantienen los límites de tamaño del editor.

Los borradores son una función de la 0.2.4: utiliza esta versión o una posterior para conservarlos al volver a guardar. Las versiones anteriores no los reconocen.

## Alcance de esta alpha

- App de escritorio en español e inglés, código fuente; el arranque y los scripts de Windows requieren probarse en tu equipo.
- Sin reconocimiento de canto, división automática lingüística en sílabas, glow/partículas ni animaciones de trayectorias personalizadas.
- Un único medio por proyecto, sin mezclador de pistas ni audio externo separado de un fondo de video.
- Importación de texto pegado o TXT; sin importadores SRT/ASS/LRC en esta versión.
- Las fuentes dependen del equipo. Para japonés utiliza una fuente instalada con esos caracteres, por ejemplo una de tus fuentes japonesas habituales. Mantén la misma fuente al mover el proyecto.
- La reproducción depende de los formatos admitidos por Qt Multimedia. Los errores del medio se muestran en la barra inferior.
- Los solapamientos de frases son intencionalmente posibles. La duración insuficiente o los intervalos inválidos bloquean la exportación hasta corregirlos.

## Pruebas incluidas

Con las dependencias y FFmpeg instalados, ejecuta desde la carpeta del proyecto:

```sh
python -m unittest discover -s tests -v
```

Las pruebas cubren tiempos, Unicode, guardado y reapertura, escalado de marcas, alineación, layouts/modos, edición, deshacer, ajuste a ataques, ventana ampliada, forma de onda, MP4 con audio, fondo de video sin audio, fallos y cancelación. La suite utiliza la plataforma Qt sin pantalla y no sustituye la prueba de reproducción audible en Windows.

## Alpha 0.2: vincular selección y tiempo

El check **Vincular frase ↔ tiempo**, debajo de los controles de reproducción, permite:

- Seleccionar una fila: el cabezal va al inicio de esa frase. Volver a hacer clic en la misma fila la reinicia.
- Buscar en la onda, mover el deslizador o reproducir: la lista selecciona la frase activa, conservando el tiempo exacto que elegiste.
- En huecos sin letra se conserva la selección. Si hay frases solapadas, conserva la seleccionada mientras siga activa; en caso contrario elige la activa que empezó más recientemente.
- Desactivarlo permite revisar una fila sin mover la reproducción. El programa recuerda el estado del check entre sesiones.
- El avance automático de selección durante el marcado con Ctrl+M no adelanta el audio ni reinicia la secuencia de marcas.
- Si estás escribiendo texto que aún no aplicaste, el seguimiento automático espera a que pulses **Aplicar cambios de texto** para no descartarlo.

## Alpha 0.2: keyframes de avance por frase

Selecciona una frase y abre la pestaña **Keyframes**. Aquí controlas **cuándo alcanza cada porcentaje de su animación**. El eje horizontal son segundos desde el inicio de esa frase; el vertical es avance de 0 a 100%.

1. Activa **Usar keyframes en esta frase**. Elige **Repintado y énfasis**, **Solo repintado** o **Solo énfasis**.
2. Busca el punto donde cambia el ritmo de la frase y pulsa **+ En el cabezal**. Se agrega un punto con el avance actual; puedes editar su porcentaje en la tabla.
3. Ve hasta el final de la palabra sostenida y pulsa **Sostener hasta aquí**. Repite el porcentaje del punto anterior, creando un tramo horizontal. Necesitas haber agregado un punto donde quieras comenzar esa espera.
4. Agrega o mueve otros puntos para que lo que falta avance más rápido o más lento. Puedes arrastrarlos en el gráfico; doble clic en el gráfico agrega un punto directamente.
5. Reproduce o usa el bucle para comprobar el resultado. Desactiva el check de keyframes para comparar con el avance lineal sin borrar la curva.

Ejemplo para una frase cuyo intervalo de repintado va de 0 a 4 segundos:

| Tiempo desde inicio | Avance |
|---|---|
| 0.0 s | 0% (automático) |
| 1.0 s | 40% |
| 3.0 s | 40% |
| 4.0 s | 100% (automático) |

El repintado llega al 40% en un segundo, se sostiene durante dos segundos y completa el 60% restante durante el último segundo. Si la curva también afecta al énfasis, sostendrá su movimiento y color en el estado alcanzado.

Los extremos 0% y 100% siguen **Repintar desde / Hasta** en la pestaña Frase. Para completar la animación antes, acorta **Hasta**. Los puntos interiores deben tener tiempos distintos y avanzar sin retroceder; se permiten porcentajes iguales para las pausas. La interpolación entre puntos es lineal. **Restablecer lineal** elimina los puntos interiores; los extremos son automáticos y no se eliminan.

La curva se aplica a original y traducción con el mismo porcentaje. Sus marcas de sílabas siguen siendo independientes. Cuando la curva afecta al énfasis, los tiempos de la tabla Sílabas representan tiempos de animación anteriores a la curva; el programa los reprograma para respetar sus pausas y aceleraciones. El doble clic en una sílaba busca el primer instante real en que se alcanza su inicio.

La aparición y el desvanecimiento mantienen sus tiempos reales. Los keyframes no alargan la frase ni cambian la velocidad del audio. Cambiar la duración de la frase reescala los tiempos de sus puntos; cambiar el intervalo de repintado los redistribuye proporcionalmente dentro de ese intervalo.

Los puntos, su activación y su destino se guardan en el proyecto y forman parte de deshacer/rehacer. **La 0.2 abre los proyectos de las alphas anteriores. Los nuevos guardados usan schema 2: ábrelos con 0.2 o posterior para conservar los keyframes.** Las versiones antiguas rechazan este formato en vez de borrar la curva.

Abre `examples/Demo-Keyframes.lyric.json` para probar una pausa entre los segundos 1 y 3. `examples/Demo-Keyframes.mp4` muestra su exportación. Es una demostración con audio sintético, sin voz.

## Alpha 0.2.1: probar fuentes al pasar el mouse

En **Diseño → Fuente**, abre la lista o escribe parte del nombre para buscar. Al pasar el mouse por una fuente, las letras de la vista previa se dibujan con esa fuente **sin aplicarla todavía**. También se puede recorrer la lista con el teclado.

- Haz clic en la fuente o confírmala para aplicarla al proyecto.
- Pulsa **Esc** o cierra la lista sin elegir para volver a la fuente anterior. Si sales con el mouse de la lista, termina la prueba temporal.
- Probar fuentes no marca el proyecto como modificado y no crea entradas en deshacer. Confirmar una elección crea un único cambio que puedes deshacer.
- Guardar o exportar utiliza la fuente confirmada, no la que estuvieras probando temporalmente.
- Si en ese instante no hay letra visible, busca una frase o activa la selección vinculada para situarte sobre ella. Las letras que ya estén incrustadas en un video de fondo no son editables por el selector de fuentes.

## Alpha 0.2.1: reabrir video en el fotograma guardado

**Guardar** y el autoguardado conservan también la posición del cabezal. Al volver a abrir el proyecto se restaura esa posición y se prepara su fotograma de video en segundo plano, sin tener que pulsar Play. La reproducción queda detenida.

Las búsquedas con el video pausado también actualizan el fotograma. Si haces varias seguidas, se descartan las respuestas antiguas para no volver a una imagen anterior. El último fotograma se conserva cuando el cabezal está justo al final del video.

FFmpeg se usa para la extracción en segundo plano cuando está disponible. Si no está, se utiliza el decodificador de Qt con preparación silenciada y regreso a pausa en el punto solicitado. No hace falta instalar una dependencia nueva para esta actualización.

**Los proyectos de versiones anteriores no tenían guardada la posición**: se abren en el segundo 0, con su primer fotograma. Sitúate donde quieras y vuelve a guardarlos con 0.2.1 para que recuerden ese punto. La posición de vista no modifica los tiempos de la letra ni la duración del MP4 exportado.

Puedes abrir `examples/Demo-Video-Pausado.lyric.json`: utiliza el MP4 de demostración y está guardado en el segundo 2. Sus letras ya están incrustadas en el video; es un ejemplo de restauración del fotograma, no de edición del texto.

## Alpha 0.2.2: botones numéricos − y +

Los campos numéricos ahora muestran dos botones explícitos: **− a la izquierda y + a la derecha**. Reemplazan los indicadores pequeños que podían verse como puntos. Se utilizan en Diseño y en los otros controles numéricos del editor.

Puedes hacer clic para subir/bajar un paso, mantener pulsado para repetir, escribir el valor directamente o usar las flechas del teclado. Los botones respetan los límites y se desactivan cuando el campo no se puede editar. Se conservan los pasos decimales y el separador de tu configuración regional.

## Alpha 0.2.3: correcciones de marcado y texto

- **Ctrl+M** ya no deforma los tiempos de sílabas ni keyframes cuando el final provisional de la frase queda antes de la marca (por ejemplo, tras importar una canción con intro).
- El texto que escribes en **Frase** sin aplicar se conserva aunque marques, arrastres bordes, deshagas o cambies el diseño. Si cambias de fila, queda como borrador de esa frase hasta que vuelvas a ella y lo apliques.
- Con **Vincular frase ↔ tiempo**, mientras marcas con Ctrl+M la selección muestra la frase que iniciará la siguiente marca. Pulsa Ctrl+F o selecciona una fila para volver al seguimiento normal.
- «Marcar selección» y «Repetir en frases» proponen tiempos dentro del intervalo de repintado.
- «+ Frase» se inserta en la tabla según su tiempo de inicio.
- «Ajustar marcas a ataques del audio» tiene en cuenta los keyframes de énfasis.
- Mantener pulsado − o + (o varios clics seguidos en el mismo campo) crea un solo paso de deshacer.
- Los espacios duros se conservan al editar el texto de una frase.
- Si al abrir un proyecto hay tiempos o marcas por revisar, se listan y puedes abrirlo igualmente para corregirlos; exportar sigue bloqueado hasta resolverlos.
- Cada ventana tiene su propio autoguardado: al iniciar solo se ofrecen los de sesiones cerradas inesperadamente.
- La forma de onda conserva los picos cortos y muestra una guía al arrastrar los bordes de la frase.
- Doble clic en la columna Color de Sílabas abre el selector de color.

## Alpha 0.2.3: video base, rutas y keyframes

- **Diseño → Video base y exportación → «Usar resolución y FPS del video base»**: el lienzo toma el tamaño y la velocidad del video cargado, incluidas velocidades como 23.976 o 29.97. Resolución y FPS quedan bloqueados mientras está activo; al cargar otro video se vuelven a leer. Los videos con píxeles no cuadrados usan su tamaño de visualización, y el lienzo se mantiene entre 320×240 y 3840×2160.
- **«Exportar como: Igual que el video base»**: exporta con el formato del video cargado (ver «Guardar y exportar»). Lo ideal es combinarlo con el check anterior para que también coincidan resolución y FPS.
- **Resolución** ya muestra el valor del proyecto (antes aparecía vacía).
- **Separación** solo se usa con «Dos líneas» en posición «Centro»; en los demás casos se desactiva, porque a izquierda/derecha cada línea va pegada a su margen.
- **Keyframes → «Bloquear tiempo (X)» / «Bloquear avance (Y)»**: al arrastrar un punto solo cambia el otro eje. El programa recuerda estas casillas. Hacer clic en un punto sin moverlo ya no crea un paso de deshacer.
- Las rutas guardadas por versiones anteriores solo eran relativas: si ya moviste un proyecto viejo, ábrelo, busca el medio cuando lo pida y guárdalo una vez.

## Alpha 0.2.3: idioma, guía rápida y versión portable

- **Idioma**: Lyric Candle abre en español si Windows está en español y en inglés en cualquier otro idioma. Cámbialo en **Opciones → Idioma** (Automático / Español / English); se aplica al reiniciar.
- **Guía rápida**: **Ayuda → Guía rápida** o **F1**. Resume el flujo completo, los atajos y dónde se guardan tus datos.
- **Instalada o portable**: por defecto, ajustes, autoguardado y registro se guardan en tu carpeta de usuario (`%APPDATA%\JAVCIF\LyricCandleAlpha`). Para usarla portable, crea un archivo vacío `portable.txt` junto a `LyricCandle.exe` (o junto a `main.py` si ejecutas el código): desde el siguiente inicio todo va a la carpeta `data` al lado. **Opciones → Abrir carpeta de datos** te lleva a la ubicación en uso.
