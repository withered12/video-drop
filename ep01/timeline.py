#!/usr/bin/env python3
"""Build timeline.json (line timings + per-frame mouth envelopes) and, with --mix, the final audio mix.
Expects processed voice files in lines/<ID>.wav (mono 48k). With --mock, invents durations for previews."""
import json, sys, os, math
import numpy as np

FPS = 24
NL = chr(10)
SR = 48000
ORDER = ['N1', 'J2', 'N3', 'J4', 'TITLE', 'J6', 'N7', 'J8', 'J9', 'N10', 'J11', 'N12', 'J13', 'N14', 'J15', 'N16', 'J17', 'X18']
TEXT = {
 'N1': 'جدّو... كم بقي على العشاء؟ أنا جائعة!',
 'J2': 'سؤالٌ جميل يا نور! قديمًا، لم تكن عند الناس ساعاتٌ في أيديهم.',
 'N3': 'إذن، كيف كانوا يعرفون الوقت؟',
 'J4': 'بالشمس في النهار. لكن ماذا يفعلون في الليل؟ تعالي، سأريكِ سرَّ الماء.',
 'J6': 'هذا خزّانٌ مملوءٌ بالماء، وفي أسفله ثقبٌ صغيرٌ جدًّا.',
 'N7': 'الماء ينزل... قطرة... قطرة!',
 'J8': 'أحسنتِ! والقطرات تنزل بانتظام، واحدةً بعد واحدة.',
 'J9': 'وفي الإناء الأسفل عوّامةٌ خفيفة. كلّما امتلأ الإناء، ارتفعت العوّامة.',
 'N10': 'وتِكتاك يركب فوقها! انظر يا جدّو، إنّه يصعد!',
 'J11': 'وكلّما وصل تِكتاك إلى علامة، تكون قد مرّت ساعة.',
 'N12': 'يعني... الماء يعدّ الوقت!',
 'J13': 'تمامًا! وقبل أكثر من ثمانمئة سنة، كتب المخترع الجزري كتابًا عجيبًا عن آلاتٍ كهذه.',
 'N14': 'جدّو! تِكتاك وصل إلى العلامة الأخيرة!',
 'J15': 'إذن... حان وقت العشاء!',
 'N16': 'الماء أخبرني!',
 'J17': 'جرّبوا مع شخصٍ كبير: اثقبوا كوبًا ورقيًّا ثقبًا صغيرًا، واملؤوه ماءً، وعُدّوا حتى يفرغ.',
 'J18': 'فكّر... جرّب... اخترع!',
}
GAP_AFTER = {'J4': 0.7, 'TITLE': 0.5, 'N12': 0.6, 'J13': 0.4, 'N16': 1.3, 'J17': 1.3}
TITLE_DUR = 3.8
LEAD, TAIL = 1.0, 3.2


def load_wav(path):
    import subprocess
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def envelope(x):
    hop = SR // FPS
    n = int(math.ceil(len(x) / hop))
    rms = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(n)])
    mx = rms.max()
    loc = np.array([rms[max(0, i - 6):i + 7].max() for i in range(n)])
    states = [bool(r > 0.12 * mx and r > 0.45 * l) for r, l in zip(rms, loc)]
    for i in range(1, len(states) - 1):
        if states[i] != states[i - 1] and states[i] != states[i + 1]:
            states[i] = states[i - 1]
    out, run = [], 0
    for i, s in enumerate(states):
        run = run + 1 if (s and i > 0 and states[i - 1]) else (1 if s else 0)
        out.append('1' if (s and run % 5 != 0) else '0')
    return ''.join(out)


def build(mock=False):
    lines, t = [], LEAD
    durs, envs = {}, {}
    for lid in ORDER:
        if lid in ('TITLE',):
            continue
        ids = ['J18', 'N18'] if lid == 'X18' else [lid]
        for i in ids:
            if mock:
                d = len(TEXT.get(i, TEXT['J18'])) * (0.085 if i[0] == 'J' else 0.07)
                durs[i] = d
                envs[i] = ''.join('1' if (k // 3) % 2 == 0 else '0' for k in range(int(d * FPS) + 1))
            elif os.path.exists('measured.json'):
                durs[i], envs[i] = json.load(open('measured.json'))[i]
            else:
                x = load_wav(f'lines/{i}.wav')
                durs[i] = len(x) / SR
                envs[i] = envelope(x)
    title = None
    for lid in ORDER:
        if lid == 'TITLE':
            title = {'start': round(t, 3), 'dur': TITLE_DUR}
            t += TITLE_DUR + GAP_AFTER['TITLE']
            continue
        ids = ['J18', 'N18'] if lid == 'X18' else [lid]
        if lid == 'J17':
            t += 0.3
        for i in ids:
            lines.append({'id': i, 'speaker': i[0], 'start': round(t, 3), 'dur': round(durs[i], 3), 'env': envs[i]})
        t += max(durs[i] for i in ids) + GAP_AFTER.get(lid, 0.35)
    duration = round(t - 0.35 + TAIL, 3)
    return {'fps': FPS, 'duration': duration, 'title': title, 'lines': lines}


def tone(f0, dur, kind='bell', vol=0.3, f1=None):
    n = int(dur * SR); tt = np.arange(n) / SR
    if kind == 'bell':
        y = sum(a * np.sin(2 * np.pi * f0 * m * tt) * np.exp(-tt * d) for a, m, d in [(1, 1, 3.5), (0.4, 2.0, 6), (0.2, 3.01, 9)])
    elif kind == 'chirp':
        f = np.linspace(f0, f1, n); y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / dur) ** 2
    elif kind == 'drip':
        f = f0 * np.exp(-tt * 9) + 300; y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 28)
    elif kind == 'pluck':
        y = np.sin(2 * np.pi * f0 * tt) * np.exp(-tt * 4) + 0.3 * np.sin(4 * np.pi * f0 * tt) * np.exp(-tt * 7)
    elif kind == 'whoosh':
        rng = np.random.default_rng(1); w = rng.standard_normal(n)
        k = np.ones(40) / 40; w = np.convolve(w, k, 'same'); y = w * np.sin(np.pi * tt / dur) ** 2
    return (y / (np.abs(y).max() + 1e-9) * vol).astype(np.float32)


