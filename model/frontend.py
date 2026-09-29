import time
from pathlib import Path

import numpy as np

from cic import CIC_LATENCY, cic_fast
from fir_fixed import fir_fixed, fixed_taps, reduce_cic
from params import TARGET_DISTANCES
from pdm_build import pdm_path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "data" / "frontend"


def frontend_path(distance):
    return FRONTEND_DIR / f"target_{distance:.1f}m_audio.npy"


def frontend_model(packed, length, taps):
    out = []
    for mic in range(packed.shape[0]):
        bits = np.unpackbits(packed[mic : mic + 1], axis=1)[0, :length]
        out.append(fir_fixed(reduce_cic(cic_fast(bits, CIC_LATENCY)), taps))
    return np.array(out, dtype=np.int32)


if __name__ == "__main__":
    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
    taps = fixed_taps()
    for distance in TARGET_DISTANCES:
        start = time.time()
        scene = np.load(pdm_path(distance))
        audio = frontend_model(scene["bits"], int(scene["length"]), taps)
        np.save(frontend_path(distance), audio)
        print(f"{frontend_path(distance).name} {audio.shape} peak {int(np.abs(audio).max())} {time.time() - start:.0f} s", flush=True)
