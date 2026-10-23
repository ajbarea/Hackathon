#!/usr/bin/env python3
"""Train the EMG pose TCN, test it on a driver it has never seen, and save the best model.

    python examples/train_tcn.py                       # the default drivers below, 3 seeds per fold
    python examples/train_tcn.py --driver aj=data/AJ-lever-v2,data/AJ-lever-v3 --driver ben=data/ben-lever

Leave-one-driver-out: for each driver, train on everyone else and test on that driver's takes. The best
epoch is picked on the training drivers' 3 s takes (never on the test driver). The training drivers'
takes also train two linear (LDA) baselines on the controller's EMG features: 6 poses, and the brake
on its own (as armdrive.train_brake does).
Then a final model trains on every driver and is saved with its scaler (examples/models/emg_tcn.pt).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

import emg_tcn as T
import gestures as G

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DRIVERS = {                    # the two dataset releases, unzipped into data/
    "aj": ["data/AJ-myo-lever-dataset/session1", "data/AJ-myo-lever-dataset/session2"],
    "j": ["data/team-myo-lever-dataset-2026-10-23/j-lever"],
    "k": ["data/team-myo-lever-dataset-2026-10-23/k-lever"],   # k-lever-first left out: its BRAKE shows no fist
    "x": ["data/team-myo-lever-dataset-2026-10-23/x-lever"],
}
BRAKE = T.POSES.index("forward")
CONFIG = {"hidden": 32, "kernel": 5, "dilations": [1, 2, 4], "dropout": 0.1}
AUGMENT = {"gain": (0.6, 1.6), "noise": 0.05}     # training-only gain scaling and Gaussian noise


def macro_f1(y: np.ndarray, p: np.ndarray, k: int = len(T.POSES)) -> float:
    f = []
    for c in range(k):
        tp, fp, fn = np.sum((p == c) & (y == c)), np.sum((p == c) & (y != c)), np.sum((p != c) & (y == c))
        f.append(2 * tp / max(2 * tp + fp + fn, 1))
    return float(np.mean(f))


def scores(y: np.ndarray, p: np.ndarray, brake_pred: np.ndarray | None = None) -> dict:
    """6-pose accuracy and macro-F1, plus the brake: how often it fires on a non-brake window, how often it
    misses a real one."""
    b = (p == BRAKE) if brake_pred is None else brake_pred
    out = {"brake_false_fire": float(b[y != BRAKE].mean()), "brake_miss": float(1 - b[y == BRAKE].mean())}
    if brake_pred is None:
        out |= {"accuracy": float((p == y).mean()), "macro_f1": macro_f1(y, p)}
    return out


def train_one(xtr, ytr, xva, yva, seed: int, epochs: int, prescaled: bool = False,
              log=None) -> tuple[T.TCN, T.MinMax, dict]:
    """prescaled: the windows were already min-max scaled per driver, so the model's own scaler is the
    identity."""
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)
    scaler = T.MinMax(-np.ones(8), np.ones(8)) if prescaled else T.MinMax().fit(xtr)
    spread = xtr.reshape(-1, 8).std(axis=0)
    model = T.TCN(**CONFIG)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-3)
    loss_fn = nn.CrossEntropyLoss()
    xv = torch.tensor(scaler(xva).tolist(), dtype=torch.float32)
    best = {"f1": -1.0, "epoch": -1, "state": None}
    for epoch in range(epochs):
        model.train()
        order = rng.permutation(len(xtr))
        for i in range(0, len(order), 128):
            idx = order[i:i + 128]
            xb = scaler(T.augment(xtr[idx], rng, AUGMENT["gain"], AUGMENT["noise"], spread))
            xb = torch.tensor(xb.tolist(), dtype=torch.float32)
            yb = torch.tensor(ytr[idx].tolist())
            opt.zero_grad()
            loss_fn(model(xb), yb).backward()
            opt.step()
        model.eval()
        with torch.inference_mode():
            pv = np.asarray(model(xv).argmax(-1).tolist())
        f1 = macro_f1(yva, pv)
        if f1 > best["f1"]:
            best = {"f1": f1, "epoch": epoch, "state": {k: v.clone() for k, v in model.state_dict().items()}}
        if log:
            log(f"    epoch {epoch + 1:2d}  val macro-F1 {f1:.3f}" + ("  *" if best["epoch"] == epoch else ""))
    model.load_state_dict(best["state"])
    return model.eval(), scaler, {"val_macro_f1": best["f1"], "best_epoch": best["epoch"] + 1}


def lda_baselines(xtr: np.ndarray, ytr: np.ndarray, xte: np.ndarray, yte: np.ndarray) -> tuple[dict, dict]:
    ftr, fte = np.array([G.features(w) for w in xtr]), np.array([G.features(w) for w in xte])
    poses = G.LDA().fit(ftr, [T.POSES[i] for i in ytr])
    p = np.array([T.POSES.index(c) for c in poses.predict(fte)])
    brake = G.LDA().fit(ftr, ["forward" if i == BRAKE else "rest" for i in ytr])   # as armdrive.train_brake
    b = np.array([c == "forward" for c in brake.predict(fte)])
    return scores(yte, p), scores(yte, p, b)


def summary(vals: list[float]) -> str:
    return f"{np.median(vals):.2f}" + (f" ({min(vals):.2f} to {max(vals):.2f})" if len(vals) > 1 else "")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--driver", action="append", metavar="NAME=FOLDER[,FOLDER]",
                    help="a driver and their calibration folder(s); repeat (default: the dataset releases)")
    ap.add_argument("--seeds", type=int, default=3, help="training runs per held-out driver (default %(default)s)")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--out", default=str(ROOT / "examples/models/emg_tcn.pt"))
    ap.add_argument("--gain", default="0.6,1.6", help="augmentation gain range LO,HI (1,1 = off; default %(default)s)")
    ap.add_argument("--noise", type=float, default=0.05, help="augmentation noise × channel spread (default %(default)s)")
    ap.add_argument("--report", metavar="JSON", help="print the results table of a finished run and exit")
    ap.add_argument("--personal", metavar="FOLDER",
                    help="train one person's model from their own calibration folder instead (5 s takes train, "
                         "2 s pick the epoch, 3 s are the reported test); saves models/emg_tcn_<folder>.pt")
    ap.add_argument("--skip-eval", action="store_true", help="only train and save the final model")
    ap.add_argument("--norm", choices=("driver", "global"), default="global",
                    help="the saved model's min-max: per driver from their own calibration, or one global scaler")
    args = ap.parse_args()
    AUGMENT.update(gain=tuple(float(g) for g in args.gain.split(",")), noise=args.noise)
    if args.report:
        return print(report(json.loads(Path(args.report).read_text())))
    if args.personal:
        return personal(Path(args.personal), args)

    spec = ({n: f.split(",") for n, f in (d.split("=", 1) for d in args.driver)} if args.driver
            else DEFAULT_DRIVERS)
    drivers = {n: [t for f in folders for t in T.load_folder(ROOT / f if not Path(f).is_absolute() else f)]
               for n, folders in spec.items()}
    for n, takes in drivers.items():
        have = {p: sum(t.label == p for t in takes) for p in T.POSES}
        print(f"{n}: {len(takes)} takes " + " ".join(f"{T.SHOWN[p]} {k}" for p, k in have.items()))
        if not all(have.values()):
            raise SystemExit(f"{n} is missing a pose: record all six")
    print(f"TCN {CONFIG}, receptive field {T.receptive_field(CONFIG['kernel'], CONFIG['dilations'])} samples "
          f"(window {T.WINDOW})\n")

    results = {}
    for mode in [] if args.skip_eval else MODES:
        print(f"── {mode}: {MODES[mode]}")
        results[mode] = evaluate(mode, drivers, args.seeds, args.epochs)

    # the model to use: every driver, best epoch on their 3 s takes, best of the seeds on that
    norm = args.norm
    data = {n: prescale(ts) if norm == "driver" else T.dataset(ts) for n, ts in drivers.items()}
    tr, va = zip(*(split_xy(drivers[n], data[n]) for n in drivers))
    (xtr, ytr), (xva, yva) = stack(tr), stack(va)
    model, scaler, info = max((train_one(xtr, ytr, xva, yva, s, args.epochs, norm == "driver")
                               for s in range(args.seeds)), key=lambda m: m[2]["val_macro_f1"])
    info |= {"norm": norm, "augment": AUGMENT, "drivers": spec, "results": results, "config": CONFIG,
             "torch": torch.__version__}
    T.save(args.out, model, scaler, CONFIG, info)
    Path(args.out).with_suffix(".json").write_text(json.dumps(info, indent=2))
    print(f"\nsaved {args.out} ({norm} min-max; val macro-F1 {info['val_macro_f1']:.3f}, epoch "
          f"{info['best_epoch']}); results in {Path(args.out).with_suffix('.json').name}")


def personal(folder: Path, args: argparse.Namespace) -> None:
    takes = T.load_folder(folder)
    if not all(any(t.label == p for t in takes) for p in T.POSES):
        raise SystemExit(f"{folder} is missing a pose: record all six")
    x, y = T.dataset(takes)
    rounds = np.concatenate([np.full(len(T.windows(t)), t.duration) for t in takes])
    (xtr, ytr), (xva, yva), (xte, yte) = ((x[rounds == r], y[rounds == r]) for r in ("5s", "2s", "3s"))
    model, scaler, info = max((train_one(xtr, ytr, xva, yva, s, args.epochs) for s in range(args.seeds)),
                              key=lambda m: m[2]["val_macro_f1"])
    with torch.inference_mode():
        p = np.asarray(model(torch.tensor(scaler(xte).tolist(), dtype=torch.float32)).argmax(-1).tolist())
    info |= {"norm": "global", "augment": AUGMENT, "drivers": {folder.name: [str(folder)]},
             "test_3s": scores(yte, p), "config": CONFIG, "torch": torch.__version__}
    out = Path(args.out).with_name(f"emg_tcn_{folder.name}.pt")
    T.save(out, model, scaler, CONFIG, info)
    t = info["test_3s"]
    print(f"{folder.name}: on the 3 s takes it never trained on, accuracy {t['accuracy']:.2f}, macro-F1 "
          f"{t['macro_f1']:.2f}, brake false-fire {t['brake_false_fire']:.2f}, miss {t['brake_miss']:.2f} → {out}")


def report(info: dict) -> str:
    """Markdown: per mode, the median (range over drivers) of each driver's median over seeds."""
    def cell(vals):
        return f"{np.median(vals):.2f} ({min(vals):.2f}–{max(vals):.2f})"
    lines = ["| Test | Model | Accuracy | Macro-F1 | Brake false-fire | Brake miss |", "|---|---|---|---|---|---|"]
    for mode, folds in info["results"].items():
        tcn = {k: [float(np.median([r[k] for r in f["tcn"]])) for f in folds]
               for k in ("accuracy", "macro_f1", "brake_false_fire", "brake_miss")}
        lda = {k: [f["lda"][k] for f in folds] for k in ("accuracy", "macro_f1")}
        lb = {k: [f["lda_brake"][k] for f in folds] for k in ("brake_false_fire", "brake_miss")}
        lines.append(f"| {mode} | TCN | {cell(tcn['accuracy'])} | {cell(tcn['macro_f1'])} | "
                     f"{cell(tcn['brake_false_fire'])} | {cell(tcn['brake_miss'])} |")
        lines.append(f"| {mode} | LDA | {cell(lda['accuracy'])} | {cell(lda['macro_f1'])} | "
                     f"{cell(lb['brake_false_fire'])} | {cell(lb['brake_miss'])} |")
    a = info.get("augment", {"gain": [0.6, 1.6], "noise": 0.05})
    return "\n".join(lines) + (f"\n\nDrivers {', '.join(info['drivers'])}; augmentation gain {a['gain']}, "
                               f"noise {a['noise']}; TCN {info['config']}, torch {info['torch']}.")


