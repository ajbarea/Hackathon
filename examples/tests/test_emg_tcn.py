import numpy as np
import pytest

torch = pytest.importorskip("torch")

import emg_tcn as T  # noqa: E402
import train_tcn as TR  # noqa: E402


def write_take(folder, label, emg, rnd="2s", n=1):
    path = folder / f"{label}_20261023_120000_{rnd}_{n}_Myo_EMG.csv"
    head = (f"# team: t\n# label: {label}\n# sample_rate: 200.0\n# stream: Myo_EMG\n#\n"
            "timestamp," + ",".join(f"EMG_{i + 1}" for i in range(8)) + "\n")
    rows = "".join(f"{i / 200:.4f}," + ",".join(str(int(v)) for v in r) + "\n" for i, r in enumerate(emg))
    path.write_text(head + rows)
    return path


def test_loader_reads_label_round_and_eight_channels(tmp_path):
    emg = np.arange(400 * 8).reshape(400, 8) % 50
    write_take(tmp_path, "arm_up", emg, "5s")
    (tmp_path / "arm_up_20261023_120000_5s_1_Myo_IMU.csv").write_text("# label: arm_up\n")
    (t,) = T.load_folder(tmp_path)
    assert (t.label, t.duration, t.emg.shape) == ("arm_up", "5s", (400, 8))
    assert np.array_equal(t.emg, emg)


def test_windows_cut_the_ends_and_hop():
    t = T.Take("rest", np.zeros((400, 8)), "", "2s")       # 2 s: 0.5 s cut each end leaves 200 samples
    assert T.windows(t).shape == ((200 - T.WINDOW) // T.HOP + 1, T.WINDOW, 8)


def test_minmax_maps_the_training_range_to_plus_minus_one_and_clips_outliers():
    x = np.random.default_rng(0).uniform(-100, 100, size=(5000, 8))
    s = T.MinMax().fit(x)
    y = s(x)
    assert y.min() >= -2 and y.max() <= 2
    assert np.percentile(y, 0.5, axis=0) == pytest.approx(-1, abs=1e-6)
    assert np.percentile(y, 99.5, axis=0) == pytest.approx(1, abs=1e-6)
    assert s(np.full((1, 8), 1e6)).max() == 2


def test_the_network_is_causal():
    m = T.TCN().eval()
    x = torch.randn(1, 8, 60)
    with torch.inference_mode():
        a = m.blocks(x)
        x2 = x.clone()
        x2[:, :, 40:] = torch.randn(1, 8, 20) * 10          # change only the future
        b = m.blocks(x2)
    assert torch.allclose(a[:, :, :40], b[:, :, :40])
    assert not torch.allclose(a[:, :, 40:], b[:, :, 40:])
    assert T.receptive_field(5, (1, 2, 4)) >= T.WINDOW


def test_save_and_load_give_the_same_predictions(tmp_path):
    torch.manual_seed(0)
    model, scaler = T.TCN().eval(), T.MinMax(-np.ones(8) * 50, np.ones(8) * 50)
    path = tmp_path / "m.pt"
    T.save(path, model, scaler, TR.CONFIG, {"norm": "global"})
    x = np.random.default_rng(1).normal(0, 20, size=(3, T.WINDOW, 8))
    loaded = T.EMGTCN.load(path)
    direct = T.EMGTCN(model, scaler, list(T.POSES), T.WINDOW, {})
    assert np.allclose(loaded.probabilities(x), direct.probabilities(x), atol=1e-6)
    assert loaded.predict(x[0])[0] in T.POSES and not loaded.per_driver


def test_training_learns_separable_poses_and_keeps_the_best_epoch():
    rng = np.random.default_rng(0)
    amp = 5 + 55 * np.eye(len(T.POSES), 8)[:, :] + 55 * np.eye(len(T.POSES), 8, k=2)   # pose c: channels c, c+2
    def windows(n):
        y = np.repeat(np.arange(len(T.POSES)), n)
        return rng.normal(0, 1, size=(len(y), T.WINDOW, 8)) * amp[y][:, None, :], y
    (xtr, ytr), (xva, yva) = windows(60), windows(20)
    model, scaler, info = TR.train_one(xtr, ytr, xva, yva, seed=0, epochs=20)
    xte, yte = windows(20)
    with torch.inference_mode():
        p = np.asarray(model(torch.tensor(scaler(xte).tolist(), dtype=torch.float32)).argmax(-1).tolist())
    assert (p == yte).mean() > 0.9
    assert 1 <= info["best_epoch"] <= 20 and info["val_macro_f1"] > 0.9


def test_brake_scores_count_false_fires_and_misses():
    y = np.array([TR.BRAKE, TR.BRAKE, 0, 0, 0, 0])
    p = np.array([TR.BRAKE, 0, TR.BRAKE, 0, 0, 0])
    s = TR.scores(y, p)
    assert s["brake_false_fire"] == pytest.approx(0.25) and s["brake_miss"] == pytest.approx(0.5)
