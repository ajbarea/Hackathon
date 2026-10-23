"""A causal 1-D temporal convolutional network (TCN) that reads the lever pose from 200 ms of Myo EMG.

    pipeline: CSV loader → windows → gain scaling + Gaussian noise (training only) → min-max scaling
              (fit on the training drivers only) → TCN → saved checkpoint → EMGTCN.load(...).predict(window)

Train and evaluate with train_tcn.py; predict on a folder or the live Myo with predict_tcn.py.
Needs PyTorch (pip install torch; on an Intel Mac the last wheel is torch 2.2.2, with numpy<2).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch
from torch import nn

POSES = ("rest", "arm_up", "roll_left", "roll_right", "tip_down", "forward")     # EMG labels `record` writes
SHOWN = {"rest": "GO", "arm_up": "STOP", "roll_left": "LEFT", "roll_right": "RIGHT", "tip_down": "REVERSE",
         "forward": "BRAKE"}
SRATE = 200.0
WINDOW = 40          # samples: 200 ms at 200 Hz, as the controller's own EMG window
HOP = 10             # 50 ms between training windows: one per 20 Hz command
TRIM_S = 0.5         # cut from each end of a take (moving into and out of the pose), as gestures.py does


# ------------------------------------------------------------------------------------- CSV loader
@dataclass
class Take:
    label: str
    emg: np.ndarray          # (n, 8)
    path: str
    duration: str            # "2s", "3s" or "5s": which round of `record` it came from


def load_folder(folder: str | Path, labels: tuple[str, ...] = POSES) -> list[Take]:
    """Every Myo_EMG take in `folder` whose label is one of `labels` (lsl-web-viewer CSV: `# key: value`
    header lines, then timestamp + 8 channels)."""
    takes = []
    for path in sorted(Path(folder).glob("*_Myo_EMG.csv")):
        head, rows = {}, []
        with open(path) as f:
            for line in f:
                if line.startswith("#"):
                    key, _, value = line[1:].partition(":")
                    head[key.strip()] = value.strip()
                else:
                    rows = list(csv.reader([line] + f.readlines()))
                    break
        label = head.get("label", "").lower().split("-")[0]
        if label not in labels or head.get("stream", "Myo_EMG") != "Myo_EMG" or len(rows) < 2:
            continue
        data = np.asarray(rows[1:], dtype=float)[:, 1:9]                    # drop the timestamp column
        rnd = next((p for p in path.stem.split("_") if p.endswith("s") and p[:-1].isdigit()), "")
        takes.append(Take(label, data, str(path), rnd))
    return takes


def windows(take: Take, trim_s: float = TRIM_S, hop: int = HOP) -> np.ndarray:
    """(k, WINDOW, 8) overlapping windows over the steady middle of a take."""
    cut = round(trim_s * SRATE)
    body = take.emg[cut:len(take.emg) - cut] if len(take.emg) - 2 * cut >= WINDOW else take.emg
    starts = range(0, len(body) - WINDOW + 1, hop)
    return np.stack([body[i:i + WINDOW] for i in starts]) if len(starts) else np.zeros((0, WINDOW, 8))


def dataset(takes: list[Take]) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = [], []
    for t in takes:
        w = windows(t)
        xs.append(w)
        ys.append(np.full(len(w), POSES.index(t.label)))
    return np.concatenate(xs), np.concatenate(ys)


# ------------------------------------------------------------------------------------- scaling
@dataclass
class MinMax:
    """Per-channel min-max to [-1, 1]. The bounds are the 0.5th and 99.5th percentiles, so one spike
    doesn't set the scale; values beyond them are clipped at ±2."""
    lo: np.ndarray = field(default_factory=lambda: np.zeros(8))
    hi: np.ndarray = field(default_factory=lambda: np.ones(8))

    def fit(self, x: np.ndarray) -> "MinMax":
        flat = x.reshape(-1, x.shape[-1])
        self.lo, self.hi = np.percentile(flat, 0.5, axis=0), np.percentile(flat, 99.5, axis=0)
        return self

    def __call__(self, x: np.ndarray) -> np.ndarray:
        return np.clip(2 * (x - self.lo) / np.maximum(self.hi - self.lo, 1e-6) - 1, -2, 2)


