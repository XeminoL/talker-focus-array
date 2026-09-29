import numpy as np
from scipy.signal import freqz

from cic import CIC_LATENCY, CIC_ORDER, CIC_RATIO, cic_exact, cic_fast
from fir import FIR_INPUT_RATE, PASS_EDGE, STOP_EDGE, cic_response, design
from params import FIR_RATIO
from pdm_build import pdm_path

COEFFICIENT_BITS = (10, 12, 14, 16, 18)
DATA_BITS = (12, 14, 16, 18, 20, 24)
CIC_GAIN_BITS = CIC_ORDER * int(np.log2(CIC_RATIO))
EDGE = 200


def quantize_taps(taps, bits):
    return np.round(taps * (1 << (bits - 1))).astype(np.int64)


def response_db(taps, freqs):
    _, h = freqz(taps, worN=freqs, fs=FIR_INPUT_RATE)
    return 20 * np.log10(np.abs(h) * cic_response(freqs) + 1e-300)


def fixed_fir(samples, taps, data_bits):
    shift = CIC_GAIN_BITS + 1 - data_bits
    reduced = samples >> shift
    full = np.convolve(reduced, taps)[: len(samples)]
    return full[FIR_RATIO - 1 :: FIR_RATIO], shift


def snr(reference, estimate):
    r = reference[EDGE:-EDGE]
    e = estimate[EDGE:-EDGE] - r
    return 10 * np.log10(np.sum(r**2) / np.sum(e**2))


if __name__ == "__main__":
    taps = design()
    passband = np.linspace(0, PASS_EDGE, 2000)
    stopband = np.linspace(STOP_EDGE, FIR_INPUT_RATE / 2, 4000)
    print("coefficient bits  ripple dB         stopband dB")
    for bits in COEFFICIENT_BITS:
        q = quantize_taps(taps, bits) / (1 << (bits - 1))
        p = response_db(q, passband)
        print(f"{bits:17d}  {p.min():+.3f} {p.max():+.3f}   {response_db(q, stopband).max():7.1f}")

    bits = np.unpackbits(np.load(pdm_path(2.0))["bits"][63:64], axis=1)[0]
    head = bits[: CIC_RATIO * 4000]
    print("cic_fast equals exact on 4000 outputs", bool(np.all(cic_fast(head, CIC_LATENCY) == cic_exact(head, CIC_LATENCY))))
    cic = cic_fast(bits, CIC_LATENCY)
    reference = np.convolve(cic / float(1 << CIC_GAIN_BITS), taps)[: len(cic)][FIR_RATIO - 1 :: FIR_RATIO]
    print(f"cic outputs {len(cic)} fir outputs {len(reference)} reference peak {np.abs(reference).max():.3f}")
    print("data bits  coef 16  coef 18")
    for data_bits in DATA_BITS:
        row = []
        for coefficient_bits in (16, 18):
            q = quantize_taps(taps, coefficient_bits)
            out, shift = fixed_fir(cic, q, data_bits)
            scaled = out / float(1 << (coefficient_bits - 1)) * (1 << shift) / (1 << CIC_GAIN_BITS)
            row.append(snr(reference, scaled))
        print(f"{data_bits:9d}  {row[0]:7.1f}  {row[1]:7.1f}")
