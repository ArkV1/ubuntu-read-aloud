#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="readaloud",
    version="0.1.0",
    description="Linux Read Aloud application - text-to-speech for selected text",
    author="Read Aloud Team",
    author_email="example@example.com",
    url="https://github.com/yourusername/read-aloud",
    packages=find_packages(),
    package_dir={"": "."},
    install_requires=[
        "pyttsx3>=2.90",
        "PyGObject>=3.42.0",
        "python-xlib>=0.31",
        "pyperclip>=1.8.2",
        "click>=8.1.3",
    ],
    entry_points={
        "console_scripts": [
            "readaloud=src.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Desktop Environment :: Gnome",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
    ],
    python_requires=">=3.6",
) 