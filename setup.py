from setuptools import setup, find_packages

setup(
    name="notechart",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "aubio>=0.4.9",
        "numpy>=1.24.0",
        "soundfile>=0.12.1",
        "matplotlib>=3.7.1",
    ],
    entry_points={
        "console_scripts": [
            "notechart=notechart.cli:main",
        ],
    },
    python_requires=">=3.10",
    license="GPLv3",
    description="Generate SingStar-style notecharts from audio for rhythm games",
    author="Damon Pitkethley",
    url="https://github.com/geekstories/notechart",
)
