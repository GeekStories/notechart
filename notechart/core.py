import json
import math
import shutil
from pathlib import Path
from platformdirs import user_config_dir

import numpy as np
import soundfile as sf
from aubio import source, pitch

# For optional preview
import matplotlib.pyplot as plt

PACKAGE_ROOT = Path(__file__).resolve().parent
PACKAGED_CONFIG_ROOT = PACKAGE_ROOT / "configs"

class NoteChartGenerator:
    def __init__(
        self,
        audio_path: str | Path,
        *,
        config_dir: str | Path | None = None,
        defaults_path: str | Path | None = None,
        profile: str | None = None,
        song: str | None = None,
    ):
        self.audio_path = Path(audio_path).expanduser().resolve()
        if not self.audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {self.audio_path}")

        self.config_root = NoteChartGenerator.resolve_config_root(config_dir)

        # Ensure defaults are there
        NoteChartGenerator.bootstrap_configs(self.config_root, PACKAGED_CONFIG_ROOT)

        self.defaults_path = (
            Path(defaults_path).expanduser().resolve()
            if defaults_path
            else self.config_root / "defaults.json"
        )

        self.profile_path = (
            self.config_root / "profiles" / f"{profile}.json"
            if profile else None
        )

        self.song_path = (
            self.config_root / "songs" / f"{song}.json"
            if song else None
        )

        self.cfg =  NoteChartGenerator.load_config(
            self.defaults_path,
            self.profile_path,
            self.song_path
        )

        self.notes = []
        self.export_data = {}

    # ------------------------------
    # CONFIG LOADING
    # ------------------------------
    def bootstrap_configs(target_dir: Path, package_config_dir: Path):
        """
        Ensure the target config dir exists and contains defaults.
        Copy from packaged configs if missing.
        """
        target_dir.mkdir(parents=True, exist_ok=True)

        for item in package_config_dir.glob("**/*.json"):
            # Relative path inside the package
            rel_path = item.relative_to(package_config_dir)
            dest = target_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(item, dest)

    def default_config_root(app_name="notechart"):
        return Path(user_config_dir(app_name))

    @staticmethod
    def resolve_config_root(config_dir: Path | None = None) -> Path:
        config_root = Path(config_dir).expanduser().resolve() if config_dir else NoteChartGenerator.default_config_root()

        try:
            config_root.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise RuntimeError(
                f"No permission to use config directory: {config_root}\n"
                "Try a directory inside your home folder or run with elevated permissions."
            ) from e

        return config_root

    def load_config(defaults_path: Path, profile: Path | None, song: Path | None):
        with open(defaults_path) as f:
            cfg = json.load(f)

        if profile:
            with open(profile) as f:
                cfg = NoteChartGenerator._deep_merge(cfg, json.load(f))

        if song:
            with open(song) as f:
                cfg = NoteChartGenerator._deep_merge(cfg, json.load(f))
        return cfg

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        result = dict(base)
        for k, v in override.items():
            if isinstance(v, dict) and k in result:
                result[k] = NoteChartGenerator._deep_merge(result[k], v)
            else:
                result[k] = v
        return result

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
    # PREVIEW
    # ------------------------------
    @staticmethod
    def preview(export_data):
        notes = export_data["notes"]
        lanes = export_data["lanes"]
        name = export_data["name"]

        min_lane = -(lanes // 2)
        max_lane = lanes // 2
        WINDOW_SECONDS = 8.0
        ZOOM_FACTOR = 0.8
        SCROLL_STEP = 0.25

        song_length = max(n["start"] + n["duration"] for n in notes)
        current_start = 0.0
        current_window = WINDOW_SECONDS

        fig, ax = plt.subplots(figsize=(14, 5))
        plt.subplots_adjust(bottom=0.15)

        def draw():
            ax.clear()
            for n in notes:
                ax.broken_barh([(n["start"], n["duration"])], (n["lane"] - 0.4, 0.8))
            ax.set_xlim(current_start, current_start + current_window)
            ax.set_ylim(min_lane - 1, max_lane + 1)
            ax.set_title(f"{name}  |  Window: {current_window:.1f}s")
            ax.set_xlabel("Time (seconds)")
            ax.set_ylabel("Lane")
            ax.set_yticks(range(min_lane, max_lane + 1))
            ax.grid(True, axis="x", alpha=0.3)
            fig.canvas.draw_idle()

        def on_scroll(event):
            nonlocal current_start
            delta = current_window * SCROLL_STEP
            if event.button == "up":
                current_start = max(0, current_start - delta)
            elif event.button == "down":
                current_start = min(song_length - current_window, current_start + delta)
            draw()

        def on_key(event):
            nonlocal current_start, current_window
            if event.key in ("+", "="):
                current_window *= ZOOM_FACTOR
            elif event.key in ("-", "_"):
                current_window /= ZOOM_FACTOR
            elif event.key == "left":
                current_start = max(0, current_start - current_window * 0.25)
            elif event.key == "right":
                current_start = min(song_length - current_window, current_start + current_window * 0.25)
            elif event.key == "home":
                current_start = 0.0
            elif event.key == "end":
                current_start = max(0, song_length - current_window)
            current_window = max(1.0, current_window)
            draw()

        fig.canvas.mpl_connect("scroll_event", on_scroll)
        fig.canvas.mpl_connect("key_press_event", on_key)

        # Assign lanes for drawing
        for n in notes:
            if "lane" not in n:
                n["lane"] = 0
        draw()
        plt.show()

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
            "configs": {
                "profile": str(self.profile_path) if self.profile_path else None,
                "song": str(self.song_path) if self.song_path else None
            },
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