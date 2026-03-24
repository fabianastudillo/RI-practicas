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


class UIDDetector(gr.sync_block):
    """
    Detector didáctico de UID/ID desde stream binario (0/1).

    Estrategia:
    - Mantiene un buffer de bits.
    - Busca ventanas de 45 bits con formato ISO14443A (5 bytes + bit de paridad por byte).
    - Extrae 5 bytes (LSB-first) ignorando bits de paridad.
    - Valida BCC (byte4 = byte0 XOR byte1 XOR byte2 XOR byte3).
    - Reporta el UID cuando se observa repetidamente para reducir falsos positivos.
    """

    def __init__(self, min_repeats=3, max_buffer_bits=12000):
        gr.sync_block.__init__(
            self,
            name="uid_detector",
            in_sig=[np.uint8],
            out_sig=None,
        )
        self.buffer = deque(maxlen=max_buffer_bits)
        self.min_repeats = int(min_repeats)
        self.counts = defaultdict(int)
        self.last_reported = None

    def _scan_iso14443a_uid_candidates(self):
        bits = list(self.buffer)
        if len(bits) < 45:
            return

        # Escaneo por desplazamientos para encontrar bloques de 5*(8 data + 1 parity)
        for offset in range(0, min(9, len(bits) - 44)):
            frame = bits[offset:offset + 45]
            groups = [frame[index * 9:(index + 1) * 9] for index in range(5)]
            if any(len(group) != 9 for group in groups):
                continue

            data_bytes = [bits_to_byte_lsb_first(group[:8]) for group in groups]

            bcc = data_bytes[0] ^ data_bytes[1] ^ data_bytes[2] ^ data_bytes[3]
            if data_bytes[4] != bcc:
                continue

            uid = tuple(data_bytes[:4])

            # Filtro rápido para casos triviales de ruido
            if all(byte == 0x00 for byte in uid):
                continue

            self.counts[uid] += 1
            if self.counts[uid] >= self.min_repeats and uid != self.last_reported:
                uid_hex = "".join(f"{byte:02X}" for byte in uid)
                print(f"[UID detectado] {uid_hex}")
                self.last_reported = uid

    def work(self, input_items, output_items):
        in0 = input_items[0]

        for value in in0:
            self.buffer.append(1 if int(value) > 0 else 0)

        self._scan_iso14443a_uid_candidates()
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

        self.source = osmosdr.source(args=f"numchan=1 hackrf={hackrf_index}")
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
            firdes.low_pass(1.0, samp_rate, lpf_cutoff, lpf_transition, firdes.WIN_HAMMING, 6.76),
        )
        self.smooth = blocks.moving_average_ff(int(smooth_len), 1.0 / float(smooth_len), 4096, 1)
        self.env_amp = blocks.multiply_const_ff(float(env_gain))
        self.thr = blocks.threshold_ff(float(threshold), float(threshold) * 1.2, 0)
        self.slicer = digital.binary_slicer_fb()
        self.bits_to_float = blocks.char_to_float(1, 1.0)

        self.uid_detector = UIDDetector(min_repeats=repeats)

        self.freq_sink = qtgui.freq_sink_c(
            2048,
            0,
            center_freq,
            samp_rate,
            "RFID Spectrum",
            1,
            None,
        )
        self.freq_sink.set_update_time(0.05)
        self.freq_sink.set_y_axis(-130, 10)
        self.freq_sink.enable_grid(True)
        self.freq_sink.enable_control_panel(True)

        self.waterfall_sink = qtgui.waterfall_sink_c(
            1024,
            0,
            center_freq,
            samp_rate,
            "RFID Burst Waterfall",
            1,
            None,
        )
        self.waterfall_sink.set_update_time(0.05)
        self.waterfall_sink.enable_grid(True)

        self.pulse_sink = qtgui.time_sink_f(
            8192,
            samp_rate / float(decim),
            "Pulse Viewer",
            1,
            None,
        )
        self.pulse_sink.set_update_time(0.02)
        self.pulse_sink.enable_grid(True)
        self.pulse_sink.enable_autoscale(True)

        self.bits_sink = qtgui.time_sink_f(
            8192,
            samp_rate / float(decim),
            "Bitstream Viewer",
            1,
            None,
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
        description="Decodificación básica de trama RFID y detección de UID/ID en tiempo real"
    )
    parser.add_argument("--freq", type=float, default=13.5e6, help="Frecuencia central en Hz")
    parser.add_argument("--samp-rate", type=float, default=2e6, help="Sample rate en S/s")
    parser.add_argument("--bandwidth", type=float, default=2e6, help="Ancho de banda RF en Hz")
    parser.add_argument("--rf-gain", type=float, default=20, help="Ganancia RF/LNA")
    parser.add_argument("--if-gain", type=float, default=24, help="Ganancia IF/VGA")
    parser.add_argument("--bb-gain", type=float, default=20, help="Ganancia baseband")
    parser.add_argument("--ppm", type=float, default=0, help="Corrección en ppm")
    parser.add_argument("--hackrf-index", type=int, default=0, help="Índice del HackRF")

    parser.add_argument("--lpf-cutoff", type=float, default=120e3, help="Cutoff LPF en Hz")
    parser.add_argument("--lpf-transition", type=float, default=20e3, help="Transición LPF en Hz")
    parser.add_argument("--decim", type=int, default=10, help="Factor de decimación")
    parser.add_argument("--smooth-len", type=int, default=16, help="Ventana de suavizado")
    parser.add_argument("--env-gain", type=float, default=40.0, help="Ganancia de envolvente")
    parser.add_argument("--threshold", type=float, default=0.35, help="Umbral de binarización")
    parser.add_argument("--uid-repeats", type=int, default=3, help="Repeticiones mínimas para confirmar UID")
    return parser.parse_args()


def main():
    args = parse_args()
    qapp = Qt.QApplication(sys.argv)

    print("Iniciando decodificador RFID...")
    print("Acerque la etiqueta y observe Pulse/Bitstream.")
    print("Los UID detectados se imprimen en consola como: [UID detectado] XXXXXXXX")

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
