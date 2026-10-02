# Episode build kit

Builds the "Building an AI Employee" episodes (1080p, narrated).

Setup (from this folder):
- pip install --break-system-packages kokoro-onnx soundfile playwright
- Download kokoro-v1.0.onnx and voices-v1.0.bin from https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
- Needs ffmpeg and Chromium (Playwright).

Build: `python3 build.py N` (narration + timing), then `python3 render_ep.py N video` -> epN/episode.mp4.
Voice: af_heart at speed 1.08, same as the intro episode.

Status: Episodes 1-3 posted/scheduled. Episodes 4-9 scripted in episodes.py, not yet built.
Schedule (UTC): Ep4 Mon 2026-10-05 19:00, Ep5 Tue 10-06 19:00, Ep6 Wed 10-07 20:00, Ep7 Thu 10-08 17:00, Ep8 Fri 10-09 17:00, Ep9 Sat 10-10 14:00.
