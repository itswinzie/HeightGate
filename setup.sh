#!/bin/bash

set -e

echo ""
echo "  __   ______   _______ ____   ___  _   _  __  "
echo " / /  / ___\ \ / /_   _|  _ \ / _ \| \ | | \ \ "
echo "| |  | |    \ V /  | | | |_) | | | |  \| |  | |"
echo "| |  | |___  | |   | | |  _ <| |_| | |\  |  | |"
echo "| |   \____| |_|   |_| |_| \_\\___/|_| \_|  | |"
echo " \_\                                       /_/  "
echo ""
echo "=== Height Gate Setup ==="
echo ""

# [1] Create virtual environment
echo "[1] Creating virtual environment..."
python3 -m venv venv

# [2] Activate venv
echo "[2] Activating virtual environment..."
source venv/bin/activate

# [3] Upgrade pip
echo "[3] Upgrading pip..."
pip install --upgrade pip

# [4] Install OpenCV
echo "[4] Installing OpenCV..."
pip install opencv-python

# [5] Install MediaPipe
echo "[5] Installing MediaPipe..."
pip install mediapipe==0.10.9

# [6] Force numpy version (IMPORTANT - LAST)
echo "[6] Fixing numpy version..."
pip install "numpy<2" --force-reinstall

# Verify everything
echo "[7] Verifying installation..."
python - <<EOF
import cv2, numpy
print("OpenCV:", cv2.__version__)
print("NumPy:", numpy.__version__)
EOF

echo ""
echo "=== Setup complete ==="
echo ""
echo "To run project:"
echo "source venv/bin/activate"
echo "python main.py"
