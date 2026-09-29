import subprocess
import sys
from pathlib import Path

import numpy as np

from cic import CIC_LATENCY, CIC_RATIO, SIGN, cic_exact
from params import DECIMATION

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scene"))

from build import scene_path
from pdm_build import pdm_path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "build" / "cic"
SAMPLES = 256000


def to_wsl(path):
    drive, rest = str(path).split(":", 1)
    return f"/mnt/{drive.lower()}{rest}".replace("\\", "/")


def run_rtl(bits):
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "cic_stimulus.txt").write_text("\n".join(str(b) for b in bits) + "\n")
    rtl = to_wsl(ROOT / "rtl" / "cic_decimator.v")
    tb = to_wsl(ROOT / "tb" / "cic_decimator_tb.v")
    command = f"cd '{to_wsl(WORK)}' && iverilog -g2005 -Wall -Pcic_decimator_tb.SAMPLES={len(bits)} -o sim '{rtl}' '{tb}' && vvp -n sim"
    result = subprocess.run(["wsl", "bash", "-lc", command], capture_output=True, text=True)
    warnings = [line for line in (result.stdout + result.stderr).splitlines() if "warning" in line.lower() or "error" in line.lower()]
    if result.returncode != 0:
        print(result.stdout, result.stderr)
        raise SystemExit(1)
    return np.loadtxt(WORK / "cic_rtl.txt", dtype=np.int64, ndmin=1), warnings


def loud_window(distance, mic):
    mixture = np.load(scene_path(distance))["signals"][:, mic, :].sum(axis=0)
    centre = int(np.argmax(np.abs(mixture))) * DECIMATION
    start = max(0, centre - SAMPLES // 2) // CIC_RATIO * CIC_RATIO
    bits = np.unpackbits(np.load(pdm_path(distance))["bits"][mic : mic + 1], axis=1)[0]
    return bits[start : start + SAMPLES]


def check(name, bits):
    rtl, warnings = run_rtl(bits)
    reference = cic_exact(bits, CIC_LATENCY)
    count = min(len(rtl), len(reference))
    mismatches = int(np.sum(rtl[:count] != reference[:count]))
    peak = int(np.abs(reference).max())
    print(f"{name:26} outputs {count:5d} mismatches {mismatches} peak {peak} ({peak / (SIGN - 1):.4f} of limit) warnings {len(warnings)}")
    for line in warnings:
        print("  ", line)


if __name__ == "__main__":
    first = np.unpackbits(np.load(pdm_path(4.0))["bits"][0:1], axis=1)[0, :SAMPLES]
    check("4.0 m mic 0 start", first)
    check("2.0 m mic 63 loudest", loud_window(2.0, 63))
    check("all ones", np.ones(CIC_RATIO * 40, dtype=np.uint8))
    check("all zeros", np.zeros(CIC_RATIO * 40, dtype=np.uint8))
