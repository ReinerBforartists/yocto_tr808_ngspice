#!/usr/bin/env python3
"""Convert a node column of tr808_full_nodes.txt (NGSpice `wrdata`) to a WAV file.

    python scripts/nodes_to_wav.py                      # all nodes -> wav/<node>.wav
    python scripts/nodes_to_wav.py --node sd_out        # one node
    python scripts/nodes_to_wav.py --node u1a_out --rate 96000 --no-normalize

Needs only numpy. The node names are read from the `wrdata` line of
tr808_full.cir (wrdata writes a time column plus a value column per vector).
The transient uses an adaptive time grid, so each output sample is the exact
mean of the piecewise-linear waveform over its 1/rate interval (box filter).
"""
import argparse
import re
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent


def node_names(cir):
    for line in cir.read_text(errors="replace").splitlines():
        if line.lstrip().lower().startswith("wrdata"):
            return re.findall(r"v\(([^)]+)\)", line, flags=re.I)
    raise SystemExit(f"no wrdata line found in {cir}")


def resample(t, y, rate):
    """Mean of the piecewise-linear signal over each 1/rate interval."""
    n = int(np.floor((t[-1] - t[0]) * rate))
    edges = t[0] + np.arange(n + 1) / rate
    seg = np.diff(t)
    cum = np.concatenate(([0.0], np.cumsum(0.5 * (y[1:] + y[:-1]) * seg)))
    # integral of the linear interpolant at the edges
    i = np.clip(np.searchsorted(t, edges, side="right") - 1, 0, len(t) - 2)
    dt = edges - t[i]
    slope = (y[i + 1] - y[i]) / np.where(seg[i] > 0, seg[i], 1.0)
    integ = cum[i] + y[i] * dt + 0.5 * slope * dt * dt
    return np.diff(integ) * rate


def write_wav(path, x, rate):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nodes-file", type=Path, default=ROOT / "tr808_full_nodes.txt")
    ap.add_argument("--cir", type=Path, default=ROOT / "tr808_full.cir")
    ap.add_argument("--node", action="append", help="node name (repeatable); default: all columns")
    ap.add_argument("--rate", type=int, default=48000, help="output sample rate in Hz (default 48000)")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "wav")
    ap.add_argument("--no-normalize", action="store_true",
                    help="write volts as full scale = 1 V instead of peak-normalizing to -1 dBFS")
    ap.add_argument("--start", type=float, default=0.0,
                    help="drop the first START seconds (power-up transient of the uic start)")
    ap.add_argument("--keep-dc", action="store_true", help="do not remove the mean (DC offset)")
    a = ap.parse_args()

    names = node_names(a.cir)
    want = a.node or names
    for n in want:
        if n not in names:
            raise SystemExit(f"unknown node '{n}'; available: {', '.join(names)}")

    cols = [c for n in want for c in (2 * names.index(n), 2 * names.index(n) + 1)]
    data = np.loadtxt(a.nodes_file, usecols=sorted(set(cols)), ndmin=2)
    pos = {c: i for i, c in enumerate(sorted(set(cols)))}

    for n in want:
        k = names.index(n)
        t, v = data[:, pos[2 * k]], data[:, pos[2 * k + 1]]
        keep = np.concatenate(([True], np.diff(t) > 0))  # drop duplicate time points
        x = resample(t[keep], v[keep], a.rate)[int(a.start * a.rate):]
        if not a.keep_dc:
            x = x - x.mean()
        peak = np.abs(x).max()
        if not a.no_normalize and peak > 0:
            x = x / peak * 10 ** (-1 / 20)
        elif peak > 1:
            print(f"{n}: peak {peak:.3g} V clips at 1 V full scale")
        write_wav(a.out_dir / f"{n}.wav", x, a.rate)
        print(f"{n}: {len(x) / a.rate:.3f} s, peak {peak:.4g} V -> {a.out_dir / (n + '.wav')}")


if __name__ == "__main__":
    main()
