import time
from pathlib import Path

import numpy as np

from build import SCENE_DIR, scene_path
from params import TARGET_DISTANCES
from pdm import FULL_SCALE, modulate, upsample

CHUNK = 16


def pdm_path(distance):
    return SCENE_DIR / f"target_{distance:.1f}m_pdm.npz"


def build_pdm(distance):
    mixture = np.load(scene_path(distance))["signals"].sum(axis=0).astype(np.float64)
    scale = FULL_SCALE / np.abs(mixture).max()
    packed = []
    for first in range(0, mixture.shape[0], CHUNK):
        fast = upsample(mixture[first : first + CHUNK] * scale).astype(np.float32)
        packed.append(np.packbits(modulate(fast), axis=1))
        print(f"  mics {first}-{first + CHUNK - 1} done", flush=True)
    np.savez(pdm_path(distance), bits=np.concatenate(packed), scale=scale, length=len(fast[0]))
    return scale


if __name__ == "__main__":
    for distance in TARGET_DISTANCES:
        start = time.time()
        scale = build_pdm(distance)
        size = pdm_path(distance).stat().st_size / 1e6
        print(f"{pdm_path(distance).name} scale {scale:.5f} {size:.0f} MB {time.time() - start:.0f} s", flush=True)
