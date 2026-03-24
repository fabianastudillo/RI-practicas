#!/usr/bin/env python3

import argparse
import signal
import sys

from PyQt5 import Qt
import sip

from gnuradio import gr
from gnuradio import qtgui
import osmosdr


class RFIDHackRFCapture(gr.top_block, Qt.QWidget):
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
    ):
        gr.top_block.__init__(self, "RFID HackRF Capture")
        Qt.QWidget.__init__(self)

        self.setWindowTitle("RFID HackRF Capture")
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

        fft_size = 4096

        self.freq_sink = qtgui.freq_sink_c(
            fft_size,
            0,
            center_freq,
            samp_rate,
            "RFID Spectrum",
            1,
            None,
        )
        self.freq_sink.set_update_time(0.05)
        self.freq_sink.set_y_axis(-130, 10)
        self.freq_sink.enable_autoscale(False)
        self.freq_sink.enable_grid(True)
        self.freq_sink.set_fft_average(0.2)
        self.freq_sink.enable_control_panel(True)

        self.waterfall_sink = qtgui.waterfall_sink_c(
            2048,
            0,
            center_freq,
            samp_rate,
            "RFID Waterfall",
            1,
            None,
        )
        self.waterfall_sink.set_update_time(0.05)
        self.waterfall_sink.enable_grid(True)

        self.time_sink = qtgui.time_sink_c(
            2048,
            samp_rate,
            "RFID Time Domain",
            1,
            None,
        )
        self.time_sink.set_update_time(0.05)
        self.time_sink.enable_grid(True)

        self._layout.addWidget(sip.wrapinstance(self.freq_sink.qwidget(), Qt.QWidget))
        self._layout.addWidget(sip.wrapinstance(self.waterfall_sink.qwidget(), Qt.QWidget))
        self._layout.addWidget(sip.wrapinstance(self.time_sink.qwidget(), Qt.QWidget))

        self.connect((self.source, 0), (self.freq_sink, 0))
        self.connect((self.source, 0), (self.waterfall_sink, 0))
        self.connect((self.source, 0), (self.time_sink, 0))


def parse_args():
    parser = argparse.ArgumentParser(description="Captura de señales RFID con HackRF + GNU Radio")
    parser.add_argument("--freq", type=float, default=13.5e6, help="Frecuencia central en Hz (por defecto 13.5e6)")
    parser.add_argument("--samp-rate", type=float, default=2e6, help="Sample rate en S/s (por defecto 2e6)")
    parser.add_argument("--bandwidth", type=float, default=2e6, help="Ancho de banda RF en Hz")
    parser.add_argument("--rf-gain", type=float, default=16, help="Ganancia RF/LNA")
    parser.add_argument("--if-gain", type=float, default=24, help="Ganancia IF/VGA")
    parser.add_argument("--bb-gain", type=float, default=20, help="Ganancia baseband")
    parser.add_argument("--ppm", type=float, default=0, help="Corrección de frecuencia (ppm)")
    parser.add_argument("--hackrf-index", type=int, default=0, help="Índice del dispositivo HackRF")
    return parser.parse_args()


def main():
    args = parse_args()

    qapp = Qt.QApplication(sys.argv)

    tb = RFIDHackRFCapture(
        center_freq=args.freq,
        samp_rate=args.samp_rate,
        bandwidth=args.bandwidth,
        rf_gain=args.rf_gain,
        if_gain=args.if_gain,
        bb_gain=args.bb_gain,
        ppm=args.ppm,
        hackrf_index=args.hackrf_index,
    )

    def stop_handler(*_):
        tb.stop()
        tb.wait()
        if qapp is not None:
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
