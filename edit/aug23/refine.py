"""High-quality re-transcription of candidate clip windows (medium model, VAD relaxed)."""
import json, subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from faster_whisper import WhisperModel

WINDOWS = [
    ("W1_ai_school",   78, 152),
    ("W2_website_lead",270, 338),
    ("W3_video_weight",1025,1085),
    ("W4_capabilities",1310,1388),
    ("W5_app_case",    1418,1492),
    ("W6_untranscribed",1495,1552),
]
def fm(t): return f"{int(t//60):02d}:{t%60:05.2f}"
m = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=4)
out = {}
for name, s, e in WINDOWS:
    tmp = f"_w_{name}.wav"
    subprocess.run(["ffmpeg","-y","-ss",str(s),"-t",str(e-s),"-i","audio16k.wav",
                    "-ar","16000","-ac","1","-c:a","pcm_s16le",tmp],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    segs, _ = m.transcribe(tmp, task="translate", word_timestamps=True,
                           vad_filter=True, vad_parameters={"min_silence_duration_ms":300},
                           beam_size=2, condition_on_previous_text=False,
                           no_speech_threshold=0.45, compression_ratio_threshold=2.4)
    rec=[]
    print(f"\n########## {name}  {fm(s)} -> {fm(e)} ##########", flush=True)
    for g in segs:
        rec.append({"start":round(s+g.start,2),"end":round(s+g.end,2),"text":g.text.strip(),
                    "words":[{"t":w.word.strip(),"s":round(s+w.start,2),"e":round(s+w.end,2)} for w in (g.words or [])]})
        print(f"[{fm(s+g.start)}-{fm(s+g.end)}] {g.text.strip()}", flush=True)
    out[name]={"start":s,"end":e,"segments":rec}
    Path(tmp).unlink(missing_ok=True)
    json.dump(out, open("refined.json","w",encoding="utf-8"), indent=1)
print("\nREFINE DONE", flush=True)
