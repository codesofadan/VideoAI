"""Local transcription with faster-whisper -> Scribe-compatible JSON.

Outputs:
  transcripts/<stem>.json   -- {"words":[{type,text,start,end,speaker_id}, ...]}
                               (matches ElevenLabs Scribe shape consumed by
                                pack_transcripts.py and render.py)
  segments.txt              -- human-readable [mm:ss] sentence-level lines for topic analysis

No paid API. Runs fully local on CPU.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Windows consoles default to cp1252 which cannot encode Urdu/Arabic script.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from faster_whisper import WhisperModel


def fmt(t: float) -> str:
    m = int(t // 60)
    s = t - m * 60
    return f"{m:02d}:{s:05.2f}"


def main() -> None:
    wav = Path(sys.argv[1]).resolve()
    edit_dir = wav.parent
    stem = sys.argv[2] if len(sys.argv) > 2 else wav.stem
    model_size = sys.argv[3] if len(sys.argv) > 3 else "small"

    print(f"loading model: {model_size} (cpu/int8)", flush=True)
    model = WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=4)

    print(f"transcribing {wav.name} ...", flush=True)
    segments, info = model.transcribe(
        str(wav),
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 400},
        beam_size=5,
    )
    print(f"detected language: {info.language} (p={info.language_probability:.2f})", flush=True)

    words_out: list[dict] = []
    seg_lines: list[str] = []
    prev_end = None
    for seg in segments:
        seg_lines.append(f"[{fmt(seg.start)} -> {fmt(seg.end)}] {seg.text.strip()}")
        # progress ping every segment
        print(f"  {fmt(seg.start)}  {seg.text.strip()[:70]}", flush=True)
        if seg.words:
            for w in seg.words:
                # insert a spacing token if there is an audible gap
                if prev_end is not None and w.start - prev_end > 0.02:
                    words_out.append({
                        "type": "spacing", "text": " ",
                        "start": round(prev_end, 3), "end": round(w.start, 3),
                        "speaker_id": None,
                    })
                words_out.append({
                    "type": "word",
                    "text": w.word.strip(),
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                    "speaker_id": None,
                })
                prev_end = w.end

    (edit_dir / "transcripts").mkdir(parents=True, exist_ok=True)
    out_json = edit_dir / "transcripts" / f"{stem}.json"
    out_json.write_text(json.dumps({
        "language": info.language,
        "duration": info.duration,
        "words": words_out,
    }, indent=2), encoding="utf-8")

    (edit_dir / "segments.txt").write_text("\n".join(seg_lines), encoding="utf-8")

    n_words = sum(1 for w in words_out if w["type"] == "word")
    print(f"\nDONE: {out_json.name}  words={n_words}  segments={len(seg_lines)}", flush=True)


if __name__ == "__main__":
    main()
