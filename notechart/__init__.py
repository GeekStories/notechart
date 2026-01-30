"""
Notechart: Generate SingStar-style notecharts from audio for rhythm games.

Usage:

    from notechart import NoteChartGenerator

    generator = NoteChartGenerator("song.wav")
    chart = generator.generate_chart()
    generator.export("chart.json")
    generator.preview(chart)
"""

from .core import NoteChartGenerator

__all__ = ["NoteChartGenerator"]
