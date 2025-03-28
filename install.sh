#!/bin/bash
# Installation script for Read Aloud

set -e

echo "Installing Read Aloud dependencies..."

# Install system dependencies
if [ -x "$(command -v apt-get)" ]; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-dev python3-gi gir1.2-gtk-3.0 \
        gir1.2-appindicator3-0.1 espeak-ng xdotool xclip
elif [ -x "$(command -v dnf)" ]; then
    sudo dnf install -y python3 python3-pip python3-devel python3-gobject gtk3 \
        libappindicator-gtk3 espeak-ng xdotool xclip
elif [ -x "$(command -v pacman)" ]; then
    sudo pacman -S --needed python python-pip python-gobject gtk3 \
        libappindicator-gtk3 espeak xdotool xclip
else
    echo "Unsupported package manager. Please install dependencies manually:"
    echo "- Python 3 with pip"
    echo "- GTK 3 and PyGObject"
    echo "- AppIndicator3"
    echo "- espeak-ng or festival"
    echo "- xdotool and xclip"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install --user -r requirements.txt

# Install the package
echo "Installing Read Aloud..."
pip3 install --user -e .

# Install desktop entry
echo "Installing desktop entry..."
mkdir -p ~/.local/share/applications
cp readaloud.desktop ~/.local/share/applications/

echo "Installation complete!"
echo "You can now run 'readaloud' from the command line or application launcher." 