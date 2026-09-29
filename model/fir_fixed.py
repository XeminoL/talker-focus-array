from pathlib import Path

import numpy as np

from cic import CIC_ORDER, CIC_RATIO
from fir import design
from params import FIR_COEF_BITS, FIR_DATA_BITS, FIR_RATIO

COEFFICIENT_FILE = Path(__file__).resolve().parent.parent / "rtl" / "fir_coefficients.hex"
CIC_GAIN_BITS = CIC_ORDER * int(np.log2(CIC_RATIO))
INPUT_SHIFT = CIC_GAIN_BITS + 1 - FIR_DATA_BITS
OUTPUT_SHIFT = FIR_COEF_BITS - 1
DATA_MAX = (1 << (FIR_DATA_BITS - 1)) - 1
DATA_MIN = -(1 << (FIR_DATA_BITS - 1))


def fixed_taps():
    return np.round(design() * (1 << (FIR_COEF_BITS - 1))).astype(np.int64)


def reduce_cic(cic):
    return np.minimum(cic >> INPUT_SHIFT, DATA_MAX)


def fir_fixed(samples, taps):
    full = np.convolve(samples, taps)[: len(samples)]
    return np.clip(full[FIR_RATIO - 1 :: FIR_RATIO] >> OUTPUT_SHIFT, DATA_MIN, DATA_MAX)


def to_hex(values, bits):
    digits = (bits + 3) // 4
    return [f"{int(v) & ((1 << bits) - 1):0{digits}x}" for v in values]


def export_coefficients():
    taps = fixed_taps()
    COEFFICIENT_FILE.write_text("\n".join(to_hex(taps, FIR_COEF_BITS)) + "\n")
    return taps


if __name__ == "__main__":
    taps = export_coefficients()
    print(f"{COEFFICIENT_FILE.name} {len(taps)} taps min {taps.min()} max {taps.max()} input shift {INPUT_SHIFT} output shift {OUTPUT_SHIFT}")
