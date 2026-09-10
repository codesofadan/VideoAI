"""Resumable, chunked local transcription with faster-whisper.

- Splits audio into fixed-length chunks; transcribes each; writes chunk JSON
  to chunks/chunk_NN.json immediately (resumable across interruptions).
- task="translate" -> English output (robust for code-switched Urdu/English,
  and analyzable + usable as captions).
- Anti-hallucination: condition_on_previous_text=False kills repetition loops.
- Merges all chunks -> transcripts/<stem>.json (Scribe shape) + segments.txt.

Usage:
  python transcribe_chunked.py <wav> <stem> <model> <task> [chunk_len_s]
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import wave
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from faster_whisper import WhisperModel


def fmt(t: float) -> str:
    m = int(t // 60)
    return f"{m:02d}:{t - m * 60:05.2f}"


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def main() -> None:
    wav = Path(sys.argv[1]).resolve()
    stem = sys.argv[2]
    model_size = sys.argv[3] if len(sys.argv) > 3 else "medium"
    task = sys.argv[4] if len(sys.argv) > 4 else "translate"
    chunk_len = float(sys.argv[5]) if len(sys.argv) > 5 else 120.0

    edit = wav.parent
    chunks_dir = edit / "chunks"
    chunks_dir.mkdir(exist_ok=True)

    dur = wav_duration(wav)
    n = math.ceil(dur / chunk_len)
    print(f"duration={dur:.1f}s  chunks={n}  model={model_size}  task={task}", flush=True)

    print("loading model ...", flush=True)
    model = WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=4)

    for i in range(n):
        out = chunks_dir / f"chunk_{i:02d}.json"
        if out.exists():
            print(f"chunk {i:02d}: cached", flush=True)
            continue
        start = i * chunk_len
        length = min(chunk_len, dur - start)
        tmp = chunks_dir / f"_tmp_{i:02d}.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-t", f"{length:.3f}",
             "-i", str(wav), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(tmp)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        print(f"chunk {i:02d}: transcribing {fmt(start)}..{fmt(start+length)}", flush=True)
        segments, info = model.transcribe(
            str(tmp),
            task=task,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 400},
            beam_size=5,
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4,
        )
        words = []
        seglines = []
        for seg in segments:
            seglines.append({"start": round(start + seg.start, 3),
                             "end": round(start + seg.end, 3),
                             "text": seg.text.strip()})
            print(f"    [{fmt(start+seg.start)}] {seg.text.strip()[:80]}", flush=True)
            for w in (seg.words or []):
                words.append({"text": w.word.strip(),
                              "start": round(start + w.start, 3),
                              "end": round(start + w.end, 3)})
        out.write_text(json.dumps({"chunk": i, "start": start,
                                   "words": words, "segments": seglines},
                                  indent=2), encoding="utf-8")
        tmp.unlink(missing_ok=True)
        print(f"chunk {i:02d}: saved ({len(words)} words)", flush=True)

    # merge
    all_words, all_segs = [], []
    for i in range(n):
        data = json.loads((chunks_dir / f"chunk_{i:02d}.json").read_text(encoding="utf-8"))
        all_words.extend(data["words"])
        all_segs.extend(data["segments"])
    all_words.sort(key=lambda w: w["start"])
    all_segs.sort(key=lambda s: s["start"])

    # scribe-shape words with spacing tokens on gaps
    scribe = []
    prev_end = None
    for w in all_words:
        if prev_end is not None and w["start"] - prev_end > 0.02:
            scribe.append({"type": "spacing", "text": " ",
                           "start": round(prev_end, 3), "end": round(w["start"], 3),
                           "speaker_id": None})
        scribe.append({"type": "word", "text": w["text"],
                       "start": w["start"], "end": w["end"], "speaker_id": None})
        prev_end = w["end"]

    (edit / "transcripts").mkdir(exist_ok=True)
    (edit / "transcripts" / f"{stem}.json").write_text(
        json.dumps({"language": "ur", "task": task, "words": scribe}, indent=2),
        encoding="utf-8")
    (edit / "segments.txt").write_text(
        "\n".join(f"[{fmt(s['start'])} -> {fmt(s['end'])}] {s['text']}" for s in all_segs),
        encoding="utf-8")
    nwords = sum(1 for x in scribe if x["type"] == "word")
    print(f"\nDONE: merged {nwords} words, {len(all_segs)} segments", flush=True)


if __name__ == "__main__":
    main()
