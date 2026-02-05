import argparse
from notechart.core import NoteChartGenerator


def build_arg_parser():
        p = argparse.ArgumentParser("notechart")

        # ------------------
        # Analysis
        # ------------------
        p.add_argument("--window-size", type=int, default=2048)
        p.add_argument("--hop-size", type=int, default=512)
        p.add_argument("--min-freq", type=float, default=50.0)
        p.add_argument("--max-freq", type=float, default=2000.0)

        # ------------------
        # Stability
        # ------------------
        p.add_argument("--smooth-frames", type=int, default=3)
        p.add_argument("--stability-frames", type=int, default=4)
        p.add_argument("--hold-tolerance", type=float, default=0.5)

        # ------------------
        # Notes
        # ------------------
        p.add_argument("--min-note-duration", type=float, default=0.1)
        p.add_argument("--merge-gap", type=float, default=0.15)
        p.add_argument("--note-pitch-tolerance", type=float, default=0.5)

        # ------------------
        # Phrases
        # ------------------
        p.add_argument("--phrase-gap", type=float, default=0.4)
        p.add_argument("--phrase-pitch-tolerance", type=float, default=1.0)
        p.add_argument("--stretch-factor", type=float, default=1.0)

        # ------------------
        # Final
        # ------------------
        p.add_argument("--final-merge-gap", type=float, default=0.2)

        # ------------------
        # Lanes
        # ------------------
        p.add_argument("--lane-range", type=int, default=4)

        return p


def build_cfg_from_args(args) -> dict:
        return {
            "window_size": args.window_size,
            "hop_size": args.hop_size,
            "min_freq": args.min_freq,
            "max_freq": args.max_freq,
            "smooth_frames": args.smooth_frames,
            "stability_frames": args.stability_frames,
            "hold_tolerance": args.hold_tolerance,
            "min_note_duration": args.min_note_duration,
            "merge_gap": args.merge_gap,
            "note_pitch_tolerance": args.note_pitch_tolerance,
            "phrase_gap": args.phrase_gap,
            "phrase_pitch_tolerance": args.phrase_pitch_tolerance,
            "stretch_factor": args.stretch_factor,
            "final_merge_gap": args.final_merge_gap,
            "lane_range": args.lane_range,
        }


def main():
    parser = build_arg_parser()
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument("-o", "--output", help="Output chart path")
    args = parser.parse_args()

    cfg = build_cfg_from_args(args)

    gen = NoteChartGenerator(
        audio_path=args.audio,
        cfg=cfg
    )

    gen.generate_chart()
    gen.export(args.output)

if __name__ == "__main__":
    main()