def augment(x: np.ndarray, rng: np.random.Generator, gain: tuple[float, float] = (0.6, 1.6),
            noise: float = 0.05, spread: np.ndarray | None = None) -> np.ndarray:
    """Training-only: scale each window by one random gain (another person, a looser band) with a small
    per-channel jitter, then add Gaussian noise of `noise` × each channel's spread."""
    g = rng.uniform(*gain, size=(len(x), 1, 1)) * rng.uniform(0.9, 1.1, size=(len(x), 1, x.shape[-1]))
    s = spread if spread is not None else x.reshape(-1, x.shape[-1]).std(axis=0)
    return x * g + rng.normal(0, 1, size=x.shape) * noise * s


# ------------------------------------------------------------------------------------- model
class CausalBlock(nn.Module):
    """Two dilated causal convolutions with a residual connection: the output at time t sees only
    samples up to t."""

    def __init__(self, c_in: int, c_out: int, k: int, dilation: int, dropout: float):
        super().__init__()
        self.pad = (k - 1) * dilation
        self.c1 = nn.Conv1d(c_in, c_out, k, dilation=dilation)
        self.c2 = nn.Conv1d(c_out, c_out, k, dilation=dilation)
        self.drop = nn.Dropout(dropout)
        self.skip = nn.Conv1d(c_in, c_out, 1) if c_in != c_out else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.drop(torch.relu(self.c1(nn.functional.pad(x, (self.pad, 0)))))
        y = self.drop(torch.relu(self.c2(nn.functional.pad(y, (self.pad, 0)))))
        return torch.relu(y + self.skip(x))


class TCN(nn.Module):
    def __init__(self, channels: int = 8, hidden: int = 32, kernel: int = 5, dilations=(1, 2, 4),
                 classes: int = len(POSES), dropout: float = 0.1):
        super().__init__()
        blocks, c = [], channels
        for d in dilations:
            blocks.append(CausalBlock(c, hidden, kernel, d, dropout))
            c = hidden
        self.blocks = nn.Sequential(*blocks)
        self.head = nn.Linear(hidden, classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:        # x: (batch, time, channels)
        return self.head(self.blocks(x.transpose(1, 2))[:, :, -1])


def receptive_field(kernel: int, dilations) -> int:
    return 1 + 2 * (kernel - 1) * sum(dilations)


# ------------------------------------------------------------------------------------- save / load
def save(path: str | Path, model: TCN, scaler: MinMax, config: dict, info: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "config": config, "lo": scaler.lo.tolist(),
                "hi": scaler.hi.tolist(), "poses": list(POSES), "window": WINDOW, "srate": SRATE,
                "info": info}, path)


class EMGTCN:
    """A trained model for prediction: EMGTCN.load(path).predict(window) → (pose, probabilities)."""

    def __init__(self, model: TCN, scaler: MinMax, poses: list[str], window: int, info: dict):
        self.model, self.scaler, self.poses, self.window, self.info = model.eval(), scaler, poses, window, info

    @classmethod
    def load(cls, path: str | Path) -> "EMGTCN":
        ck = torch.load(path, map_location="cpu", weights_only=False)
        model = TCN(**ck["config"])
        model.load_state_dict(ck["state_dict"])
        return cls(model, MinMax(np.asarray(ck["lo"]), np.asarray(ck["hi"])), ck["poses"], ck["window"],
                   ck.get("info", {}))

    @property
    def per_driver(self) -> bool:
        return self.info.get("norm") == "driver"

    def calibrate(self, folder: str | Path) -> "EMGTCN":
        """Per-driver models: fit the min-max scaler on this driver's own calibration takes (labels unused)."""
        takes = load_folder(folder)
        if not takes:
            raise ValueError(f"no Myo_EMG takes in {folder}: record a calibration first")
        self.scaler = MinMax().fit(np.concatenate([windows(t) for t in takes]))
        return self

    def probabilities(self, x: np.ndarray) -> np.ndarray:
        """x: (window, 8) or (k, window, 8) raw EMG → (k, poses) probabilities."""
        x = np.asarray(x, dtype=np.float32)
        x = x[None] if x.ndim == 2 else x
        t = torch.tensor(self.scaler(x).tolist(), dtype=torch.float32)   # .tolist(): works across numpy 1/2
        with torch.inference_mode():
            return np.asarray(torch.softmax(self.model(t), dim=-1).tolist())

    def predict(self, window: np.ndarray) -> tuple[str, np.ndarray]:
        p = self.probabilities(window)[0]
        return self.poses[int(p.argmax())], p
