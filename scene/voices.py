from pathlib import Path

import numpy as np
import soundfile as sf

from params import AUDIO_RATE, CLIP_SECONDS

SPEECH_DIR = Path(__file__).resolve().parent.parent / "data" / "speech"
SPEAKERS = ("bdl", "slt", "rms", "clb")


def load_voice(speaker):
    pieces = []
    for path in sorted((SPEECH_DIR / speaker).glob("*.wav")):
        samples, rate = sf.read(path)
        if rate != AUDIO_RATE:
            raise ValueError(f"{path.name} is {rate} Hz, expected {AUDIO_RATE}")
        pieces.append(samples)
    voice = np.concatenate(pieces)[: int(CLIP_SECONDS * AUDIO_RATE)]
    if len(voice) < CLIP_SECONDS * AUDIO_RATE:
        raise ValueError(f"{speaker} has only {len(voice) / AUDIO_RATE:.2f} s")
    return voice / np.sqrt(np.mean(voice**2))


def load_voices():
    return np.array([load_voice(s) for s in SPEAKERS])


if __name__ == "__main__":
    voices = load_voices()
    print("shape", voices.shape, "rate", AUDIO_RATE)
    for speaker, voice in zip(SPEAKERS, voices):
        print(f"{speaker} seconds {len(voice) / AUDIO_RATE:.2f} rms {np.sqrt(np.mean(voice**2)):.3f} peak {np.abs(voice).max():.2f}")