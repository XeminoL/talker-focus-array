import numpy as np
import pyroomacoustics as pra
from scipy.signal import fftconvolve

from params import AUDIO_RATE, ROOM_ABSORPTION, ROOM_SIZE

IMAGE_ORDER = 3
SCATTERING = 0.1
RAY_COUNT = 20000
RECEIVER_RADIUS = 0.3
ENERGY_FLOOR = 1e-6


def impulse_responses(talkers, mics, absorption=ROOM_ABSORPTION):
    room = pra.ShoeBox(
        ROOM_SIZE,
        fs=AUDIO_RATE,
        materials=pra.Material(absorption, SCATTERING),
        max_order=IMAGE_ORDER,
        ray_tracing=True,
        air_absorption=True,
    )
    room.set_ray_tracing(receiver_radius=RECEIVER_RADIUS, n_rays=RAY_COUNT, energy_thres=ENERGY_FLOOR)
    for point in talkers:
        room.add_source(point)
    room.add_microphone_array(pra.MicrophoneArray(mics, AUDIO_RATE))
    room.compute_rir()
    return room.rir


def render(voices, responses):
    length = voices.shape[1]
    mic_count = len(responses)
    out = np.zeros((len(voices), mic_count, length))
    for talker, voice in enumerate(voices):
        for mic in range(mic_count):
            out[talker, mic] = fftconvolve(voice, responses[mic][talker])[:length]
    return out


if __name__ == "__main__":
    import sys
    import time

    from geometry import microphone_positions, talker_positions
    from params import ARRAY_CENTRE
    from voices import load_voices

    start = time.time()
    mics = microphone_positions() if "array" in sys.argv else np.array([ARRAY_CENTRE]).T
    responses = impulse_responses(talker_positions(4.0), mics)
    voices = load_voices()
    signals = render(voices, responses)
    print("signals", signals.shape, f"{time.time() - start:.1f} s")
    for talker, rir in enumerate(responses[0]):
        rt60 = pra.experimental.measure_rt60(rir, fs=AUDIO_RATE)
        level = 10 * np.log10(np.mean(signals[talker, 0] ** 2))
        print(f"talker {talker} rir {len(rir) / AUDIO_RATE:.2f} s rt60 {rt60:.2f} s level {level:+.1f} dB")