def add(buf, t, y):
    i = int(t * SR)
    if i < 0 or i >= len(buf): return
    j = min(len(buf), i + len(y)); buf[i:j] += y[:j - i]


def music(dur):
    # gentle plucked loop in D (hijaz-flavoured scale), 84 bpm, very soft
    scale = [293.66, 311.13, 369.99, 392.00, 440.00, 466.16, 523.25, 587.33]
    pat = [0, 2, 4, 2, 3, 2, 1, 0, 4, 5, 4, 2, 3, 1, 0, 0]
    beat = 60 / 84 / 2
    buf = np.zeros(int(dur * SR) + SR, np.float32)
    k, t = 0, 0.0
    while t < dur:
        f = scale[pat[k % len(pat)]]
        add(buf, t, tone(f, 1.2, 'pluck', 0.06))
        if k % 8 == 0: add(buf, t, tone(scale[0] / 2, 2.4, 'pluck', 0.05))
        k += 1; t += beat
    return buf[:int(dur * SR)]


def mix(tl, sfx):
    dur = tl['duration']; n = int(dur * SR)
    voice = np.zeros(n, np.float32)
    for l in tl['lines']:
        add(voice, l['start'], load_wav(f"lines/{l['id']}.wav") * 0.9)
    bg = music(dur)
    # duck music under dialogue
    duck = np.ones(n, np.float32)
    for l in tl['lines']:
        a, b = int((l['start'] - 0.2) * SR), int((l['start'] + l['dur'] + 0.3) * SR)
        duck[max(a, 0):min(b, n)] = 0.45
    k = int(0.25 * SR); duck = np.convolve(duck, np.ones(k) / k, 'same').astype(np.float32)
    ts, te = tl['title']['start'], tl['title']['start'] + tl['title']['dur']
    fx = np.zeros(n, np.float32)
    for td in sfx['drip']: add(fx, td, tone(1500, 0.25, 'drip', 0.10))
    for td in sfx['ding']: add(fx, td, tone(1046.5, 1.6, 'bell', 0.16))
    for td in sfx['chirp']:
        add(fx, td, tone(2200, 0.09, 'chirp', 0.12, 3400)); add(fx, td + 0.12, tone(2400, 0.11, 'chirp', 0.12, 3800))
    for td in sfx['pop']: add(fx, td, tone(600, 0.12, 'chirp', 0.12, 1200))
    for td in sfx['whoosh']: add(fx, td - 0.2, tone(0, 0.45, 'whoosh', 0.05))
    for i, f in enumerate([587.33, 739.99, 880.0]): add(fx, sfx['jingle'][0] + i * 0.28, tone(f, 1.8, 'bell', 0.18))
    out = voice + fx + bg * duck
    # fade in/out
    fi = int(0.6 * SR); out[:fi] *= np.linspace(0, 1, fi); fo = int(1.2 * SR); out[-fo:] *= np.linspace(1, 0, fo)
    peak = np.abs(out).max(); out = out / peak * 0.89 if peak > 0.89 else out
    import subprocess
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-', '-c:a', 'pcm_s16le', 'mix.wav'], input=out.astype(np.float32).tobytes())


def srt(tl):
    def ts(s):
        h, r = divmod(s, 3600); m, r = divmod(r, 60); return f'{int(h):02}:{int(m):02}:{int(r):02},{int((r % 1) * 1000):03}'
    out, k = [], 1
    for l in tl['lines']:
        if l['id'] == 'N18': continue
        txt = TEXT[l['id']]
        if l['id'] == 'J18': txt = 'الجميع: ' + txt
        out.append(NL.join([str(k), ts(l['start']) + ' --> ' + ts(l['start'] + l['dur'] + 0.15), txt, ''])); k += 1
    open('ep01_captions_ar.srt', 'w', encoding='utf-8').write(NL.join(out))


if __name__ == '__main__':
    if '--mix' in sys.argv:
        tl = json.load(open('timeline.json')); mix(tl, json.load(open('sfx.json')))
    else:
        tl = build(mock='--mock' in sys.argv)
        json.dump(tl, open('timeline.json', 'w'), ensure_ascii=False)
        srt(tl)
        print('duration', tl['duration'], 'title', tl['title'], [(l['id'], l['start'], l['dur']) for l in tl['lines']])
