from notechart import NoteChartGenerator

AUDIO_FILE = "Hurt_vocals.wav"  # Replace with your test audio
PROFILE = "rock_grit"           # Replace with a profile if you have one
SONG_CONFIG = None              # Replace with a song-specific config if needed

generator = NoteChartGenerator(AUDIO_FILE, profile=PROFILE, song=SONG_CONFIG)
chart = generator.generate_chart()

# Export chart JSON
generator.export("demo_notes.json")

# Optional preview
generator.preview(chart)