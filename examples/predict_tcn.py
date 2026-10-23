#!/usr/bin/env python3
"""Load the trained EMG pose TCN in PyTorch and predict: on a recorded folder, or live from the Myo.

    python examples/predict_tcn.py data/jose-lever                 # every take: per-pose accuracy, confusion
    python examples/predict_tcn.py --live data/jose-lever          # live Myo_EMG; the folder is your calibration

A per-driver model (the default from train_tcn.py) scales your EMG with your own calibration folder, so
pass the folder you recorded with `myo_gestures.py record` (or lever.py) while wearing the band as now.
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np

import emg_tcn as T

DEFAULT_MODEL = Path(__file__).resolve().parent / "models" / "emg_tcn.pt"


def on_folder(m: T.EMGTCN, folder: str) -> None:
    takes = T.load_folder(folder)
    if not takes:
        sys.exit(f"no Myo_EMG takes in {folder}")
    k = len(m.poses)
    confusion = np.zeros((k, k), dtype=int)
    for t in takes:
        p = m.probabilities(T.windows(t)).argmax(axis=1)
        np.add.at(confusion, (m.poses.index(t.label), p), 1)
    print(f"{len(takes)} takes, {confusion.sum()} windows of {m.window} samples\n")
    print("true \\ predicted  " + " ".join(f"{T.SHOWN[p]:>7s}" for p in m.poses) + "   correct")
    for i, pose in enumerate(m.poses):
        row = confusion[i]
        print(f"{T.SHOWN[pose]:>16s}  " + " ".join(f"{v:7d}" for v in row) + f"   {row[i] / max(row.sum(), 1):6.0%}")
    print(f"\naccuracy {np.trace(confusion) / confusion.sum():.0%} (chance {1 / k:.0%})")


def live(m: T.EMGTCN, stream: str) -> None:
    import pylsl
    print(f"Looking for the {stream} LSL stream …")
    found = []
    while not found:
        found = pylsl.resolve_byprop("name", stream, timeout=3.0)
    inlet = pylsl.StreamInlet(found[0], max_buflen=2)
    buf: deque = deque(maxlen=m.window)
    print("✓ streaming. Hold a pose; Ctrl+C to stop.\n")
    try:
        while True:
            chunk, _ = inlet.pull_chunk(timeout=0.0)
            buf.extend(chunk)
            if len(buf) == m.window:
                pose, p = m.predict(np.asarray(buf, dtype=float))
                bars = " ".join(f"{T.SHOWN[q]} {v:4.0%}" for q, v in zip(m.poses, p))
                print(f"\r  {T.SHOWN[pose]:8s} {p.max():4.0%}   {bars}   ", end="", flush=True)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", help="takes to predict, or (with --live) your calibration folder")
    ap.add_argument("--model", default=str(DEFAULT_MODEL))
    ap.add_argument("--live", action="store_true", help="predict from the live Myo_EMG stream")
    ap.add_argument("--stream", default="Myo_EMG")
    args = ap.parse_args()
    m = T.EMGTCN.load(args.model)
    if m.per_driver:
        m.calibrate(args.folder)
    print(f"model {args.model}: {m.info.get('norm', 'global')} min-max, trained on "
          f"{', '.join(m.info.get('drivers', {})) or '?'}")
    live(m, args.stream) if args.live else on_folder(m, args.folder)


if __name__ == "__main__":
    main()
