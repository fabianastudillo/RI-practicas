"""
Embedded Python block: detecta UID en stream binario y lo imprime.
"""

import numpy as np
from collections import defaultdict, deque
from gnuradio import gr


def bits_to_byte_lsb_first(bit_list):
    value = 0
    for i, b in enumerate(bit_list):
        value |= (int(b) & 0x1) << i
    return value


class blk(gr.sync_block):
    """UID detector and passthrough"""

    def __init__(self, min_repeats=3):
        gr.sync_block.__init__(
            self,
            name='UID Detector',
            in_sig=[np.uint8],
            out_sig=[np.uint8],
        )
        self.buffer = deque(maxlen=12000)
        self.min_repeats = int(min_repeats)
        self.counts = defaultdict(int)
        self.last_reported = None

    def _scan_candidates(self):
        bits = list(self.buffer)
        if len(bits) < 45:
            return

        for offset in range(0, min(9, len(bits) - 44)):
            frame = bits[offset:offset + 45]
            groups = [frame[j * 9:(j + 1) * 9] for j in range(5)]
            if any(len(group) != 9 for group in groups):
                continue

            data = [bits_to_byte_lsb_first(group[:8]) for group in groups]
            bcc = data[0] ^ data[1] ^ data[2] ^ data[3]
            if data[4] != bcc:
                continue

            uid = tuple(data[:4])
            if all(v == 0x00 for v in uid):
                continue

            self.counts[uid] += 1
            if self.counts[uid] >= self.min_repeats and uid != self.last_reported:
                uid_hex = ''.join(f'{x:02X}' for x in uid)
                print(f'[UID detectado] {uid_hex}')
                self.last_reported = uid

    def work(self, input_items, output_items):
        in0 = input_items[0]
        out = output_items[0]

        out[:] = in0
        for x in in0:
            self.buffer.append(1 if int(x) > 0 else 0)

        self._scan_candidates()
        return len(out)