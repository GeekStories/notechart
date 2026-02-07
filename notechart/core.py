import json
import math
import re
import requests
import numpy as np
import soundfile as sf
from pathlib import Path
from aubio import source, pitch

LRC_LINE = re.compile(r"\[(\d+):(\d+\.\d+)\](.*)")

class NoteChartGenerator:
    def __init__(
        self,
        audio_path: str | Path,
        lyrics_path: str | Path,
        *,
        cfg: dict,
    ):
        self.audio_path = Path(audio_path).expanduser().resolve()
        if not self.audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {self.audio_path}")
        
        self.lyrics_path = Path(lyrics_path).expanduser().resolve()
        if not self.lyrics_path.exists():
            raise FileNotFoundError(f"Lyrics file not found: {self.lyrics_path}")

        self.cfg = cfg
        self.notes = []
        self.export_data = {}
    
    # ------------------------------
    # UTILITY FUNCTIONS
    # ------------------------------
    @staticmethod
    def hz_to_midi(freq):
        return 69 + 12 * math.log2(freq / 440) if freq and freq > 0 else None

    @staticmethod
    def clamp_octaves(pitches):
        result = []
        prev = 0.0
        for p in pitches:
            if p == 0 or prev == 0:
                result.append(p)
            else:
                if p > prev * 1.9:
                    p *= 0.5
                elif p < prev * 0.55:
                    p *= 2.0
                result.append(p)
            prev = p
        return result

    @staticmethod
    def smooth_time_series(pitches, window_size):
        smoothed = []
        for i in range(len(pitches)):
            window = pitches[max(0, i - window_size): i + 1]
            valid = [p for p in window if p > 0]
            smoothed.append(sum(valid) / len(valid) if valid else 0.0)
        return smoothed

    @staticmethod
    def apply_hysteresis(pitches, stability_frames):
        stable = []
        current = None
        candidate = None
        count = 0
        for p in pitches:
            if p is None:
                stable.append(None)
                candidate = None
                count = 0
                continue
            if p == candidate:
                count += 1
            else:
                candidate = p
                count = 1
            if count >= stability_frames:
                current = candidate
            stable.append(current)
        return stable

    @staticmethod
    def hold_pitch(pitches, hold_tolerance):
        held = []
        last = None
        for p in pitches:
            if p is None:
                held.append(None)
                last = None
            elif last is None or abs(p - last) > hold_tolerance:
                held.append(p)
                last = p
            else:
                held.append(last)
        return held

    @staticmethod
    def fill_micro_gaps(times, pitches, max_gap=0.3):
        filled = []
        last_pitch = None
        last_time = None
        for t, p in zip(times, pitches):
            if p is None and last_pitch is not None and t - last_time < max_gap:
                filled.append(last_pitch)
            else:
                filled.append(p)
                last_pitch = p
                last_time = t
        return filled

    @staticmethod
    def segment_notes(times, pitches):
        notes = []
        current_pitch = None
        start_time = None
        for t, p in zip(times, pitches):
            if p is None:
                if current_pitch is not None:
                    notes.append({"start": start_time, "end": t, "pitch": current_pitch})
                    current_pitch = None
                continue
            if current_pitch is None:
                current_pitch = p
                start_time = t
            elif p != current_pitch:
                notes.append({"start": start_time, "end": t, "pitch": current_pitch})
                current_pitch = p
                start_time = t
        if current_pitch is not None:
            notes.append({"start": start_time, "end": times[-1], "pitch": current_pitch})
        return notes

    @staticmethod
    def merge_notes(notes, gap, pitch_tol, min_duration=0.0):
        merged = []
        for n in notes:
            if n["end"] - n["start"] < min_duration:
                continue
            if not merged:
                merged.append(n.copy())
                continue
            prev = merged[-1]
            close_pitch = abs(n["pitch"] - prev["pitch"]) <= pitch_tol
            close_time = n["start"] - prev["end"] <= gap
            if close_pitch and close_time:
                prev["end"] = n["end"]
                prev["pitch"] = (prev["pitch"] + n["pitch"]) / 2
            else:
                merged.append(n.copy())
        return merged

    @staticmethod
    def mash_merge(notes, gap):
        result = []
        buffer = []
        for n in notes:
            if not buffer:
                buffer.append(n.copy())
                continue
            if n["start"] - buffer[-1]["end"] <= gap:
                buffer.append(n.copy())
            else:
                result.append({
                    "start": buffer[0]["start"],
                    "end": buffer[-1]["end"],
                    "pitch": sum(b["pitch"] for b in buffer) / len(buffer)
                })
                buffer = [n.copy()]
        if buffer:
            result.append({
                "start": buffer[0]["start"],
                "end": buffer[-1]["end"],
                "pitch": sum(b["pitch"] for b in buffer) / len(buffer)
            })
        return result

    @staticmethod
    def parse_lrc(lines):
        entries = []

        for line in lines:
            match = LRC_LINE.match(line)
            if not match:
                continue

            minutes = int(match.group(1))
            seconds = float(match.group(2))
            timestamp = minutes * 60 + seconds
            text = match.group(3).strip()

            entries.append((timestamp, text))

        return entries
    
    # ------------------------------
    # GENERATE & EXPORT
    # ------------------------------
    def generate_chart(self):
        if self.cfg is None:
            self.load_config()

        cfg = self.cfg

        # Analysis parameters
        WINDOW_SIZE = cfg["window_size"]
        HOP_SIZE = cfg["hop_size"]
        MIN_FREQ = cfg["min_freq"]
        MAX_FREQ = cfg["max_freq"]

        # Pitch stability
        SMOOTH_FRAMES = cfg["smooth_frames"]
        STABILITY_FRAMES = cfg["stability_frames"]
        HOLD_TOLERANCE = cfg["hold_tolerance"]

        # Notes
        MIN_NOTE_DURATION = cfg["min_note_duration"]
        MERGE_GAP = cfg["merge_gap"]
        MERGE_PITCH_TOLERANCE = cfg["note_pitch_tolerance"]

        # Phrase
        PHRASE_GAP = cfg["phrase_gap"]
        PHRASE_PITCH_TOLERANCE = cfg["phrase_pitch_tolerance"]
        STRETCH_FACTOR = cfg["stretch_factor"]

        # Final mash
        FINAL_MERGE_GAP = cfg["final_merge_gap"]

        # --------------------------
        # Load audio
        # --------------------------
        audio, sr = sf.read(str(self.audio_path))
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        src = source(str(self.audio_path), sr, HOP_SIZE)
        pitch_detector = pitch("yin", WINDOW_SIZE, HOP_SIZE, sr)
        pitch_detector.set_unit("Hz")
        pitch_detector.set_silence(-30)
        pitch_detector.set_tolerance(0.8)

        times, pitches = [], []
        total_samples = 0

        while True:
            samples, read = src()
            p = pitch_detector(samples)[0]
            pitches.append(p if MIN_FREQ <= p <= MAX_FREQ else 0.0)
            times.append(total_samples / sr)
            total_samples += read
            if read < HOP_SIZE:
                break

        # --------------------------
        # Load lyrics
        # --------------------------
        with open(self.lyrics_path, "r") as f:
            entries = self.parse_lrc(f.read().strip().splitlines())

        lyrics = []
        with open(self.lyrics_path, "r") as f:
            self.lyrics = f.read().strip().splitlines()

            for i, (start, text) in enumerate(entries):
                end = entries[i + 1][0] if i + 1 < len(entries) else audio.shape[0] / sr
                lyrics.append({"start": start, "end": end, "text": text})

        # Round each lyric start/end to 2 decimals
        for l in lyrics:
            l["start"] = round(l["start"], 2)
            l["end"] = round(l["end"], 2)

        # --------------------------
        # Pitch processing pipeline
        # --------------------------
        raw_pitches = pitches.copy()
        pitches = self.clamp_octaves(pitches)
        pitches = self.smooth_time_series(pitches, SMOOTH_FRAMES)
        midi = [self.hz_to_midi(p) for p in pitches]
        quantized = [round(m * 2) / 2 if m else None for m in midi]

        stable = self.apply_hysteresis(quantized, STABILITY_FRAMES)
        held = self.hold_pitch(stable, HOLD_TOLERANCE)
        filled = self.fill_micro_gaps(times, held)

        # --------------------------
        # Note -> phrase generation
        # --------------------------
        notes = self.segment_notes(times, filled)
        notes = self.merge_notes(notes, MERGE_GAP, MERGE_PITCH_TOLERANCE, MIN_NOTE_DURATION)
        notes = self.merge_notes(notes, PHRASE_GAP, PHRASE_PITCH_TOLERANCE)

        # Stretch phrases
        for n in notes:
            duration = n["end"] - n["start"]
            n["end"] = n["start"] + duration * STRETCH_FACTOR

        notes = self.mash_merge(notes, FINAL_MERGE_GAP)

        # --------------------------
        # Lane normalization & export
        # --------------------------
        reference_pitch = np.median([n["pitch"] for n in notes])
        export_notes = []
        for n in notes:
            semitone_offset = round(12 * math.log2(n["pitch"] / reference_pitch))
            lane = semitone_offset + self.cfg["lane_range"] // 2
            lane = max(0, min(self.cfg["lane_range"] - 1, lane))
            export_notes.append({
                "start": round(n["start"], 3),
                "duration": round(n["end"] - n["start"], 3),
                "lane": int(lane)
            })

        self.export_data = {
            "name": str(self.audio_path.stem),
            "length": total_samples / sr,
            "lanes": self.cfg["lane_range"],
            "notes": export_notes,
            "pitches": [{"time": float(t), "pitch": float(p), "midi": float(self.hz_to_midi(p))}
                        for t, p in zip(times, raw_pitches) if p > 0],
            "lyrics": lyrics
        }

        self.notes = notes
        return self.export_data

    def export(self, output_file: str | None = None):
        if not self.export_data:
            raise ValueError("No chart generated yet. Call generate_chart() first.")
        output_file = output_file or (self.audio_path.parent / f"{self.audio_path.stem}_chart.json")
        with open(output_file, "w") as f:
            json.dump(self.export_data, f, indent=2)
        print(f"Exported chart to {output_file}")