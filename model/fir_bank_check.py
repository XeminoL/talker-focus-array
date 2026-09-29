import subprocess
import time
from pathlib import Path

import numpy as np

from cic import CIC_LATENCY, CIC_RATIO, cic_fast
from cic_check import to_wsl
from fir_fixed import FIR_DATA_BITS, export_coefficients, fir_fixed, reduce_cic, to_hex
from params import DECIMATION
from pdm_build import pdm_path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "build" / "fir_bank"
CHANNELS = 64
FRAMES = 300


def channel_inputs(distance, frames):
    packed = np.load(pdm_path(distance))["bits"]
    first = np.unpackbits(packed[0:1], axis=1)[0]
    loud = int(np.argmax(np.abs(reduce_cic(cic_fast(first, CIC_LATENCY)))))
    start_frame = max(0, loud - frames // 2) // 3 * 3
    count = (start_frame + frames) * CIC_RATIO
    rows = []
    for mic in range(CHANNELS):
        bits = np.unpackbits(packed[mic : mic + 1], axis=1)[0, :count]
        rows.append(reduce_cic(cic_fast(bits, CIC_LATENCY))[start_frame : start_frame + frames])
    return np.array(rows)


def run_rtl(inputs):
    WORK.mkdir(parents=True, exist_ok=True)
    stream = inputs.T.reshape(-1)
    (WORK / "fir_bank_stimulus.hex").write_text("\n".join(to_hex(stream, FIR_DATA_BITS)) + "\n")
    rtl = to_wsl(ROOT / "rtl" / "fir_bank.v")
    tb = to_wsl(ROOT / "tb" / "fir_bank_tb.v")
    coefficients = to_wsl(ROOT / "rtl" / "fir_coefficients.hex")
    command = (
        f"cd '{to_wsl(WORK)}' && cp '{coefficients}' . && "
        f"iverilog -g2005 -Wall -Pfir_bank_tb.FRAMES={inputs.shape[1]} -o sim '{rtl}' '{tb}' && vvp -n sim"
    )
    result = subprocess.run(["wsl", "bash", "-lc", command], capture_output=True, text=True)
    text = result.stdout + result.stderr
    warnings = [line for line in text.splitlines() if "warning" in line.lower() or "error" in line.lower()]
    if result.returncode != 0:
        print(text)
        raise SystemExit(1)
    return np.loadtxt(WORK / "fir_bank_rtl.txt", dtype=np.int64, ndmin=2), warnings


if __name__ == "__main__":
    taps = export_coefficients()
    start = time.time()
    inputs = channel_inputs(2.0, FRAMES)
    print(f"inputs {inputs.shape} prepared in {time.time() - start:.0f} s")
    start = time.time()
    rows, warnings = run_rtl(inputs)
    print(f"rtl {len(rows)} outputs in {time.time() - start:.0f} s warnings {len(warnings)}")
    for line in warnings[:5]:
        print("  ", line)
    order_ok = bool(np.all(rows[:, 0] == np.tile(np.arange(CHANNELS), len(rows) // CHANNELS)))
    print("channel order 0..63 repeating", order_ok)
    mismatches = 0
    compared = 0
    for channel in range(CHANNELS):
        reference = fir_fixed(inputs[channel], taps)
        got = rows[rows[:, 0] == channel, 1]
        count = min(len(got), len(reference))
        compared += count
        mismatches += int(np.sum(got[:count] != reference[:count]))
    print(f"compared {compared} samples over {CHANNELS} channels mismatches {mismatches}")
