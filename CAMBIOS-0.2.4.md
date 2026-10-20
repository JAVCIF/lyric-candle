# Alpha 0.2.4 · Estabilización

## Texto sin aplicar

- Escribir en los cuadros de Frase marca el proyecto como modificado. Cerrar, abrir otro proyecto o crear uno nuevo ofrece guardar los cambios.
- Guardar y autoguardar conservan los borradores de la fila actual y de otras filas. Reabrir o recuperar la sesión los devuelve a sus cuadros sin sustituir el texto aplicado ni borrar marcas de sílabas.
- Un indicador en la cabecera muestra las frases con texto pendiente. Antes de exportar se pide revisarlas y aplicarlas; la app selecciona la primera pendiente.
- Los borradores se guardan en el campo opcional `text_drafts` del schema 2. Los proyectos anteriores siguen abriendo. Para conservar borradores al guardar se necesita 0.2.4 o posterior.

## Video

- El tamaño del video base aplica la relación de aspecto de píxel y luego su orientación de 90°/180°/270°, en lugar de usar solamente las dimensiones codificadas.
- La extracción de fotogramas para la vista pausada y la exportación normalizan los píxeles antes de ajustar el video al lienzo. Esto evita comprimir la imagen y añadir barras en medios anamórficos.
- La composición exportada declara píxeles cuadrados. También se contemplan medios sin información de aspecto y píxeles estrechos.
- Al abrir o recuperar un proyecto con seguimiento de resolución/FPS activado se releen las propiedades del medio. Se corrigen así los tamaños que una versión anterior guardó sin interpretar la rotación.
- Se conserva la transformación que Qt ya aplica al video durante la reproducción, para evitar rotarlo o estirarlo dos veces.

## Comprobaciones

- Nuevas regresiones en `tests/test_stability.py`: borradores con Unicode y texto vacío, guardar al cerrar, cancelar cierre, reapertura, autoguardado/recuperación, aplicar/undo, bloqueo de exportación y videos sintéticos con diferentes relaciones de píxel y rotaciones.
- Documentación y guía rápida en español e inglés actualizadas.
- Consulta `VERIFICACION.md` para el resultado completo y los límites de la validación.
