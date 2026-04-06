# Instrucciones para agentes (Cursor / IA)

## Fuente de verdad MIDI (prioridad absoluta)

Antes de asumir direcciones SysEx, mapas de parámetros o comportamiento del FP-30X:

1. **Consulta primero** `docs/midi_reference.md` — referencia consolidada con el mapa
   completo de direcciones SysEx (extraídas de Roland Piano App 1.5.9 por ingeniería inversa)
   y los mensajes estándar ya implementados. Es el punto de partida más rápido.

2. **Si necesitas más detalle**, usa el PDF oficial:
   `docs/FP-30X_MIDI_Imple_eng01_W.pdf` — *FP-30X MIDI Implementation*

El PDF es la **fuente de verdad** para:
- Formato de mensajes (SysEx, RPN/NRPN, Control Change, etc.)
- Modelos de datos y validación de bytes

Si hay conflicto entre `midi_reference.md`, comentarios en el código, foros o recuerdo del modelo, **gana el PDF** salvo error tipográfico evidente.

## Stack del proyecto

- **Python** 3.11+
- **Qt** vía **PySide6**
- Paquete editable bajo `src/roland_fp30x_controller/`

## Convenciones

- Mantener la lógica MIDI separada de widgets Qt cuando sea razonable (facilita pruebas).
- No eliminar ni mover `docs/FP-30X_MIDI_Imple_eng01_W.pdf` sin sustituirlo por una versión equivalente o actualizada del mismo documento.
- Si un cambio afecta a valores leídos/escritos del piano (direcciones SysEx, mapeos, decodificación o sincronización UI↔piano), actualizar también:
  - `_READ_PIANO_VALUE_SPECS` en `src/roland_fp30x_controller/ui/main_window.py`
  - `_piano_value_summary()` / trazas `MIDI [VALUES]` en ese mismo archivo
  - `docs/midi_reference.md` si aparecen direcciones nuevas o cambia su interpretación
