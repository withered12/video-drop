import json, sys, os, numpy as np, soundfile as sf, importlib
from kokoro_onnx import Kokoro

VOICE, SPEED = "af_heart", 1.08          # same voice and pace as the intro episode
GAP, LEAD, TAIL = 0.3, 0.5, 0.9

def build(num):
    eps = importlib.import_module("episodes")
    EP = eps.EPISODES[num]
    os.makedirs(f"ep{num}", exist_ok=True)
    k = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
    SR = 24000
    t = 0.0
    clips = []
    for si, sc in enumerate(EP["scenes"]):
        sc["start"] = round(t, 3)
        lt = LEAD
        for li, ln in enumerate(sc["lines"]):
            audio, SR = k.create(ln["say"], voice=VOICE, speed=SPEED, lang="en-us")
            a = np.abs(audio); idx = np.where(a > 0.01)[0]
            if len(idx): audio = audio[max(0, idx[0] - int(.03 * SR)): idx[-1] + int(.06 * SR)]
            lt += ln.get("wait", 0)
            ln["start"] = round(t + lt, 3)
            ln["end"] = round(t + lt + len(audio) / SR, 3)
            clips.append((t + lt, audio))
            lt += len(audio) / SR + GAP
        dur = max(lt - GAP + TAIL, sc.get("min", 0))
        t += dur
        sc["end"] = round(t, 3)
    EP["total"] = round(t, 3)
    track = np.zeros(int((t + .5) * SR), dtype=np.float32)
    for st, a in clips:
        s = int(st * SR); track[s:s + len(a)] += a
    track = track[: int(t * SR)]
    track = track / max(1e-6, np.abs(track).max()) * 0.89
    sf.write(f"ep{num}/voice.wav", track, SR)
    for sc in EP["scenes"]:
        for ln in sc["lines"]:
            ln.setdefault("cap", ln["say"])
    html = open("engine.html").read().replace("/*DATA*/", "window.EP=" + json.dumps(EP) + ";")
    open(f"ep{num}/film.html", "w").write(html.replace('url(fonts/', 'url(../fonts/'))
    print(num, "total", EP["total"], "scenes", [(s["start"], s["end"]) for s in EP["scenes"]])

if __name__ == "__main__":
    for n in sys.argv[1:]:
        build(int(n))
