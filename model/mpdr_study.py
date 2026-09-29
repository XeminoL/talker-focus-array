import sys

import numpy as np

from beam_fixed import aligned_stoi, beam_fixed, design
from build import scene_path
from frontend import frontend_path
from voices import load_voices

LOADING = 0.01
TAP_OPTIONS = (64, 128, 256)


def interference_recording(distance, like):
    signals = np.load(scene_path(distance))["signals"]
    interference = signals[1:].sum(axis=0)
    return np.round(interference / np.abs(interference).max() * np.abs(like).max()).astype(np.int64)


if __name__ == "__main__":
    distances = [float(v) for v in sys.argv[1:]] or [2.0, 4.0, 5.5]
    voices = load_voices()
    print("distance  covariance     " + "  ".join(f"{t:>5d}" for t in TAP_OPTIONS))
    for distance in distances:
        audio = np.load(frontend_path(distance))
        sources = {"mixture": audio, "interference": interference_recording(distance, audio)}
        for label, recording in sources.items():
            row = []
            for taps in TAP_OPTIONS:
                weights, shift = design("mpdr", distance, audio=recording, loading=LOADING, taps=taps, tag=f"-{label}-{taps}")
                row.append(aligned_stoi(voices[0], beam_fixed(audio, weights, shift).astype(float))[0])
            print(f"{distance:8.1f}  {label:13}  " + "  ".join(f"{v:.3f}" for v in row), flush=True)
