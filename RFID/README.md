# Proyecto GNU Radio RFID + HackRF

Este proyecto captura señales RFID usando **HackRF** con GNU Radio.

## Archivos

- `capture_rfid_hackrf.py`: capturador con GUI (espectro, waterfall y dominio temporal) y modo headless.
- `rfid_hackrf_capture.grc`: proyecto GNU Radio Companion para captura con HackRF (espectro + grabación IQ).

## Requisitos

Ya instalados en tu sistema:

- `gnuradio`
- `gr-osmosdr`
- `hackrf`

## Verificar HackRF

```bash
hackrf_info
```

## Ejecutar

### Abrir proyecto `.grc` en GNU Radio Companion

```bash
cd /home/fabian/Projects/github/RI-practicas/RFID
gnuradio-companion rfid_hackrf_capture.grc
```

En el diagrama:

- Cambia `center_freq` según banda RFID (por ejemplo `866e6`, `915e6` o `13.56e6`).
- Ajusta `samp_rate`, `bandwidth` y ganancias (`rf_gain`, `if_gain`, `bb_gain`).
- Define `output_file` para guardar IQ.
- Presiona **Run**.

### UHF RFID (EPC Gen2, Europa ~865-868 MHz)

```bash
python3 capture_rfid_hackrf.py --freq 866e6 --samp-rate 10e6 --bandwidth 10e6 --rf-gain 16 --if-gain 24 --bb-gain 20
```

### UHF RFID (US ~902-928 MHz)

```bash
python3 capture_rfid_hackrf.py --freq 915e6 --samp-rate 10e6 --bandwidth 10e6 --rf-gain 16 --if-gain 24 --bb-gain 20
```

### HF RFID / NFC (13.56 MHz)

```bash
python3 capture_rfid_hackrf.py --freq 13.56e6 --samp-rate 2e6 --bandwidth 2e6 --rf-gain 24 --if-gain 24 --bb-gain 20
```

### Capturar IQ a archivo (sin GUI)

```bash
python3 capture_rfid_hackrf.py --freq 915e6 --samp-rate 10e6 --output rfid_915M.cfile --headless
```

Detener con `Ctrl+C`.

## Notas

- Ajusta ganancias según tu entorno para evitar saturación.
- Para demodular protocolos RFID concretos después de capturar IQ, se puede añadir un flowgraph de procesamiento adicional.
