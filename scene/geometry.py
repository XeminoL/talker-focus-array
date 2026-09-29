import numpy as np

from params import (
    ARRAY_CENTRE,
    ARRAY_COLS,
    ARRAY_PITCH,
    ARRAY_ROWS,
    INTERFERERS,
    ROOM_SIZE,
    TARGET_DISTANCES,
    TARGET_HEIGHT,
)

WALL_CLEARANCE = 0.3


def microphone_positions():
    xs = (np.arange(ARRAY_COLS) - (ARRAY_COLS - 1) / 2) * ARRAY_PITCH
    ys = (np.arange(ARRAY_ROWS) - (ARRAY_ROWS - 1) / 2) * ARRAY_PITCH
    grid = [(ARRAY_CENTRE[0] + x, ARRAY_CENTRE[1] + y, ARRAY_CENTRE[2]) for y in ys for x in xs]
    return np.array(grid).T


def target_position(distance):
    return np.array([ARRAY_CENTRE[0], ARRAY_CENTRE[1] + distance, TARGET_HEIGHT])


def talker_positions(distance):
    return np.array([target_position(distance), *INTERFERERS])


def inside_room(point):
    return all(WALL_CLEARANCE <= p <= size - WALL_CLEARANCE for p, size in zip(point, ROOM_SIZE))


if __name__ == "__main__":
    mics = microphone_positions()
    print("shape", mics.shape)
    print("first", mics[:, 0])
    print("last ", mics[:, -1])
    print("centre", mics.mean(axis=1))
    print("span  ", mics.max(axis=1) - mics.min(axis=1))
    for distance in TARGET_DISTANCES:
        for index, point in enumerate(talker_positions(distance)):
            gap = np.linalg.norm(point - np.array(ARRAY_CENTRE))
            print(f"distance {distance} talker {index} {point} from array {gap:.2f} m inside {inside_room(point)}")