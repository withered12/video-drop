set -e
B=https://d8j0ntlcm91z4.cloudfront.net/user_3JmkWHWcGKjhnwnMaVpOTweeUQ9
mkdir -p raw lines
while read id f; do curl -sf -o raw/$id.mp3 "$B/hf_20261002_$f.mp3"; done < map.txt
TRIM="silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse"
for f in raw/*.mp3; do id=$(basename $f .mp3); if [ ${id:0:1} = N ]; then PF="aresample=44100,asetrate=52437,aresample=48000,atempo=0.8410,"; else PF="aresample=48000,"; fi
 ffmpeg -y -v error -i $f -af "${PF}${TRIM},loudnorm=I=-19:TP=-2:LRA=11,aresample=48000" -ac 1 -ar 48000 lines/$id.wav; done
