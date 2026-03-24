# Proyecto GNU Radio RFID + HackRF

Visualización en tiempo real de señales RFID con **GNU Radio** y **HackRF**, usando script o flowgraph `.grc`.

## Contenido

- [Qué incluye](#qué-incluye)
- [Requisitos](#requisitos)
- [Inicio rápido](#inicio-rápido)
- [Presets recomendados](#presets-recomendados)
- [Notas](#notas)

## Qué incluye

- `capture_rfid_hackrf.py`: visualizador en tiempo real con GUI (espectro, waterfall y dominio temporal).
- `rfid_hackrf_capture.grc`: proyecto de GNU Radio Companion para captura con HackRF.
- `rfid_hackrf_capture.py`: script autogenerado desde el `.grc`.
- `rfid_epcgen2_basic_demod.grc`: demodulación básica UHF RFID EPC Gen2 (envolvente + filtrado + slicer).
- `rfid_epcgen2_basic_demod.py`: script autogenerado desde el `.grc` de demodulación.

## Requisitos

- `gnuradio`
- `gr-osmosdr`
- `hackrf`

Verifica dispositivo:

```bash
hackrf_info
```

## Inicio rápido

### Opción A: GNU Radio Companion (`.grc`)

```bash
cd /home/fabian/Projects/github/RI-practicas/RFID
gnuradio-companion rfid_hackrf_capture.grc
```

Para demodulación básica EPC Gen2:

```bash
cd /home/fabian/Projects/github/RI-practicas/RFID
gnuradio-companion rfid_epcgen2_basic_demod.grc
```

Parámetros clave dentro del diagrama:

- `center_freq`: frecuencia central (ej. `866e6`, `915e6`, `13.56e6`).
- `samp_rate`: tasa de muestreo.
- `bandwidth`: ancho de banda.
- `rf_gain`, `if_gain`, `bb_gain`: ganancias del frontend.

Parámetros clave en `rfid_epcgen2_basic_demod.grc`:

- `LPF Cutoff (Hz)`: ancho del filtro para extraer envolvente de backscatter.
- `Threshold`: umbral del detector para convertir señal a bits.
- `decim` y `smooth_len`: controlan resolución temporal y suavizado.

### Opción B: Script Python

```bash
python3 capture_rfid_hackrf.py --freq 915e6 --samp-rate 10e6 --bandwidth 10e6 --rf-gain 16 --if-gain 24 --bb-gain 20
```

## Presets recomendados

### UHF RFID (EPC Gen2, Europa ~865–868 MHz)

```bash
python3 capture_rfid_hackrf.py --freq 866e6 --samp-rate 10e6 --bandwidth 10e6 --rf-gain 16 --if-gain 24 --bb-gain 20
```

### UHF RFID (US ~902–928 MHz)

```bash
python3 capture_rfid_hackrf.py --freq 915e6 --samp-rate 10e6 --bandwidth 10e6 --rf-gain 16 --if-gain 24 --bb-gain 20
```

### HF RFID / NFC (13.56 MHz)

```bash
python3 capture_rfid_hackrf.py --freq 13.56e6 --samp-rate 2e6 --bandwidth 2e6 --rf-gain 24 --if-gain 24 --bb-gain 20
```

## Notas

- Ajusta ganancias según tu entorno para evitar saturación.
- Para demodulación de protocolos RFID específicos, se puede agregar un flowgraph de post-procesado dedicado.
