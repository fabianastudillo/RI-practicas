#!/usr/bin/env python3

import argparse
import signal
import sys
from collections import defaultdict, deque
import numpy as np

from PyQt5 import Qt
import sip

from gnuradio import blocks
from gnuradio import digital
from gnuradio import filter
from gnuradio import gr
from gnuradio import qtgui
from gnuradio.filter import firdes
import osmosdr


def bits_to_byte_lsb_first(bit_list):
    value = 0
    for index, bit in enumerate(bit_list):
        value |= (int(bit) & 0x1) << index
    return value


def manchester_decode(raw_bits, sps):
    """ISO14443A tag->reader Manchester: 0=low/high, 1=high/low."""
    half = max(1, int(round(sps / 2.0)))
    span = int(sps)
    data_bits = []
    i = 0
    while i + span <= len(raw_bits):
        v1 = 1 if sum(raw_bits[i: i + half]) >= half / 2.0 else 0
        v2 = 1 if sum(raw_bits[i + half: i + span]) >= (span - half) / 2.0 else 0
        if v1 == 0 and v2 == 1:
            data_bits.append(0)
        elif v1 == 1 and v2 == 0:
            data_bits.append(1)
        else:
            data_bits.append(0)
        i += span
    return data_bits


class UIDDetector(gr.sync_block):
    """
    Detector didactico de UID/ID desde stream binario (0/1).

    Estrategia:
    - Mantiene un buffer circular de muestras binarizadas (40000 muestras).
    - Decodifica Manchester (ISO14443A tag->reader: 0=L/H, 1=H/L).
    - Busca ventanas con formato ISO14443A: 5 bytes + BCC (con y sin paridad).
    - Valida BCC (byte4 = byte0 XOR byte1 XOR byte2 XOR byte3).
    - Reporta el UID cuando se observa repetidamente para reducir falsos positivos.
    """

    def __init__(self, min_repeats=2, sample_rate=2e6, symbol_rate=106e3):
        gr.sync_block.__init__(
            self,
            name="uid_detector",
            in_sig=[np.uint8],
            out_sig=None,
        )
        self.buffer = deque(maxlen=40000)
        self.min_repeats = int(min_repeats)
        self.sample_rate = float(sample_rate)
        self.symbol_rate = float(symbol_rate)
        self.samples_per_symbol = max(2.0, self.sample_rate / self.symbol_rate)
        self.counts = defaultdict(int)
        self.last_reported = None

    def _try_decode_uid(self, bits):
        n = len(bits)
        # 5 bytes x 8 bits, LSB-first, no parity
        if n >= 40:
            for offset in range(min(n - 39, 12)):
                data = []
                for j in range(5):
                    s = offset + j * 8
                    data.append(bits_to_byte_lsb_first(bits[s:s + 8]))
                xor = data[0] ^ data[1] ^ data[2] ^ data[3]
                if data[4] == xor and not all(v == 0 for v in data[:4]):
                    return tuple(data[:4])
        # 5 bytes x 9 bits (8 data + 1 parity), LSB-first
        if n >= 45:
            for offset in range(min(n - 44, 12)):
                data = []
                for j in range(5):
                    s = offset + j * 9
                    data.append(bits_to_byte_lsb_first(bits[s:s + 8]))
                xor = data[0] ^ data[1] ^ data[2] ^ data[3]
                if data[4] == xor and not all(v == 0 for v in data[:4]):
                    return tuple(data[:4])
        return None

    def _report_uid(self, uid):
        self.counts[uid] += 1
        if self.counts[uid] >= self.min_repeats and uid != self.last_reported:
            uid_display = "UID: " + " ".join("{:02X}".format(b) for b in uid)
            print("[UID detectado] " + uid_display)
            self.last_reported = uid

    def _scan_candidates(self):
        samples = list(self.buffer)
        sps = self.samples_per_symbol
        n = len(samples)
        if n < int(sps) * 46:
            return

        window = int(sps * 260)
        recent = samples[max(0, n - window):]

        for polarity_flip in (False, True):
            seg = [1 - b for b in recent] if polarity_flip else recent

            # Manchester decode with multiple phase offsets
            ph_step = max(1, int(sps) // 4)
            for ph in range(0, min(int(sps), 20), ph_step):
                mbits = manchester_decode(seg[ph:], sps)
                uid = self._try_decode_uid(mbits)
                if uid:
                    self._report_uid(uid)
                    return

            # NRZ multi-phase sampling
            for phase in [sps * k / 6.0 for k in range(7)]:
                idx = phase
                bits = []
                while idx < len(seg):
                    s = int(max(0, round(idx - 0.4 * sps)))
                    e = int(min(len(seg), round(idx + 0.4 * sps) + 1))
                    w = seg[s:e]
                    if not w:
                        break
                    bits.append(1 if sum(w) >= len(w) / 2.0 else 0)
                    idx += sps
                uid = self._try_decode_uid(bits)
                if uid:
                    self._report_uid(uid)
                    return

    def work(self, input_items, output_items):
        in0 = input_items[0]
        for value in in0:
            self.buffer.append(1 if int(value) > 0 else 0)
        self._scan_candidates()
        return len(in0)


class RFIDTagIDDecoder(gr.top_block, Qt.QWidget):
    def __init__(
        self,
        center_freq,
        samp_rate,
        bandwidth,
        rf_gain,
        if_gain,
        bb_gain,
        ppm,
        hackrf_index,
        lpf_cutoff,
        lpf_transition,
        decim,
        smooth_len,
        env_gain,
        threshold,
        repeats,
    ):
        gr.top_block.__init__(self, "RFID Tag ID Decoder")
        Qt.QWidget.__init__(self)

        self.setWindowTitle("RFID Tag ID Decoder")
        qtgui.util.check_set_qss()
        self._layout = Qt.QVBoxLayout(self)

        self.source = osmosdr.source(args="numchan=1 hackrf={}".format(hackrf_index))
        self.source.set_sample_rate(samp_rate)
        self.source.set_center_freq(center_freq, 0)
        self.source.set_freq_corr(ppm, 0)
        self.source.set_dc_offset_mode(0, 0)
        self.source.set_iq_balance_mode(0, 0)
        self.source.set_gain_mode(False, 0)
        self.source.set_gain(rf_gain, 0)
        self.source.set_if_gain(if_gain, 0)
        self.source.set_bb_gain(bb_gain, 0)
        self.source.set_antenna("", 0)
        self.source.set_bandwidth(bandwidth, 0)

        self.c2mag = blocks.complex_to_mag_squared(1)
        self.lpf = filter.fir_filter_fff(
            int(decim),
            firdes.low_pass(
                1.0, samp_rate, lpf_cutoff, lpf_transition,
                firdes.WIN_HAMMING, 6.76
            ),
        )
        self.smooth = blocks.moving_average_ff(
            int(smooth_len), 1.0 / float(smooth_len), 4096, 1
        )
        self.env_amp = blocks.multiply_const_ff(float(env_gain))
        self.thr = blocks.threshold_ff(float(threshold), float(threshold) * 1.2, 0)
        self.slicer = digital.binary_slicer_fb()
        self.bits_to_float = blocks.char_to_float(1, 1.0)

        self.uid_detector = UIDDetector(
            min_repeats=repeats,
            sample_rate=samp_rate / decim,
            symbol_rate=106e3,
        )

        self.freq_sink = qtgui.freq_sink_c(
            2048, 0, center_freq, samp_rate, "RFID Spectrum", 1, None,
        )
        self.freq_sink.set_update_time(0.05)
        self.freq_sink.set_y_axis(-130, 10)
        self.freq_sink.enable_grid(True)
        self.freq_sink.enable_control_panel(True)

        self.waterfall_sink = qtgui.waterfall_sink_c(
            1024, 0, center_freq, samp_rate, "RFID Burst Waterfall", 1, None,
        )
        self.waterfall_sink.set_update_time(0.05)
        self.waterfall_sink.enable_grid(True)

        self.pulse_sink = qtgui.time_sink_f(
            8192, samp_rate / float(decim), "Pulse Viewer", 1, None,
        )
        self.pulse_sink.set_update_time(0.02)
        self.pulse_sink.enable_grid(True)
        self.pulse_sink.enable_autoscale(True)

        self.bits_sink = qtgui.time_sink_f(
            8192, samp_rate / float(decim), "Bitstream Viewer", 1, None,
        )
        self.bits_sink.set_update_time(0.02)
        self.bits_sink.enable_grid(True)
        self.bits_sink.set_y_axis(-0.2, 1.2)

        self._layout.addWidget(sip.wrapinstance(self.freq_sink.qwidget(), Qt.QWidget))
        self._layout.addWidget(sip.wrapinstance(self.waterfall_sink.qwidget(), Qt.QWidget))
        self._layout.addWidget(sip.wrapinstance(self.pulse_sink.qwidget(), Qt.QWidget))
        self._layout.addWidget(sip.wrapinstance(self.bits_sink.qwidget(), Qt.QWidget))

        self.connect((self.source, 0), (self.freq_sink, 0))
        self.connect((self.source, 0), (self.waterfall_sink, 0))
        self.connect((self.source, 0), (self.c2mag, 0))
        self.connect((self.c2mag, 0), (self.lpf, 0))
        self.connect((self.lpf, 0), (self.smooth, 0))
        self.connect((self.smooth, 0), (self.env_amp, 0))
        self.connect((self.env_amp, 0), (self.pulse_sink, 0))
        self.connect((self.env_amp, 0), (self.thr, 0))
        self.connect((self.thr, 0), (self.slicer, 0))
        self.connect((self.slicer, 0), (self.uid_detector, 0))
        self.connect((self.slicer, 0), (self.bits_to_float, 0))
        self.connect((self.bits_to_float, 0), (self.bits_sink, 0))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Decodificacion basica de trama RFID y deteccion de UID/ID en tiempo real"
    )
    parser.add_argument("--freq", type=float, default=13.56e6,
                        help="Frecuencia central en Hz")
    parser.add_argument("--samp-rate", type=float, default=4e6,
                        help="Sample rate en S/s (4e6 para capturar subportadora 847.5 kHz)")
    parser.add_argument("--bandwidth", type=float, default=4e6,
                        help="Ancho de banda RF en Hz")
    parser.add_argument("--rf-gain", type=float, default=24, help="Ganancia RF/LNA")
    parser.add_argument("--if-gain", type=float, default=24, help="Ganancia IF/VGA")
    parser.add_argument("--bb-gain", type=float, default=20, help="Ganancia baseband")
    parser.add_argument("--ppm", type=float, default=0, help="Correccion en ppm")
    parser.add_argument("--hackrf-index", type=int, default=0, help="Indice del HackRF")
    parser.add_argument("--lpf-cutoff", type=float, default=950e3,
                        help="Cutoff LPF en Hz (debe ser > 847.5 kHz para ISO14443A)")
    parser.add_argument("--lpf-transition", type=float, default=100e3,
                        help="Transicion LPF en Hz")
    parser.add_argument("--decim", type=int, default=2,
                        help="Factor de decimacion (2 con samp-rate=4e6 -> 2 MHz efectivos)")
    parser.add_argument("--smooth-len", type=int, default=4, help="Ventana de suavizado")
    parser.add_argument("--env-gain", type=float, default=100.0, help="Ganancia de envolvente")
    parser.add_argument("--threshold", type=float, default=0.35, help="Umbral de binarizacion")
    parser.add_argument("--uid-repeats", type=int, default=2,
                        help="Repeticiones minimas para confirmar UID")
    return parser.parse_args()


