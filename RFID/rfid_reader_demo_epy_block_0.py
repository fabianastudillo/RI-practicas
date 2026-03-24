"""Embedded Python block: detecta UID ISO14443A con decodificacion Manchester."""

import numpy as np
from collections import defaultdict, deque
from gnuradio import gr


def bits_to_byte_lsb_first(bit_list):
    value = 0
    for i, b in enumerate(bit_list):
        value |= (int(b) & 0x1) << i
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
            data_bits.append(0)  # ambiguous, treat as 0
        i += span
    return data_bits


class blk(gr.sync_block):
    """UID Detector and passthrough"""

    def __init__(self, min_repeats=2, sample_rate=2e6, symbol_rate=106e3, top_block=None):
        gr.sync_block.__init__(self, name='UID Detector',
                               in_sig=[np.uint8], out_sig=[np.uint8])
        self.buffer = deque(maxlen=40000)
        self.min_repeats = int(min_repeats)
        self.sample_rate = float(sample_rate)
        self.symbol_rate = float(symbol_rate)
        self.samples_per_symbol = max(2.0, self.sample_rate / self.symbol_rate)
        self.counts = defaultdict(int)
        self.last_reported = None
        self.top_block = top_block

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
            uid_display = 'UID: ' + ' '.join('{:02X}'.format(x) for x in uid)
            print('[UID detectado] ' + uid_display)
            self.last_reported = uid
            if self.top_block is not None and hasattr(self.top_block, 'set_detected_uid'):
                self.top_block.set_detected_uid(uid_display)

    def _scan_candidates(self):
        samples = list(self.buffer)
        sps = self.samples_per_symbol
        n = len(samples)
        if n < int(sps) * 46:
            return

        window = int(sps * 260)
        recent = samples[max(0, n - window):]

        for polarity_flip in (False, True):
            if polarity_flip:
                seg = [1 - b for b in recent]
            else:
                seg = recent

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
        out = output_items[0]
        out[:] = in0
        for x in in0:
            self.buffer.append(1 if int(x) > 0 else 0)
        self._scan_candidates()
        return len(out)