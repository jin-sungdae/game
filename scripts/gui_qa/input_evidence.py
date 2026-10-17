"""Conservative offline classifier for a single recorded native-input trial.

Collector attestations are evidence inputs, not replaced by inferred success.
This module never opens windows, sends input, or changes application state.
"""
import argparse
import json
import math

KINDS = {"transparent", "character", "boundary", "button", "drag"}
SOURCES = {"receiver", "luma-monitor"}


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def analyze_trial(trial):
    counts = {"receiver": {"down": 0, "up": 0, "drag": 0},
              "luma-monitor": {"down": 0, "up": 0, "drag": 0}, "actions": 0}

    def result(status, *reasons):
        return {"status": status, "reasons": list(reasons), "counts": counts}

    if not isinstance(trial, dict):
        return result("NOT_VERIFIED", "Trial must be an object")
    focus = trial.get("focus", {})
    if isinstance(focus, dict) and any(integer(focus.get(key), 1) for key in ("activations", "keyWindows")):
        return result("FAIL", "Observed LUMA activation or key-window acquisition")
    preflight = trial.get("preflight", {})
    if isinstance(preflight, dict) and preflight.get("status") == "GUI_ENVIRONMENT_BLOCKED":
        return result("GUI_ENVIRONMENT_BLOCKED", "Preflight could not establish a safe GUI environment")
    if trial.get("version") != 1 or type(trial.get("version")) is not int or not isinstance(trial.get("kind"), str) or trial.get("kind") not in KINDS:
        return result("NOT_VERIFIED", "Unsupported version or trial kind")
    if not isinstance(preflight, dict) or preflight.get("status") != "READY":
        return result("NOT_VERIFIED", "Preflight is not verified")
    if trial.get("runtimeSafe") is not True or trial.get("completed") is not True:
        return result("NOT_VERIFIED", "Safe runtime or trial completion is unverified")
    if (not isinstance(focus, dict) or focus.get("complete") is not True
            or any(not integer(focus.get(k)) for k in ("activations", "keyWindows"))):
        return result("NOT_VERIFIED", "Full valid focus audit is required")
    interval = trial.get("interval", {})
    if (not isinstance(interval, dict) or not number(interval.get("start"))
            or not number(interval.get("end")) or interval["start"] >= interval["end"]):
        return result("NOT_VERIFIED", "Invalid trial interval")
    start, end = interval["start"], interval["end"]
    identity = trial.get("identity", {})
    keys = ("lumaPid", "lumaWindowId", "receiverPid", "receiverWindowId")
    if (not isinstance(identity, dict) or any(not integer(identity.get(k), 1) for k in keys)
            or identity["lumaPid"] == identity["receiverPid"]
            or identity["lumaWindowId"] == identity["receiverWindowId"]):
        return result("NOT_VERIFIED", "Missing or ambiguous process/window identity")
    coverage = trial.get("coverage", {})
    if not isinstance(coverage, dict) or any(coverage.get(k) is not True for k in ("complete", "geometryStable", "receiverFrontmost", "monitorInstalled")):
        return result("NOT_VERIFIED", "Continuous recording/input/geometry coverage is required")
    coordinate = trial.get("coordinate", {})
    if (not isinstance(coordinate, dict) or any(not number(coordinate.get(k)) for k in ("x", "y", "frameWallTime"))
            or coordinate.get("visualVerified") is not True or coordinate.get("classification") != trial["kind"]
            or not isinstance(coordinate.get("frameFile"), str) or not coordinate["frameFile"]):
        return result("NOT_VERIFIED", "Coordinate requires verified visual classification and frame evidence")
    recording = trial.get("recording", {})
    if (not isinstance(recording, dict) or recording.get("complete") is not True
            or recording.get("windowId") != identity["lumaWindowId"]
            or not isinstance(recording.get("frames"), list) or not recording["frames"]):
        return result("NOT_VERIFIED", "Complete recording of the identified LUMA window is required")
    previous_frame = None
    for frame in recording["frames"]:
        if (not isinstance(frame, dict) or not isinstance(frame.get("file"), str) or not frame["file"]
                or not number(frame.get("wallTime")) or not start <= frame["wallTime"] <= end):
            return result("NOT_VERIFIED", "Invalid recording frame")
        if previous_frame is not None and frame["wallTime"] <= previous_frame:
            return result("NOT_VERIFIED", "Recording timestamps are not strictly ordered")
        previous_frame = frame["wallTime"]
    if not any(f["file"] == coordinate["frameFile"] and f["wallTime"] == coordinate["frameWallTime"] for f in recording["frames"]):
        return result("NOT_VERIFIED", "Coordinate frame is not part of the recording")
    target = "receiver" if trial["kind"] == "transparent" else "luma-monitor"
    if trial["kind"] == "boundary":
        alpha = coordinate.get("alphaEvidence", {})
        declared = trial.get("expectedTarget")
        if (declared not in ("receiver", "luma") or not isinstance(alpha, dict)
                or alpha.get("verified") is not True or not number(alpha.get("alpha"))
                or not 0 <= alpha["alpha"] <= 1):
            return result("NOT_VERIFIED", "Boundary characterization needs explicit target and verified visual alpha")
        target = "receiver" if declared == "receiver" else "luma-monitor"
    expected = trial.get("expectedAction")
    if target == "luma-monitor" and (not isinstance(expected, str) or not expected or (trial["kind"] == "drag" and expected != "drag")):
        return result("NOT_VERIFIED", "Expected LUMA action must be declared")
    button = trial.get("expectedButton")
    if not integer(button) or button > 2:
        return result("NOT_VERIFIED", "Expected mouse button required")
    events, actions = trial.get("events"), trial.get("actions")
    if not isinstance(events, list) or not isinstance(actions, list):
        return result("NOT_VERIFIED", "Recorded events and actions must be arrays")
    inputs = []
    for event in events:
        if not isinstance(event, dict) or event.get("type") not in ("input", "ready", "heartbeat", "end"):
            return result("NOT_VERIFIED", "Malformed event record")
        source = event.get("source")
        if not isinstance(source, str) or source not in SOURCES:
            return result("NOT_VERIFIED", "Unknown event source")
        prefix = "receiver" if source == "receiver" else "luma"
        if (any(not number(event.get(k)) for k in ("wallTime", "uptime"))
                or event["uptime"] < 0 or not start <= event["wallTime"] <= end
                or type(event.get("pid")) is not int or type(event.get("windowId")) is not int
                or event["pid"] != identity[prefix + "Pid"] or event["windowId"] != identity[prefix + "WindowId"]):
            return result("NOT_VERIFIED", "Event timestamp or process/window identity is invalid")
        if event["type"] != "input":
            continue
        if event.get("kind") not in ("down", "up", "drag") or any(not number(event.get(k)) for k in ("x", "y")):
            return result("NOT_VERIFIED", "Invalid native input event")
        if event.get("button") != button or type(event.get("button")) is not int:
            return result("FAIL", "Gesture button ownership changed")
        if event.get("targetPid") != event["pid"]:
            return result("NOT_VERIFIED", "Native event target process is unverified")
        counts[source][event["kind"]] += 1
        inputs.append(event)
    for action in actions:
        if (not isinstance(action, dict) or not isinstance(action.get("kind"), str) or not action["kind"]
                or not number(action.get("wallTime")) or not start <= action["wallTime"] <= end):
            return result("NOT_VERIFIED", "Invalid observed action record")
    counts["actions"] = len(actions)
    if not inputs:
        return result("NOT_VERIFIED", "No actual native input was recorded")
    other = "luma-monitor" if target == "receiver" else "receiver"
    if any(counts[other].values()):
        return result("FAIL", "Input delivered to an unexpected target")
    chosen = [e for e in inputs if e["source"] == target]
    if counts[target]["down"] != 1 or counts[target]["up"] != 1:
        return result("FAIL", "Expected exactly one native down/up pair")
    down = next(e for e in chosen if e["kind"] == "down")
    up = next(e for e in chosen if e["kind"] == "up")
    if (math.hypot(down["x"] - coordinate["x"], down["y"] - coordinate["y"]) > 2
            or not 0 <= down["wallTime"] - coordinate["frameWallTime"] <= 0.100001):
        return result("NOT_VERIFIED", "Input coordinate does not match its prior classified frame")
    if (down["wallTime"] > up["wallTime"] or down["uptime"] > up["uptime"]
            or any(not down["wallTime"] <= e["wallTime"] <= up["wallTime"] or not down["uptime"] <= e["uptime"] <= up["uptime"] for e in chosen)):
        return result("NOT_VERIFIED", "Input sequence is temporally inconsistent")
    frames = recording["frames"]
    before = [f for f in frames if f["wallTime"] <= down["wallTime"]]
    after = [f for f in frames if f["wallTime"] >= up["wallTime"]]
    if not before or not after or after[0]["wallTime"]-up["wallTime"] > .25:
        return result("NOT_VERIFIED", "Recording does not bracket the gesture")
    span = [f["wallTime"] for f in frames if before[-1]["wallTime"] <= f["wallTime"] <= after[0]["wallTime"]]
    if any(b-a > .25 for a,b in zip(span,span[1:])):
        return result("NOT_VERIFIED", "Recording gap during gesture")
    if trial["kind"] == "drag":
        if counts[target]["drag"] < 1:
            return result("FAIL", "Drag trial lacks an observed native drag event")
    elif counts[target]["drag"]:
        return result("FAIL", "Click trial contains unexpected drag input")
    if target == "receiver":
        if actions:
            return result("FAIL", "Pass-through input triggered a LUMA action")
    elif len(actions) != 1 or actions[0]["kind"] != expected:
        return result("FAIL", "Expected exactly one matching LUMA action")
    elif actions[0]["wallTime"] < down["wallTime"]:
        return result("NOT_VERIFIED", "Observed action precedes input")
    return result("PASS", "Native observation and production IPC command counts match; domain success is not asserted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trial", help="Single trial JSON evidence file")
    args = parser.parse_args()
    try:
        with open(args.trial, encoding="utf-8") as source:
            trial = json.load(source)
        output = analyze_trial(trial)
    except (OSError, ValueError) as error:
        output = {"status": "NOT_VERIFIED", "reasons": [str(error)], "counts": {}}
    print(json.dumps(output, allow_nan=False))
    return 0 if output["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
