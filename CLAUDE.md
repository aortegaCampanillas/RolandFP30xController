# CLAUDE.md — RolandFP30xController

## Proyecto
Controlador GUI para el Roland FP-30X via MIDI (SysEx / RPN / CC).
- **Python** 3.11+ · **PySide6** · paquete editable en `src/roland_fp30x_controller/`

## Fuente de verdad MIDI
1. `docs/FP-30X_MIDI_Imple_eng01_W.pdf` — fuente de verdad (prioridad absoluta)
2. `docs/midi_reference.md` — referencia consolidada: mapa completo de direcciones SysEx
   extraídas de la app Roland Piano App 1.5.9 + mensajes estándar ya implementados.
   Consultar aquí antes de explorar el código o el PDF para nuevas funcionalidades.

## Estructura clave
```
src/roland_fp30x_controller/
  midi/         # lógica MIDI pura (sin Qt): client, messages, ports, parsers, tone_catalog
  ui/           # widgets Qt: main_window, midi_in_worker, i18n
  app.py        # QApplication bootstrap
  __main__.py   # punto de entrada
```

## Convenciones
- Lógica MIDI separada de widgets Qt (facilita pruebas).
- No eliminar `docs/FP-30X_MIDI_Imple_eng01_W.pdf`.