MODES = {
    "cross-global": "train on the other drivers, one min-max scaler fit on their windows",
    "cross-driver": "train on the other drivers, each driver min-max scaled by their own calibration",
    "personal": "one driver only: train on their 5 s takes, pick the epoch on 2 s, test on 3 s",
}


def prescale(takes: list[T.Take]) -> tuple[np.ndarray, np.ndarray]:
    """One driver's windows, min-max scaled by a scaler fit on that driver's own calibration."""
    x, y = T.dataset(takes)
    return T.MinMax().fit(x)(x), y


def split_xy(takes: list[T.Take], xy, val: str = "3s"):
    """(train, val) windows, split by whole take: takes of the `val` round validate."""
    x, y = xy
    rounds = np.concatenate([np.full(len(T.windows(t)), t.duration) for t in takes])
    return (x[rounds != val], y[rounds != val]), (x[rounds == val], y[rounds == val])


def stack(parts):
    return np.concatenate([p[0] for p in parts]), np.concatenate([p[1] for p in parts])


def evaluate(mode: str, drivers: dict[str, list[T.Take]], seeds: int, epochs: int) -> list[dict]:
    pre = mode != "cross-global"
    data = {n: prescale(ts) if pre else T.dataset(ts) for n, ts in drivers.items()}
    folds = []
    for held in drivers:
        if mode == "personal":
            x, y = data[held]
            rounds = np.concatenate([np.full(len(T.windows(t)), t.duration) for t in drivers[held]])
            (xtr, ytr), (xva, yva), (xte, yte) = ((x[rounds == r], y[rounds == r]) for r in ("5s", "2s", "3s"))
            lda_x, lda_y = np.concatenate([xtr, xva]), np.concatenate([ytr, yva])
        else:
            tr, va = zip(*(split_xy(drivers[n], data[n]) for n in drivers if n != held))
            (xtr, ytr), (xva, yva), (xte, yte) = stack(tr), stack(va), data[held]
            lda_x, lda_y = np.concatenate([xtr, xva]), np.concatenate([ytr, yva])
        runs = []
        for seed in range(seeds):
            t0 = time.time()
            model, scaler, info = train_one(xtr, ytr, xva, yva, seed, epochs, pre)
            with torch.inference_mode():
                p = np.asarray(model(torch.tensor(scaler(xte).tolist(), dtype=torch.float32)).argmax(-1).tolist())
            runs.append({**scores(yte, p), **info, "seed": seed, "secs": round(time.time() - t0, 1)})
        lda, lda_brake = lda_baselines(lda_x, lda_y, xte, yte)
        folds.append({"driver": held, "test_windows": int(len(yte)), "tcn": runs, "lda": lda,
                      "lda_brake": lda_brake})
        print(f"  {held}: TCN accuracy {summary([r['accuracy'] for r in runs])}, macro-F1 "
              f"{summary([r['macro_f1'] for r in runs])}, brake false-fire "
              f"{summary([r['brake_false_fire'] for r in runs])}, miss {summary([r['brake_miss'] for r in runs])}"
              f"\n  {' ' * len(held)}  LDA accuracy {lda['accuracy']:.2f}, macro-F1 {lda['macro_f1']:.2f}; "
              f"LDA brake false-fire {lda_brake['brake_false_fire']:.2f}, miss {lda_brake['brake_miss']:.2f}",
              flush=True)
    return folds


if __name__ == "__main__":
    main()
