# Proyecto GNU Radio RFID + HackRF

Captura de señales RFID con **GNU Radio** y **HackRF**, con opciones de ejecución por script o flowgraph `.grc`.

## Contenido

- [Qué incluye](#qué-incluye)
- [Requisitos](#requisitos)
- [Inicio rápido](#inicio-rápido)
- [Presets recomendados](#presets-recomendados)
- [Captura a archivo (IQ)](#captura-a-archivo-iq)
- [Notas](#notas)

## Qué incluye

- `capture_rfid_hackrf.py`: capturador con GUI (espectro, waterfall y dominio temporal) + modo headless.
- `rfid_hackrf_capture.grc`: proyecto de GNU Radio Companion para captura con HackRF.
- `rfid_hackrf_capture.py`: script autogenerado desde el `.grc`.

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

Parámetros clave dentro del diagrama:

- `center_freq`: frecuencia central (ej. `866e6`, `915e6`, `13.56e6`).
- `samp_rate`: tasa de muestreo.
- `bandwidth`: ancho de banda.
- `rf_gain`, `if_gain`, `bb_gain`: ganancias del frontend.
- `output_file`: archivo de salida IQ.

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

## Captura a archivo (IQ)

```bash
python3 capture_rfid_hackrf.py --freq 915e6 --samp-rate 10e6 --output rfid_915M.cfile --headless
```

Detener con `Ctrl+C`.

## Notas

- Ajusta ganancias según tu entorno para evitar saturación.
- Para demodulación de protocolos RFID específicos, usa los IQ capturados en un flowgraph de post-procesado.
