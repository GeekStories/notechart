# Notechart

Generate SingStar-style notecharts from audio for rhythm games.

**Notechart** is an open-source project for extracting rhythm/game note timelines from vocal stems. It allows you to generate note charts, preview them, and export for use in rhythm games or other interactive applications.

---

## Features

- Extract vocal/instrumental notes from audio
- Generate SingStar-style notecharts
- Export note data for Unity or other game engines
- Preview note timelines in Python before export
- Lightweight and easy-to-integrate

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/GeekStories/notechart.git
cd notechart
```

2. Install dependencies (example using pip):

```bash
pip install -r requirements.txt
```

Note: This project uses [aubio](https://aubio.org/) under GPLv3.

## Usage

```python
from notechart import NoteChartGenerator

# Initialize generator
generator = NoteChartGenerator("path/to/audio/file.wav")

# Generate note chart
chart = generator.generate_chart()

# Preview in Python (optional)
generator.preview(chart)

# Export to Unity-friendly format
generator.export(chart, "output/chart.json")
```

_Example output for Hurt by Johnny Cash_

![Example output of the vocal track for Hurt by Johnny Cash](images/chart_example.png)

You can see the full generated output [here](output/demo_notes.json)

## Profiles / Songs

The file [defaults.json](notechart//configs//defaults.json) won't work for every track. So, make a copy and give it a name; you can use 1 profile config and 1 song config in total (or either or none, default settings will be used where no options are given). Each config is merged into the default to make up your overall settings. Place your configs under `notechart/configs/profiles` or `notechart/configs/songs`, or pass a custom config path with --config-dir (must use a `song` and a `profiles` folder)

`min_freq` (Hz): Minimum frequency to consider as a valid pitch.

- Example: 70 Hz ignores very low rumble or noise.
- Useful to filter out bass/floor noise or male/female voice range extremes.

`max_freq` (Hz): Maximum frequency to consider.

- Example: 300 Hz limits to vocal range; higher frequencies are ignored.

`window_size` (samples): Size of the analysis window for pitch detection (aubio’s yin algorithm).

- Larger windows → more stable pitch detection but less time resolution.
- Smaller windows → faster response but noisier pitch results.

`hop_size` (samples): Step size between analysis frames.

- Smaller hop → more frequent pitch updates, smoother but more CPU-heavy.
- Larger hop → less precise timing, but faster processing.

`smooth_frames`: Number of frames for moving average smoothing.

- Reduces small pitch jitters (“micro wobble”) in the raw pitch data.
- Example: 5 frames → averages 5 consecutive frames, ignoring zeros.

`stability_frames`: Number of consecutive frames a pitch must remain the same to be considered “stable.”

- Prevents rapid switching between similar notes.
- Example: 6 frames → the pitch must be steady for ~6 hop intervals.

`hold_tolerance`: Maximum allowed change in pitch to “hold” the previous note.

- Helps prevent breaking a single sung note into multiple notes due to tiny pitch fluctuations.
- Example: 0.75 (in MIDI units) → pitches within ±0.75 are treated as the same note.

`min_note_duration` (seconds): Ignore very short notes below this duration.

- Filters out micro-spikes and noise in pitch detection.
- Example: 0.12s → notes shorter than 120 ms are discarded.

`merge_gap` (seconds): Maximum time gap between consecutive notes to merge them.

- Small pauses are ignored, treating them as one continuous note.

`merge_pitch_tolerance` (MIDI units): Maximum pitch difference for merging consecutive notes.

- Prevents merging notes that are significantly different.
- Example: 0.5 → two notes less than half a semitone apart are merged.

`phrase_gap` (seconds): Maximum allowed silence between notes for them to be part of the same phrase.

- Example: 0.45 → notes separated by ≤450 ms are grouped into the same phrase.

`phrase_pitch_tolerance` (MIDI units): Maximum pitch difference within a phrase.

- Example: 1.75 → notes within ~2 semitones are considered part of the same phrase.

`stretch_factor`: Stretch or compress the duration of notes in a phrase.

- Example: 1.25 → increases note duration by 25%, often to match rhythm game timing.

`final_merge_gap` (seconds): Gap threshold for the last pass of merging notes.

- Ensures very short gaps at the end of sequences are combined to prevent fragmented note charts.

`lane_range`: Number of lanes above and below a reference pitch for the notechart.

- Total lanes = lane_range \* 2 + 1.
- Example: 4 → total 9 lanes, with middle lane as reference pitch.
- Determines how finely pitches are mapped to lanes in-game.

## Contributing

Contributions are welcome!

- Fork the repo
- Make changes in a feature branch
- Submit a pull request

Please follow [PEP8](https://www.python.org/dev/peps/pep-0008/) for code style.
