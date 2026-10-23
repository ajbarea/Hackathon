"""Drive L1's first gate from an off-line heading, with and without the gate assist, through the real sim.

Needs jackal-bridge --serve-site and the sim page open on ?course=L1-gates. Each trial: restart, drive at 0.6 m/s
turning at turn_w for turn_s, then straight, every command through armdrive.assist(); stop when gate 1 is passed,
when the robot is past it (x > -5), or after 14 s. Prints one JSON line per trial pair (gate-trial.json)."""
import json, sys, threading, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "examples"))
import armdrive as A
from websockets.sync.client import connect

BASE = "ws://localhost:8765"
latest = {}
def follow():
    with connect(BASE + "/state") as ws:
        for raw in ws:
            m = json.loads(raw)
            if m.get("type") == "state":
                latest["s"] = m
threading.Thread(target=follow, daemon=True).start()
cmd = connect(BASE + "/cmd")
def send(v, w, **kw):
    cmd.send(json.dumps({"type": "cmd", "v": v, "w": w, "source": "gate-trial", "t": time.time(), **kw}))

def trial(turn_w, turn_s, gate):
    send(0, 0, action="restart"); time.sleep(1.5)
    s0 = latest["s"]; c0 = s0.get("collisions", 0)
    t0 = time.monotonic(); notes = 0; v = 0.6
    while time.monotonic() - t0 < 14:
        s = latest.get("s", {})
        w_driver = turn_w if time.monotonic() - t0 < turn_s else 0.0
        v2, w2, note = A.assist(v, w_driver, s, gate=gate)
        notes += "gate" in note
        send(v2, w2)
        course = s.get("course") or {}
        if course.get("gates_passed", 0) >= 1 or (course.get("next_gate", 0) or 0) >= 1:
            break
        if s.get("pose", {}).get("x", -9) > -5.0:      # past gate 1's posts without passing it
            break
        time.sleep(0.05)
    s = latest["s"]; course = s.get("course") or {}
    send(0, 0)
    return {"passed": course.get("gates_passed", 0), "collisions": s.get("collisions", 0) - c0,
            "gate_ticks": notes, "y_end": round(s["pose"]["y"], 2), "secs": round(time.monotonic() - t0, 1)}

time.sleep(2)
for turn_w, turn_s in [(0.25, 1.0), (-0.25, 1.0), (0.35, 1.2), (-0.35, 1.2), (0.4, 1.5), (-0.4, 1.5)]:
    on, off = trial(turn_w, turn_s, True), trial(turn_w, turn_s, False)
    print(json.dumps({"turn_w": turn_w, "turn_s": turn_s, "gate_on": on, "gate_off": off}), flush=True)
