#!/usr/bin/env bash
# Runs on the Higgsfield sandbox (it can download Higgsfield audio; the Claude workspace cannot).
# voices.txt: one line per voice line: "<LINE_ID> <result file name>", e.g.
#   N1 hf_20261002_081425_b25d8b8a-7d0a-4147-9bda-37db6d804b56.mp3
# Line ids start with the speaker letter(s): J = Jiddo, N = Nour, S = Sami. Output: lines/<ID>.wav (mono 48 kHz).
# Trim uses peak detection: the default RMS detection cut short opening words like "نعم!" and "دُم!" (found on ep02).
set -e
BASE=https://d8j0ntlcm91z4.cloudfront.net/user_3JmkWHWcGKjhnwnMaVpOTweeUQ9
mkdir -p raw lines
while read id f; do [ -z "$id" ] && continue; curl -sf -o "raw/$id.mp3" "$BASE/$f"; done < voices.txt
TRIM="silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05:detection=peak,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08:detection=peak,areverse"
for f in raw/*.mp3; do
  id=$(basename "$f" .mp3); spk=${id%%[0-9]*}
  case "$spk" in
    N) FX="aresample=44100,asetrate=52437,aresample=48000,atempo=0.8410," ;;   # Nour: Pixie +3 semitones
    S) FX="aresample=44100,asetrate=55562,aresample=48000,atempo=0.7937," ;;   # Sami: Skye +4 semitones
    *) FX="aresample=48000," ;;                                              # Jiddo (Desmond) and others: as voiced
  esac
  # measure with loudnorm (its input_i is right), then apply that gain to -19 LUFS and a -2 dBFS limiter.
  # loudnorm's own output stage misbehaves on clips under ~3 s: on ep04 it pushed J16 (2.4 s) to -39 LUFS.
  # (ebur128 reports I: 0.0 in the sandbox's ffmpeg build, so it isn't used.)
  I=$(ffmpeg -hide_banner -i "$f" -af "${FX}${TRIM},loudnorm=print_format=json" -f null - 2>&1 | sed -n '/^{/,/^}/p' | jq -r .input_i)
  GAIN=$(awk -v i="$I" 'BEGIN{printf "%.2f", -19 - i}')
  ffmpeg -y -v error -i "$f" -af "${FX}${TRIM},volume=${GAIN}dB,alimiter=limit=0.794:level=false,aresample=48000" -ac 1 -ar 48000 "lines/$id.wav"
done
echo "prepared $(ls lines | wc -l) lines"
# lines spoken together (ids in episode.json "order" lists) are then word-aligned by chorus.py
