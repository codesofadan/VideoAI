"""Merge whisper segments with the border-derived speaker timeline."""
import json, glob, numpy as np, sys
FPS = 2.0
A = np.load("spk_adan.npy"); S = np.load("spk_shay.npy")
def who(s, e):
    i0, i1 = int(s*FPS), max(int(e*FPS), int(s*FPS)+1)
    a, sh = A[i0:i1].sum(), S[i0:i1].sum()
    if a == 0 and sh == 0: return "?"
    return "ADAN" if a >= sh else "SHAYAN"
segs = []
for f in sorted(glob.glob("chunks/chunk_*.json")):
    segs += json.load(open(f, encoding="utf-8"))["segments"]
segs.sort(key=lambda x: x["start"])
def fm(t): return f"{int(t//60):02d}:{t%60:05.2f}"
out, prev = [], None
for s in segs:
    w = who(s["start"], s["end"])
    tag = f"\n=== {w} ===" if w != prev else ""
    prev = w
    if tag: out.append(tag)
    out.append(f"[{fm(s['start'])}-{fm(s['end'])}] {s['text']}")
open("labelled.txt","w",encoding="utf-8").write("\n".join(out))
print(f"{len(segs)} segments -> labelled.txt  (covers {fm(segs[0]['start'])}..{fm(segs[-1]['end'])})")
