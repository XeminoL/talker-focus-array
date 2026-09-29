import subprocess
from pathlib import Path

import numpy as np
from pystoi import stoi

from cic_check import to_wsl
from frontend import frontend_path
from geometry import microphone_positions, talker_positions
from params import AUDIO_RATE, SPEED_OF_SOUND
from voices import load_voices

ROOT = Path(__file__).resolve().parent.parent
WEIGHT_DIR = ROOT / "build" / "weights"
DESIGNER = ROOT / "host" / "design_weights"
BEAM_TAPS = 64
BEAM_COEF_BITS = 18
OUT_BITS = 24
OUT_MAX = (1 << (OUT_BITS - 1)) - 1
OUT_MIN = -(1 << (OUT_BITS - 1))
REFERENCE_MIC = 27
EDGE = 1600


def write_scene(distance, path, talker=0):
    mics = microphone_positions()
    point = talker_positions(distance)[talker]
    lines = [f"mic {x:.6f} {y:.6f} {z:.6f}" for x, y, z in mics.T]
    lines += [f"target {point[0]:.6f} {point[1]:.6f} {point[2]:.6f}", f"rate {AUDIO_RATE}", f"speed {SPEED_OF_SOUND}"]
    path.write_text("\n".join(lines) + "\n")


def design(mode, distance, talker=0, audio=None, loading=None, taps=None, tag=""):
    WEIGHT_DIR.mkdir(parents=True, exist_ok=True)
    scene_file = WEIGHT_DIR / f"scene_{distance:.1f}m_t{talker}.txt"
    write_scene(distance, scene_file, talker)
    prefix = WEIGHT_DIR / f"{mode}{tag}_{distance:.1f}m_t{talker}"
    command = f"'{to_wsl(DESIGNER)}' {mode} '{to_wsl(scene_file)}' '{to_wsl(prefix)}'"
    if audio is not None:
        recording = WEIGHT_DIR / f"recording{tag}_{distance:.1f}m.bin"
        audio.astype("<i4").tofile(recording)
        command += f" '{to_wsl(recording)}' {loading}"
        if taps:
            command += f" {taps}"
    result = subprocess.run(["wsl", "bash", "-lc", command], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    raw = np.array([int(line, 16) for line in Path(f"{prefix}.hex").read_text().split()], dtype=np.int64)
    raw = np.where(raw >= 1 << (BEAM_COEF_BITS - 1), raw - (1 << BEAM_COEF_BITS), raw)
    shift = int(Path(f"{prefix}.shift").read_text())
    return raw.reshape(64, -1), shift


def beam_fixed(audio, weights, shift):
    total = np.zeros(audio.shape[1], dtype=np.int64)
    for channel, taps in enumerate(weights):
        total += np.convolve(audio[channel].astype(np.int64), taps)[: audio.shape[1]]
    return np.clip(total >> shift, OUT_MIN, OUT_MAX)


def aligned_stoi(clean, processed):
    lag = int(np.argmax(np.correlate(processed[: 4 * AUDIO_RATE], clean[: 4 * AUDIO_RATE - 400], mode="valid")))
    shifted = processed[lag : lag + len(clean)]
    count = min(len(clean), len(shifted)) - EDGE
    return stoi(clean[EDGE:count], shifted[EDGE:count], AUDIO_RATE), lag


if __name__ == "__main__":
    import sys

    voices = load_voices()
    loadings = [float(v) for v in sys.argv[1:]] or [0.01]
    print("distance  mic27   das   " + "  ".join(f"mpdr {v:g}" for v in loadings))
    for distance in (2.0, 4.0, 5.5):
        audio = np.load(frontend_path(distance))
        row = [aligned_stoi(voices[0], audio[REFERENCE_MIC].astype(float))[0]]
        weights, shift = design("das-sinc", distance)
        row.append(aligned_stoi(voices[0], beam_fixed(audio, weights, shift).astype(float))[0])
        for loading in loadings:
            weights, shift = design("mpdr", distance, audio=audio, loading=loading)
            row.append(aligned_stoi(voices[0], beam_fixed(audio, weights, shift).astype(float))[0])
        print(f"{distance:8.1f}  " + "  ".join(f"{v:.3f}" for v in row), flush=True)
