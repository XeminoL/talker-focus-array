import numpy as np
from scipy.signal import firwin, resample_poly

from params import DECIMATION, PDM_RATE

FULL_SCALE = 0.5
RESAMPLE_TAPS = DECIMATION * 256
RESAMPLE_CUTOFF = 7800.0
RESAMPLE_WINDOW = firwin(RESAMPLE_TAPS + 1, RESAMPLE_CUTOFF, window=("kaiser", 12.0), fs=PDM_RATE)


def upsample(audio):
    return resample_poly(audio, DECIMATION, 1, axis=-1, window=RESAMPLE_WINDOW)


def modulate(signal):
    x = np.atleast_2d(signal)
    first = np.zeros(x.shape[0])
    second = np.zeros(x.shape[0])
    feedback = np.zeros(x.shape[0])
    bits = np.empty(x.shape, dtype=np.uint8)
    for t in range(x.shape[1]):
        first += x[:, t] - feedback
        second += first - feedback
        high = second >= 0
        bits[:, t] = high
        feedback = np.where(high, 1.0, -1.0)
    return bits


def to_level(bits):
    return bits.astype(np.float64) * 2 - 1


def decimate(bits):
    return resample_poly(to_level(bits), 1, DECIMATION, axis=-1, window=RESAMPLE_WINDOW)


if __name__ == "__main__":
    import time
    from pathlib import Path

    scene = np.load(Path(__file__).resolve().parent.parent / "data" / "scenes" / "target_4.0m.npz")
    audio = scene["signals"][:, 0, :].sum(axis=0)
    scale = FULL_SCALE / np.abs(audio).max()
    start = time.time()
    bits = modulate(upsample(audio * scale))
    print("bits", bits.shape, f"ones {bits.mean():.3f}", f"{time.time() - start:.1f} s")
    back = decimate(bits)[0] / scale
    edge = 3000
    error = back[edge:-edge] - audio[edge:-edge]
    snr = 10 * np.log10(np.sum(audio[edge:-edge] ** 2) / np.sum(error**2))
    print(f"recovered snr {snr:.1f} dB")
