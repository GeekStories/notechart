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
git clone https://github.com/yourusername/notechart.git
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

Example output: A timeline with note timestamps, durations, and pitch values ready for importing into your rhythm game.

## Contributing

Contributions are welcome!

- Fork the repo
- Make changes in a feature branch
- Submit a pull request

Please follow [PEP8](https://www.python.org/dev/peps/pep-0008/) for code style.
