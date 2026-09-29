import numpy as np
import pyroomacoustics as pra

from geometry import talker_positions
from params import ARRAY_CENTRE, AUDIO_RATE, ROOM_RT60, ROOM_SIZE
from room import impulse_responses

ROUNDS = 5
TOLERANCE = 0.02


def measured_rt60(absorption):
    mics = np.array([ARRAY_CENTRE]).T
    responses = impulse_responses(talker_positions(4.0), mics, absorption)
    return float(np.median([pra.experimental.measure_rt60(r, fs=AUDIO_RATE) for r in responses[0]]))


def calibrate():
    absorption, _ = pra.inverse_sabine(ROOM_RT60, ROOM_SIZE)
    for round_index in range(ROUNDS):
        rt60 = measured_rt60(absorption)
        print(f"round {round_index} absorption {absorption:.4f} rt60 {rt60:.3f} s")
        if abs(rt60 - ROOM_RT60) / ROOM_RT60 < TOLERANCE:
            return absorption
        absorption *= rt60 / ROOM_RT60
    return absorption


if __name__ == "__main__":
    print(f"absorption {calibrate():.4f}")
