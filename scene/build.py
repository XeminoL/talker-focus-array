import time
from pathlib import Path

import numpy as np

from geometry import microphone_positions, talker_positions
from params import AUDIO_RATE, TARGET_DISTANCES
from room import impulse_responses, render
from voices import SPEAKERS, load_voices

SCENE_DIR = Path(__file__).resolve().parent.parent / "data" / "scenes"


def scene_path(distance):
    return SCENE_DIR / f"target_{distance:.1f}m.npz"


def build(distance, voices, mics):
    talkers = talker_positions(distance)
    signals = render(voices, impulse_responses(talkers, mics)).astype(np.float32)
    np.savez(
        scene_path(distance),
        signals=signals,
        voices=voices.astype(np.float32),
        talkers=talkers,
        mics=mics,
        speakers=np.array(SPEAKERS),
        rate=AUDIO_RATE,
    )
    return signals


if __name__ == "__main__":
    SCENE_DIR.mkdir(parents=True, exist_ok=True)
    voices = load_voices()
    mics = microphone_positions()
    for distance in TARGET_DISTANCES:
        start = time.time()
        signals = build(distance, voices, mics)
        size = scene_path(distance).stat().st_size / 1e6
        print(f"{scene_path(distance).name} {signals.shape} {size:.0f} MB {time.time() - start:.0f} s", flush=True)
