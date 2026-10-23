<!-- budget: 760 words -->
# EMG pose TCN

A causal 1-D temporal convolutional network (TCN) that reads the six lever poses from 200 ms of Myo EMG,
compared with the controller's linear discriminant (LDA) on the same takes.

```
CSV loader → 200 ms windows → gain scaling + Gaussian noise (training only) → min-max scaling (fit on
training data only) → TCN (3 dilated causal blocks, 32 channels) → best epoch saved → loaded in PyTorch
```

## Run it

Needs PyTorch (`pip install torch`). On an Intel Mac the last wheel is torch 2.2.2, which needs numpy<2:
`uv run --python 3.11 --with "torch==2.2.2" --with "numpy<2" --with pylsl --with websockets python …`.
Unzip both dataset releases into `data/` first.

```bash
python examples/train_tcn.py                          # evaluate (3 tests below) and save models/emg_tcn.pt
python examples/train_tcn.py --personal data/ben-lever   # one person's model from their calibration
python examples/predict_tcn.py data/ben-lever            # load in PyTorch: per-pose accuracy on a folder
python examples/predict_tcn.py --live data/ben-lever     # live from the Myo (publisher running)
```

## What we measured (2026-10-23)

Four drivers (aj, j, k, x), 3 seeds per held-out driver, from `models/emg_tcn_eval.json`. Each cell is the median across drivers of each
driver's median over seeds, with the range across drivers. Chance is 0.17.

- **cross-global**: trained on the other three drivers, one scaler fit on their windows.
- **cross-driver**: the same, but each driver scaled by their own calibration.
- **personal**: one driver's own calibration only: 5 s takes train, 2 s pick the epoch, 3 s are the test.

| Test | Model | Accuracy | Macro-F1 | Brake false-fire | Brake miss |
|---|---|---|---|---|---|
| cross-global | TCN | 0.26 (0.17–0.51) | 0.23 (0.13–0.43) | 0.13 (0.00–0.29) | 0.39 (0.00–1.00) |
| cross-global | LDA | 0.24 (0.19–0.32) | 0.19 (0.14–0.26) | 0.01 (0.00–0.23) | 0.05 (0.00–1.00) |
| cross-driver | TCN | 0.17 (0.16–0.43) | 0.08 (0.05–0.42) | 0.60 (0.05–0.98) | 0.04 (0.00–0.04) |
| cross-driver | LDA | 0.32 (0.29–0.34) | 0.27 (0.18–0.29) | 0.02 (0.00–0.16) | 0.13 (0.00–0.25) |
| personal | TCN | 0.68 (0.45–0.89) | 0.69 (0.38–0.89) | 0.00 (0.00–0.01) | 0.00 (0.00–0.04) |
| personal | LDA | 0.85 (0.76–0.88) | 0.86 (0.70–0.88) | 0.00 (0.00–0.00) | 0.00 (0.00–0.00) |

Drivers aj, j, k, x; augmentation gain [0.6, 1.6], noise 0.05; TCN {'hidden': 32, 'kernel': 5, 'dilations': [1, 2, 4], 'dropout': 0.1}, torch 2.2.2.

Without gain scaling (`--gain 1,1`, noise kept), from `models/emg_tcn_eval_nogain.json`:

| Test | Model | Accuracy | Macro-F1 | Brake false-fire | Brake miss |
|---|---|---|---|---|---|
| cross-global | TCN | 0.24 (0.17–0.50) | 0.22 (0.13–0.43) | 0.13 (0.00–0.26) | 0.48 (0.00–1.00) |
| cross-global | LDA | 0.24 (0.19–0.32) | 0.19 (0.14–0.26) | 0.01 (0.00–0.23) | 0.05 (0.00–1.00) |
| cross-driver | TCN | 0.33 (0.23–0.38) | 0.25 (0.15–0.32) | 0.03 (0.01–0.35) | 0.01 (0.00–0.09) |
| cross-driver | LDA | 0.32 (0.29–0.34) | 0.27 (0.18–0.29) | 0.02 (0.00–0.16) | 0.13 (0.00–0.25) |
| personal | TCN | 0.61 (0.37–0.83) | 0.62 (0.33–0.82) | 0.00 (0.00–0.00) | 0.00 (0.00–0.28) |
| personal | LDA | 0.85 (0.76–0.88) | 0.86 (0.70–0.88) | 0.00 (0.00–0.00) | 0.00 (0.00–0.00) |

Drivers aj, j, k, x; augmentation gain [1.0, 1.0], noise 0.05; TCN {'hidden': 32, 'kernel': 5, 'dilations': [1, 2, 4], 'dropout': 0.1}, torch 2.2.2.

## What it means

- **The simple model wins on our data.** With 2.5 minutes per person, the LDA on 16 hand-picked features
  beats the TCN on each person's own data, and neither generalises well to a driver it has never seen.
- **Gain scaling helps one setup and hurts another.** Per-driver scaling already evens out how strong each
  person's EMG is; random gain on top of it blurred the poses (new-driver accuracy 0.17 with it, 0.33
  without, and brake false-fires 0.60 against 0.03). Personal models did better with it (0.68 against 0.61).
- **The EMG only has one job in lever mode.** The arm-angle sensor reads GO, STOP, LEFT, RIGHT and REVERSE
  exactly; EMG decides only BRAKE. On held-out takes the personal LDA brake made no false fires and no
  misses, so the controller keeps it.
- **Where a TCN could win:** many more people. Pretraining on a multi-person Myo dataset and fine-tuning on
  each calibration is the usual route; the UCI "EMG data for gestures" set (36 people, CC BY 4.0) has
  rest and fist, the two poses that matter for the brake.

Code: `emg_tcn.py` (loader, scaler, augmentation, model, save/load), `train_tcn.py`, `predict_tcn.py`.
Tests: `pytest examples/tests/test_emg_tcn.py` (skipped without PyTorch).
