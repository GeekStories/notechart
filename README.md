# Notechart

Generate SingStar-style notecharts from audio for rhythm games.

Notechart is an open-source tool that analyzes audio files, extracts pitch over time, and converts it into playable rhythm-game notecharts. It’s designed for vocal-driven games (SingStar-like), but can be adapted for other melodic content.

---

# Features

- Pitch detection using aubio (YIN)
- Stable note extraction with smoothing, hysteresis, and gap filling
- Phrase-based note merging
- Lane-based pitch normalization for rhythm games
- JSON export suitable for game engines (Unity, custom engines, etc.)
- Simple CLI with explicit, reproducible settings

---

# Installation

Requirements

- Python 3.10+
- aubio (GPLv3)
- numpy
- soundfile

---

# Install

```
git clone https://github.com/GeekStories/notechart.git
cd notechart
pip install -r requirements.txt
```

---

# Usage

Once installed, you can use notechart in the terminal:

Example: `notechart input.wav -o output_chart.json`

# Config Options

### Analysis

- --window-size
  - FFT window size for pitch detection (default: 2048)
- --hop-size
  - Hop size between frames (default: 512)
- --min-freq Minimum
  - frequency in Hz (default: 50.0)
- --max-freq
  - Maximum frequency in Hz (default: 2000.0)

### Pitch Stability

- --smooth-frames
  - Moving average window for pitch smoothing (default: 3)
- --stability-frames
  - Frames required for pitch stability (default: 4)
- --hold-tolerance
  - Max pitch change in MIDI to hold a note (default: 0.5)

### Notes

- --min-note-duration
  - Minimum note duration in seconds (default: 0.1)
- --merge-gap
  - Time gap allowed when merging notes (default: 0.15)
- --note-pitch-tolerance
  - Pitch difference allowed when merging notes (default: 0.5)

### Phrases

- --phrase-gap
  - Max silence between notes in a phrase (default: 0.4)
- --phrase-pitch-tolerance
  - Pitch range allowed within a phrase (default: 1.0)
- --stretch-factor
  - Stretch factor applied to phrases (default: 1.0)

### Final Pass

- --final-merge-gap
  - Final gap threshold for merging (default: 0.2)

### Lane Mapping

- --lane-range
  - Number of lanes for notes (default: 9)

---

# Usage

```Python
from notechart.core import NoteChartGenerator

cfg = {
    "window_size": 2048,
    "hop_size": 512,
    "min_freq": 70.0,
    "max_freq": 800.0,
    "smooth_frames": 5,
    "stability_frames": 6,
    "hold_tolerance": 0.5,
    "min_note_duration": 0.1,
    "merge_gap": 0.15,
    "note_pitch_tolerance": 0.5,
    "phrase_gap": 0.4,
    "phrase_pitch_tolerance": 1.0,
    "stretch_factor": 1.0,
    "final_merge_gap": 0.2,
    "lane_range": 9
}

gen = NoteChartGenerator("audio.wav", cfg=cfg)
chart = gen.generate_chart()
gen.export("chart.json")
```

---

# Export Format

```json
{
  "name": "Audio File stem",
  "length": "Track length in seconds",
  "lanes": "Max lanes to render",
  "notes": "List of playable notes",
  "pitches": "List of raw pitch data"
}
```

Each `note` entry contains:

- **start**: Start time in seconds
- **duration**: Duration in seconds
- **lane**: Lane index

Each `pitch` entry contains:

- **time**: Time in seconds
- **pitch**: Frequency in Hz
- **midi**: MIDI pitch value

---

# How It Works

1. Pitch extraction using aubio (YIN)
2. Octave correction and smoothing
3. MIDI quantization to half-semitones
4. Stability enforcement and pitch holding
5. Micro-gap filling
6. Note segmentation
7. Phrase merging and stretching
8. Lane normalization relative to median pitch

---

# Contributing

Contributions are welcome.

- Fork the repository
- Create a feature branch
- Submit a pull request

Please follow PEP8 for code style.

---

# License

This project is open-source and depends on aubio (GPLv3).
Any redistribution must comply with GPLv3 requirements.