def main():
    args = parse_args()
    qapp = Qt.QApplication(sys.argv)

    eff_rate = args.samp_rate / args.decim
    print("Iniciando decodificador RFID...")
    print("  center_freq  = {:.3f} MHz".format(args.freq / 1e6))
    print("  samp_rate    = {:.1f} MS/s".format(args.samp_rate / 1e6))
    print("  decim        = {}  ->  eff. rate = {:.0f} kHz".format(
        args.decim, eff_rate / 1e3))
    print("  lpf_cutoff   = {:.0f} kHz".format(args.lpf_cutoff / 1e3))
    print("  ISO14443A subcarrier @ 847.5 kHz: {}".format(
        "OK (< Nyquist)" if eff_rate / 2 > 847.5e3 else "WARN: aliasing!"))
    print("Acerque la etiqueta. Los UID detectados: [UID detectado] UID: XX XX XX XX")

    tb = RFIDTagIDDecoder(
        center_freq=args.freq,
        samp_rate=args.samp_rate,
        bandwidth=args.bandwidth,
        rf_gain=args.rf_gain,
        if_gain=args.if_gain,
        bb_gain=args.bb_gain,
        ppm=args.ppm,
        hackrf_index=args.hackrf_index,
        lpf_cutoff=args.lpf_cutoff,
        lpf_transition=args.lpf_transition,
        decim=args.decim,
        smooth_len=args.smooth_len,
        env_gain=args.env_gain,
        threshold=args.threshold,
        repeats=args.uid_repeats,
    )

    def stop_handler(*_):
        tb.stop()
        tb.wait()
        qapp.quit()

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    tb.start()
    tb.show()
    qapp.exec_()
    tb.stop()
    tb.wait()


if __name__ == "__main__":
    main()
