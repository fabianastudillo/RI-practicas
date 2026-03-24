# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Educational SDR (Software Defined Radio) repository for RFID signal capture and analysis using GNU Radio and HackRF hardware. The main project lives in [RFID/](RFID/).

## Running the tools

All scripts require GNU Radio, gr-osmosdr, and a connected HackRF device (`hackrf_info` to verify).

**Real-time spectrum/waterfall visualizer:**
```bash
cd RFID
python3 capture_rfid_hackrf.py --freq 13.5e6 --samp-rate 2e6 --bandwidth 2e6 --rf-gain 24 --if-gain 24 --bb-gain 20
```

**Frame decoder / UID output to console:**
```bash
cd RFID
python3 rfid_tag_id_decoder.py --freq 13.5e6 --samp-rate 2e6 --bandwidth 2e6 --rf-gain 20 --if-gain 24 --bb-gain 20
```

**Open a flowgraph in GNU Radio Companion:**
```bash
cd RFID
gnuradio-companion rfid_hackrf_capture.grc
# or
gnuradio-companion rfid_epcgen2_basic_demod.grc
# or
gnuradio-companion rfid_reader_demo.grc
```

## Architecture

The project has two layers:

1. **Flowgraph layer** (`.grc` files) — XML-based GNU Radio Companion projects that define signal processing pipelines visually. They auto-generate the corresponding `.py` files; **do not edit the generated `.py` files directly**.

2. **Standalone scripts** — `capture_rfid_hackrf.py` and `rfid_tag_id_decoder.py` are hand-written and serve as the primary development targets.

### Signal processing chain (HF RFID / ISO14443A)

```
HackRF source (OsmoSDR) → LPF → envelope detection → threshold slicer → Manchester decoder → UID frame extractor
```

- `rfid_hackrf_capture.grc`: basic capture with FFT + waterfall + time-domain display
- `rfid_epcgen2_basic_demod.grc`: UHF EPC Gen2 demodulation (envelope + slicer + bit visualization)
- `rfid_reader_demo.grc`: NFC-style reader demo; UID printed to console and displayed in GUI via embedded Python block `rfid_reader_demo_epy_block_0.py`
- `rfid_tag_id_decoder.py`: standalone ISO14443A pipeline with Manchester decoding and UID validation

## Key parameters

| Parameter | HF RFID (class preset) | UHF Europe | UHF US |
|-----------|------------------------|------------|--------|
| `center_freq` | 13.5e6 | 866e6 | 915e6 |
| `samp_rate` | 2e6 | 10e6 | 10e6 |
| `bandwidth` | 2e6 | 10e6 | 10e6 |
| `rf_gain` | 20 | 16 | 16 |
| `if_gain` | 24 | 24 | 24 |
| `bb_gain` | 20 | 20 | 20 |

For `rfid_epcgen2_basic_demod.grc` specifically: `LPF Cutoff=120e3`, `Env Gain=40`, `Threshold=0.35`, `decim=10`, `smooth_len=16`.

## Embedded Python blocks

`rfid_reader_demo_epy_block_0.py` is an embedded block referenced from `rfid_reader_demo.grc`. It contains the UID detection logic (Manchester decode + frame validation). When editing it, regenerate the flowgraph's `.py` by running the `.grc` in GNU Radio Companion or via `grcc rfid_reader_demo.grc`.

## Notes

- `*.cfile` IQ capture files are gitignored (they can be several GB).
- The `RFID/__pycache__/` directory is untracked; it is safe to ignore.
