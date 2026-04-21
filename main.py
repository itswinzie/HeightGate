#!/bin/bash
set -e
echo "=== Height Gate Setup ==="
echo ""
echo "[1] Checking OpenCV..."
python3 -c "import cv2; print('OpenCV:', cv2.__version__)" || {
    echo "[WARN] OpenCV not found. Try: sudo apt install python3-opencv"
}
echo ""
echo "[2] Installing MediaPipe..."
pip3 install mediapipe==0.10.9
echo ""
echo "=== Setup complete ==="
echo "Run with: python3 main.py"
