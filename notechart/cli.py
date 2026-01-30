import argparse
from notechart.core import NoteChartGenerator

def main():
    parser = argparse.ArgumentParser("notechart")
    parser.add_argument("audio")
    parser.add_argument("--config")
    parser.add_argument("--config-dir")
    parser.add_argument("--profile")
    parser.add_argument("--song")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    config_root = NoteChartGenerator.resolve_config_root(args.config_dir)
    generator = NoteChartGenerator(
        args.audio,
        config_dir=config_root,
        defaults_path=args.config,
        profile=args.profile,
        song=args.song,
    )

    chart = generator.generate_chart()
    generator.export()
    
    if args.preview:
        generator.preview(chart)


if __name__ == "__main__":
    main()
