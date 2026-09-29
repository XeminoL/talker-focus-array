import numpy as np
from scipy.signal import resample_poly

from params import AUDIO_RATE, DECIMATION, PDM_RATE
from pdm import RESAMPLE_WINDOW, decimate, modulate, to_level, upsample

TONE_HZ = 1000.0
SECONDS = 1.0
AMPLITUDE = 0.5
EDGE = 1000


def snr(reference, estimate):
    r = reference[EDGE:-EDGE]
    e = estimate[EDGE:-EDGE] - r
    return 10 * np.log10(np.sum(r**2) / np.sum(e**2))


def in_band_snr(bits):
    level = to_level(bits)[0]
    window = np.hanning(len(level))
    spectrum = np.abs(np.fft.rfft(level * window)) ** 2
    freqs = np.fft.rfftfreq(len(level), 1 / PDM_RATE)
    tone = np.abs(freqs - TONE_HZ) < 20
    band = (freqs > 20) & (freqs < AUDIO_RATE / 2) & ~tone
    return 10 * np.log10(spectrum[tone].sum() / spectrum[band].sum())


if __name__ == "__main__":
    t = np.arange(int(SECONDS * AUDIO_RATE)) / AUDIO_RATE
    tone = AMPLITUDE * np.sin(2 * np.pi * TONE_HZ * t)
    fast = upsample(tone)
    round_trip = resample_poly(fast, 1, DECIMATION, window=RESAMPLE_WINDOW)
    print(f"resample round trip, no modulation   {snr(tone, round_trip):.1f} dB")
    bits = modulate(fast)
    print(f"modulator, in-band spectrum          {in_band_snr(bits):.1f} dB")
    print(f"modulator + decimate                 {snr(tone, decimate(bits)[0]):.1f} dB")
