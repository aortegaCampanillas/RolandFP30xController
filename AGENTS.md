# Instrucciones para agentes (Cursor / IA)

## Fuente de verdad MIDI (prioridad absoluta)

Antes de asumir direcciones SysEx, mapas de parámetros o comportamiento del FP-30X, **consulta y prioriza** el documento oficial de Roland en este repositorio:

- `docs/FP-30X_MIDI_Imple_eng01_W.pdf` — *FP-30X MIDI Implementation*

Ese PDF debe tratarse como la **primera fuente de información** para:

- Formato de mensajes (SysEx, RPN/NRPN, Control Change, etc.)
- Modelos de datos y validación de bytes
- Cualquier implementación de envío/recepción MIDI hacia el instrumento

Si hay conflicto entre el PDF, comentarios en el código, foros o recuerdo del modelo, **gana el PDF** salvo que se demuestre un error tipográfico evidente en el manual.

## Stack del proyecto

- **Python** 3.11+
- **Qt** vía **PySide6**
- Paquete editable bajo `src/roland_fp30x_controller/`

## Convenciones

- Mantener la lógica MIDI separada de widgets Qt cuando sea razonable (facilita pruebas).
- No eliminar ni mover `docs/FP-30X_MIDI_Imple_eng01_W.pdf` sin sustituirlo por una versión equivalente o actualizada del mismo documento.
