# Alpha 0.2.3

- Ctrl+M conserva la duración provisional de la frase al marcar su inicio; ya no la reduce a 0.1 s. Las sílabas, los keyframes y el intervalo de repintado se reescalan una sola vez, al cerrar la frase, sin deformarse. Cerca del final del proyecto la frase se recorta a la duración del proyecto.
- El texto escrito sin aplicar en la pestaña Frase ya no se borra al marcar, arrastrar bordes en la onda, deshacer o cambiar el diseño.
- Al cambiar de fila con texto sin aplicar, se conserva como borrador de esa frase; al volver a seleccionarla reaparece para aplicarlo. Abrir, crear, recuperar o importar reemplazando descarta los borradores.
- Los espacios duros (U+00A0) ya no cuentan como cambios sin aplicar: el seguimiento vinculado no se detiene y «Aplicar» no pide borrar marcas si no editaste nada.
- Con «Vincular frase ↔ tiempo», durante una secuencia de Ctrl+M la tabla y el panel muestran la frase que iniciará la siguiente marca. El seguimiento normal vuelve tras Ctrl+F o al seleccionar una fila.

## Correcciones de prioridad media

- Editar una frase con espacios duros (U+00A0) los conserva al aplicar; antes se convertían en espacios normales.
- «Marcar selección» y «Repetir en frases» estiman los tiempos dentro del intervalo de repintado, con el mismo reparto que «Estimar tiempos». La sílaba marcada ya no se enfatiza después de que el repintado haya pasado.
- «+ Frase» inserta la frase según su tiempo de inicio, no al final de la lista, para que Ctrl+M y la navegación vinculada la recorran en orden.
- «Ajustar marcas a ataques del audio» respeta los keyframes que afectan al énfasis: convierte los tiempos al reloj real, busca el ataque y los devuelve al reloj de animación.
- Deshacer agrupa los cambios seguidos del mismo control dentro de un segundo, como mantener pulsado − o +. Antes cada paso ocupaba una entrada y podía agotar las 80 del historial.

## Correcciones de prioridad baja

- EXE: FFmpeg se busca también en `tools\` junto a `LyricCandle.exe`, como indica el LEEME (antes solo dentro de `_internal\`).
- Ctrl+M y Ctrl+F leen el reloj de reproducción en el instante de la tecla, sin el retraso de hasta 33 ms del refresco de pantalla.
- Forma de onda: cada columna muestra el pico más alto de su tramo, así los ataques cortos no desaparecen en canciones largas. Al arrastrar un borde se ve una guía con el tiempo antes de soltar.
- Video: los fotogramas solo se convierten a imagen cuando el fondo es «Video del medio», y como máximo unas 30 veces por segundo durante la reproducción.
- Abrir o recuperar un proyecto con tiempos o marcas por revisar ya no lo rechaza: muestra la lista y ofrece abrirlo para corregirlo; la exportación sigue bloqueada hasta resolverlos. Deshacer/rehacer nunca rechaza sus propios estados.
- Posición o texto principal incoherentes en un archivo editado a mano se ajustan al valor válido más cercano.
- Cada ventana abierta autoguarda en su propio archivo protegido por un bloqueo. Cerrar una ya no borra el autoguardado de otra; al iniciar solo se ofrecen los de sesiones que se cerraron inesperadamente (incluido el `recovery.lyric.json` de versiones anteriores).
- Espacio reproduce/pausa también con el foco en un desplegable normal (velocidad, modo…); solo se reserva para campos de texto y la búsqueda de fuente.
- Doble clic en la columna Color de Sílabas abre solo el selector de color. En +Inicio, +Fin, Subir y Escala el doble clic sigue editando; también se puede escribir directamente.

## Interfaz

- El botón de reproducción usa iconos dibujados de play y pausa (nítidos en pantallas HiDPI) en lugar de los caracteres ▶ / Ⅱ. El editor ampliado de sílabas usa el mismo botón.

## Video base, rutas y keyframes

- Corregido: el desplegable Resolución aparecía siempre vacío (comparaba tuplas por identidad).
- Nuevo: «Usar resolución y FPS del video base», con FPS no estándar (23.976, 29.97…) y tamaño de visualización para píxeles no cuadrados.
- Nuevo: «Exportar como: Igual que el video base» (contenedor, códec, formato de píxel, bitrate y etiqueta como XVID; audio copiado). Si no es posible, alternativa compatible con aviso. «Exportar MP4» pasa a llamarse «Exportar video» y propone guardar junto al medio.
- Proyectos movidos: se guarda también la ruta absoluta de medio e imagen; al abrir se prueba la ruta relativa, luego la absoluta y luego un archivo con el mismo nombre junto al proyecto. Si falta, se ofrece buscarlo.
- Separación solo se activa con dos líneas centradas, con una explicación en su tooltip.
- Keyframes: casillas para bloquear tiempo (X) o avance (Y) al arrastrar; un clic sin mover no crea paso de deshacer.
- Los campos desactivados se ven atenuados en el tema oscuro.

## Identidad

- Icono propio: la insignia de Sonic Candle (aro negro, disco con degradado) con una llama de vela que repinta una línea de letra. Se usa como icono de ventana, de la barra de tareas de Windows y del EXE (`lyric_candle/assets/logo.svg`, `logo.ico`, `logo-256.png`).
- Marca dentro de la app adaptada de la cabecera de Sonic Candle: «Lyric Candle» con la misma vela blanca y, en lugar de la señal que se apaga, una línea de palabras de karaoke (repintadas en azul, la actual en dorado y elevada, las siguientes apagadas).
- El título de la ventana es solo «Lyric Candle»; antes mostraba el título interno del proyecto (por ejemplo «Demo · Luz y ritmo») aunque abrieras otro.
- El número de versión del encabezado se lee de `VERSION` en `lyric_candle/model.py`; `INSTALAR.bat` ya no lo repite.

## Idioma, guía y versión portable

- Interfaz en español e inglés. Al iniciar se usa el idioma de interfaz del sistema: español si es cualquier variante de español, inglés en los demás casos. **Opciones → Idioma** permite elegir Automático, Español o English; se aplica al reiniciar y ofrece reiniciar en el momento.
- Los textos propios de Qt (botones Sí/No/Guardar, selectores de archivo y color) también siguen el idioma elegido.
- Nueva guía rápida (**Ayuda → Guía rápida**, F1) para la 0.2.3, en ventana con secciones: FFmpeg, flujo de trabajo, sílabas y efectos, diseño y video base, guardar/exportar, atajos, versión instalada o portable y límites.
- Versión portable: con un archivo `portable.txt` junto a `LyricCandle.exe` (o junto a `main.py`), ajustes, autoguardado y registro se guardan en la carpeta `data` al lado. **Opciones → Abrir carpeta de datos** abre la ubicación en uso.
- Las validaciones del proyecto se identifican por código y no por su texto, para funcionar igual en ambos idiomas.
