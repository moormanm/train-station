#!/usr/bin/env bash
set -e

# Install Python dependencies
pip3 install --break-system-packages pygame requests pillow

# Set up autostart
mkdir -p ~/.config/autostart
cp train_station.desktop ~/.config/autostart
