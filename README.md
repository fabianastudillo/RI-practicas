# RI-practicas

Repositorio de prácticas de radio definida por software (SDR).

## Estructura

- `RFID/`: proyecto de captura de señales RFID con **GNU Radio** y **HackRF**.

## Proyecto RFID + HackRF

En la carpeta `RFID/` se incluye:

- `capture_rfid_hackrf.py`: captura con GUI (espectro, waterfall, tiempo) y modo headless.
- `rfid_hackrf_capture.grc`: flowgraph de GNU Radio Companion.
- `README.md`: guía específica del proyecto.

## Requisitos

- GNU Radio
- gr-osmosdr
- HackRF tools

## Uso rápido

### Abrir el flowgraph en GNU Radio Companion

```bash
cd RFID
gnuradio-companion rfid_hackrf_capture.grc
```

### Ejecutar el script de captura

```bash
cd RFID
python3 capture_rfid_hackrf.py --freq 915e6 --samp-rate 10e6 --bandwidth 10e6 --rf-gain 16 --if-gain 24 --bb-gain 20
```

### Verificar dispositivo HackRF

```bash
hackrf_info
```

## Próximas prácticas

- [ ] Demodulación básica de tramas RFID UHF (EPC Gen2).
- [ ] Post-procesado offline de archivos IQ capturados.
- [ ] Comparación de desempeño por banda (HF 13.56 MHz vs UHF 860-960 MHz).
- [ ] Automatización de capturas por lotes con distintos parámetros de ganancia.
