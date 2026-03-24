# RI-practicas

Repositorio de prácticas de **Radio Definida por Software (SDR)**, enfocado en captura y análisis de señales RFID con GNU Radio.

## Contenido

- [Resumen](#resumen)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Proyecto RFID + HackRF](#proyecto-rfid--hackrf)
- [Requisitos](#requisitos)
- [Inicio rápido](#inicio-rápido)
- [Próximas prácticas](#próximas-prácticas)

## Resumen

Este repositorio contiene prácticas orientadas a:

- Captura de señales RFID en distintas bandas.
- Visualización de espectro y waterfall en GNU Radio.
- Grabación de datos IQ para análisis posterior.

## Estructura del repositorio

```text
RI-practicas/
├── README.md
└── RFID/
	├── README.md
	├── capture_rfid_hackrf.py
	├── rfid_hackrf_capture.grc
	└── rfid_hackrf_capture.py
```

## Proyecto RFID + HackRF

La carpeta `RFID/` incluye:

- `capture_rfid_hackrf.py`: captura con GUI (espectro, waterfall y tiempo) y modo headless.
- `rfid_hackrf_capture.grc`: flowgraph para GNU Radio Companion.
- `rfid_hackrf_capture.py`: script autogenerado desde el `.grc`.
- `README.md`: documentación específica del proyecto RFID.

## Requisitos

- GNU Radio
- gr-osmosdr
- HackRF tools

## Inicio rápido

1. Entra al proyecto RFID:

```bash
cd RFID
```

2. Verifica que HackRF esté disponible:

```bash
hackrf_info
```

3. Abre el flowgraph en GNU Radio Companion:

```bash
gnuradio-companion rfid_hackrf_capture.grc
```

4. O ejecuta captura directa por script:

```bash
python3 capture_rfid_hackrf.py --freq 13.5e6 --samp-rate 2e6 --bandwidth 2e6 --rf-gain 24 --if-gain 24 --bb-gain 20
```

## Próximas prácticas

- [x] Demodulación básica de tramas RFID UHF (EPC Gen2).
- [ ] Post-procesado offline de archivos IQ capturados.
- [ ] Comparación de desempeño por banda (HF 13.56 MHz vs UHF 860–960 MHz).
- [ ] Automatización de capturas por lotes con distintos parámetros de ganancia.
