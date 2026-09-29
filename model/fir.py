import numpy as np
from scipy.signal import firls, freqz

from cic import CIC_ORDER, CIC_RATIO
from params import AUDIO_RATE, PDM_RATE

FIR_INPUT_RATE = PDM_RATE // CIC_RATIO
PASS_EDGE = 7000.0
STOP_EDGE = 9000.0
FIR_TAPS = 121
STOP_WEIGHT = 30.0
GRID = 64


def cic_response(freqs):
    x = np.pi * np.asarray(freqs) / PDM_RATE
    ratio = np.ones_like(x)
    nonzero = x != 0
    ratio[nonzero] = np.sin(CIC_RATIO * x[nonzero]) / (CIC_RATIO * np.sin(x[nonzero]))
    return np.abs(ratio) ** CIC_ORDER


def design():
    edges = np.linspace(0, PASS_EDGE, GRID + 1)
    bands, desired, weights = [], [], []
    for low, high in zip(edges[:-1], edges[1:]):
        bands += [low, high]
        desired += list(1 / cic_response(np.array([low, high])))
        weights.append(1.0)
    bands += [STOP_EDGE, FIR_INPUT_RATE / 2]
    desired += [0.0, 0.0]
    weights.append(STOP_WEIGHT)
    return firls(FIR_TAPS, bands, desired, weight=weights, fs=FIR_INPUT_RATE)


def overall_response(taps, freqs):
    _, fir = freqz(taps, worN=freqs, fs=FIR_INPUT_RATE)
    return np.abs(fir) * cic_response(freqs)


if __name__ == "__main__":
    taps = design()
    passband = np.linspace(0, PASS_EDGE, 2000)
    stopband = np.linspace(STOP_EDGE, FIR_INPUT_RATE / 2, 4000)
    total_pass = 20 * np.log10(overall_response(taps, passband))
    total_stop = 20 * np.log10(overall_response(taps, stopband))
    droop = 20 * np.log10(cic_response(np.array([PASS_EDGE])))[0]
    print(f"taps {len(taps)} input {FIR_INPUT_RATE} Hz output {AUDIO_RATE} Hz")
    print(f"cic droop at {PASS_EDGE:.0f} Hz {droop:.2f} dB")
    print(f"passband ripple {total_pass.min():+.3f} to {total_pass.max():+.3f} dB")
    print(f"stopband worst {total_stop.max():.1f} dB")
    print(f"coefficient peak {np.abs(taps).max():.4f} sum {taps.sum():.4f}")
