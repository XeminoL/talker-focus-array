import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scene"))
sys.path.insert(0, str(ROOT / "model"))

from beam_fixed import REFERENCE_MIC, aligned_stoi, beam_fixed, design
from frontend import frontend_path
from geometry import microphone_positions, talker_positions
from params import AUDIO_RATE, ROOM_RT60, ROOM_SIZE, TARGET_DISTANCES
from voices import SPEAKERS, load_voices

DATA_DIR = Path(__file__).resolve().parent / "data"
LOADING = 0.01
TARGET_RMS = 0.08


def write_clip(path, samples):
    x = samples.astype(np.float64)
    x = x / (np.sqrt(np.mean(x**2)) + 1e-12) * TARGET_RMS
    sf.write(path, np.clip(x, -1.0, 1.0), AUDIO_RATE, subtype="PCM_16")


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    voices = load_voices()
    mics = microphone_positions()
    scenes = []
    for distance in TARGET_DISTANCES:
        start = time.time()
        audio = np.load(frontend_path(distance))
        tag = f"{distance:.1f}m"
        single = audio[REFERENCE_MIC].astype(np.float64)
        write_clip(DATA_DIR / f"{tag}_mic.wav", single)
        talkers = []
        for index, point in enumerate(talker_positions(distance)):
            entry = {"name": SPEAKERS[index], "position": [round(float(v), 3) for v in point], "stoi": {}}
            entry["stoi"]["mic"] = round(aligned_stoi(voices[index], single)[0], 3)
            for method in ("das", "mpdr"):
                if method == "das":
                    weights, shift = design("das-sinc", distance, talker=index)
                else:
                    weights, shift = design("mpdr", distance, talker=index, audio=audio, loading=LOADING)
                out = beam_fixed(audio, weights, shift).astype(np.float64)
                write_clip(DATA_DIR / f"{tag}_t{index}_{method}.wav", out)
                entry["stoi"][method] = round(aligned_stoi(voices[index], out)[0], 3)
            talkers.append(entry)
            print(f"{tag} talker {index} {entry['stoi']}", flush=True)
        scenes.append({"id": tag, "distance": distance, "talkers": talkers})
        print(f"{tag} done {time.time() - start:.0f} s", flush=True)
    demo = {
        "room": list(ROOM_SIZE),
        "rt60": ROOM_RT60,
        "rate": AUDIO_RATE,
        "reference_mic": REFERENCE_MIC,
        "mics": [[round(float(x), 3), round(float(y), 3)] for x, y, _ in mics.T],
        "scenes": scenes,
    }
    (DATA_DIR / "demo.js").write_text("window.DEMO = " + json.dumps(demo) + ";\n")


if __name__ == "__main__":
    main()
