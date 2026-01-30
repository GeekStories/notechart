from .core import NoteChartGenerator

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_file")
    parser.add_argument("--profile")
    parser.add_argument("--song")
    parser.add_argument("--export", "-o", default="chart.json")
    parser.add_argument("--preview", "-p", action="store_true")
    args = parser.parse_args()

    gen = NoteChartGenerator(args.audio_file, profile=args.profile, song=args.song)
    gen.generate_chart()
    gen.export(args.export)

    if args.preview:
        gen.preview(gen.export_data)