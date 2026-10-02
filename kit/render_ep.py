import sys, subprocess, time
from playwright.sync_api import sync_playwright

num = int(sys.argv[1]); MODE = sys.argv[2] if len(sys.argv) > 2 else "video"
FPS = 30
D = f"/home/claude/vid/ep{num}"

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    pg.goto(f"file://{D}/film.html")
    pg.wait_for_function("window.READY === true")
    total = pg.evaluate("window.TOTAL")
    if MODE == "stills":
        times = pg.evaluate("window.EP.scenes.map(s=>s.end-0.6)")
        for i, t in enumerate(times):
            pg.evaluate(f"render({t})")
            pg.screenshot(path=f"{D}/still_{i:02d}.jpg", type="jpeg", quality=75)
        print("stills", len(times))
    else:
        n = int(round(total * FPS))
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
            "-c:v", "mjpeg", "-i", "-", "-i", f"{D}/voice.wav", "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", f"{D}/episode.mp4"], stdin=subprocess.PIPE)
        t0 = time.time()
        for f in range(n):
            pg.evaluate(f"render({f / FPS})")
            ff.stdin.write(pg.screenshot(type="jpeg", quality=95))
        ff.stdin.close(); ff.wait()
        print("ep", num, "encoded", n, "frames in", round(time.time() - t0), "s")
    b.close()
