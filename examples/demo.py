from notechart import NoteChartGenerator

AUDIO_FILE_PATH = "path/to/your/audiofile.wav"
PROFILE = None # profile.json from configs/profiles/**PROFILE**.json
SONG_CONFIG = None # song.json from configs/songs/**SONG_CONFIG**.json

generator = NoteChartGenerator(AUDIO_FILE_PATH, profile=PROFILE, song=SONG_CONFIG)
chart = generator.generate_chart()

# Export vocal bars as JSON
generator.export("demo_notes.json")

# Optional preview
generator.preview(chart)