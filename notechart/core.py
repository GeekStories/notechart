import json
import math
import numpy as np
import soundfile as sf
from pathlib import Path
from aubio import source, pitch

PACKAGE_ROOT = Path(__file__).resolve().parent
PACKAGED_CONFIG_ROOT = PACKAGE_ROOT / "configs"

class NoteChartGenerator:
    def __init__(
        self,
        audio_path: str | Path,
        *,
        cfg: dict,
    ):
        self.audio_path = Path(audio_path).expanduser().resolve()
        if not self.audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {self.audio_path}")

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

    # ------------------------------
    # GENERATE & EXPORT
    # ------------------------------
    def generate_chart(self):
        if self.cfg is None:
            self.load_config()

        cfg = self.cfg

        # Analysis parameters
        WINDOW_SIZE = cfg["analysis"]["window_size"]
        HOP_SIZE = cfg["analysis"]["hop_size"]
        MIN_FREQ = cfg["analysis"]["min_freq"]
        MAX_FREQ = cfg["analysis"]["max_freq"]

        # Pitch stability
        SMOOTH_FRAMES = cfg["stability"]["smooth_frames"]
        STABILITY_FRAMES = cfg["stability"]["stability_frames"]
        HOLD_TOLERANCE = cfg["stability"]["hold_tolerance"]

        # Notes
        MIN_NOTE_DURATION = cfg["notes"]["min_note_duration"]
        MERGE_GAP = cfg["notes"]["merge_gap"]
        MERGE_PITCH_TOLERANCE = cfg["notes"]["merge_pitch_tolerance"]

        # Phrase
        PHRASE_GAP = cfg["phrases"]["phrase_gap"]
        PHRASE_PITCH_TOLERANCE = cfg["phrases"]["phrase_pitch_tolerance"]
        STRETCH_FACTOR = cfg["phrases"]["stretch_factor"]

        # Final mash
        FINAL_MERGE_GAP = cfg["final"]["final_merge_gap"]

        # Lane export
        LANE_RANGE = cfg["lanes"]["lane_range"]

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

        # Lane normalization & export
        reference_pitch = np.median([n["pitch"] for n in notes])
        export_notes = []
        for n in notes:
            lane = round(n["pitch"] - reference_pitch)
            lane = max(-LANE_RANGE, min(LANE_RANGE, lane))
            export_notes.append({
                "start": round(n["start"], 3),
                "duration": round(n["end"] - n["start"], 3),
                "lane": int(lane)
            })

        self.export_data = {
            "name": str(self.audio_path.stem),
            "length": total_samples / sr,
            "lanes": LANE_RANGE * 2 + 1,
            "notes": export_notes,
            "pitches": [{"time": float(t), "pitch": float(p)} for t, p in zip(times, raw_pitches)],
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