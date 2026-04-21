# Height Gate System
**Vision-Based Height Gate Detection — Edge AI**
Jetson Orin NX | Python | OpenCV | MediaPipe Pose

---

## Overview

Height Gate System is a real-time, vision-based height screening tool designed to run on edge AI hardware — specifically the **NVIDIA Jetson Orin NX**. It uses a single camera mounted in front of a door or entrance to determine whether a person meets a minimum height requirement.

Instead of using a physical ruler or barrier, the system draws a **virtual horizontal line** on the camera feed. When a person walks into frame, it detects the top of their head using **MediaPipe Pose** and compares that position against the line.

The result is simple and immediate:

- Head is **above** the line → **OK** (displayed in green)
- Head is **below** the line → **NOT OK** (displayed in red)

No calibration with a known height reference is required. You simply adjust the line visually until it sits at the right height, lock it, and the system is ready.

---

## How It Works

### 1. Camera Feed
The program opens a camera stream using OpenCV. Resolution defaults to 1280×720 at 30 FPS. The buffer size is set to 1 to minimise latency, which is important for real-time edge deployment.

### 2. Pose Detection with MediaPipe
Every frame is passed through **MediaPipe Pose**, a machine learning model that detects 33 body landmarks — including the nose, shoulders, hips, ankles, and heels. The model runs in `model_complexity=1` mode, which balances accuracy and performance well on the Jetson Orin NX.

### 3. Head Position Estimation
The system uses **landmark index 0 (nose)** as the primary reference for head position. Since the nose sits slightly below the true top of the head, the Y coordinate is shifted **4% upward** in the frame to approximate the crown of the head more accurately.

```
head_y = (nose.y - 0.04) * frame_height
```

A visibility threshold of **0.45** is applied — if MediaPipe is not confident enough about the nose landmark (e.g. person is partially out of frame or facing away), the reading is discarded and no result is shown.

### 4. Threshold Line
The threshold line is a horizontal line drawn across the full width of the frame. Its vertical position (`line_y`) is stored in pixels but also saved as a **ratio** relative to the frame height. This means if you ever change the camera resolution, the line will remain proportionally correct after reload.

```json
{
  "line_y": 215,
  "ratio": 0.298611,
  "frame_h": 720,
  "saved_at": "2024-01-15T10:30:00"
}
```

### 5. Decision Logic
Once a valid head position is obtained, the comparison is straightforward:

```python
passed = head_y < line_y
```

In screen coordinates, Y increases downward. So a head that is **above** the line has a **smaller Y value** than the line — meaning the person is tall enough.

### 6. On-Screen Display
The UI is intentionally minimal:

- **Centre overlay** — large "OK" (green) or "NOT OK" (red) text with a semi-transparent background box
- **Threshold line** — cyan when adjustable, yellow when locked, with arrow markers on both edges
- **Head marker** — a small filled circle at the detected head position, coloured green or red to match the result
- **Info panel** (bottom left) — shows current line Y position, head Y position, pose detection status, and FPS
- **Hotkey guide** (bottom right) — always visible reminder of available controls
- **Skeleton overlay** — a subtle dark grey skeleton drawn over the person so you can see what MediaPipe is tracking

---

## Hardware Requirements

| Component | Requirement |
|-----------|-------------|
| Device | NVIDIA Jetson Orin NX |
| OS | Ubuntu 20.04 / JetPack 5.x |
| Python | 3.8 or higher |
| Camera | Any USB or CSI camera |
| Display | HDMI monitor or VNC |

---

## Software Dependencies

| Library | Version | Notes |
|---------|---------|-------|
| OpenCV | Any (JetPack) | **Do NOT install from pip.** Use the version that ships with JetPack — it includes CUDA acceleration. Installing `opencv-python` from pip will replace it with a CPU-only build. |
| MediaPipe | 0.10.9 | Install via pip as listed in `requirements.txt` |
| NumPy | ≥1.21.0, <2.0 | Usually pre-installed with JetPack. MediaPipe and OpenCV both depend on it. |

---

## Installation

```bash
# Clone or copy the project folder to your Jetson
cd height_system

# Make the setup script executable
chmod +x setup.sh

# Run setup
./setup.sh
```

The setup script will verify that OpenCV is available and install MediaPipe. It will warn you if OpenCV is missing rather than installing the wrong version automatically.

---

## Running the Program

```bash
# Default — camera index 0, resolution 1280x720
python3 main.py

# Use a different camera
python3 main.py --camera 1

# Mirror the image horizontally (if camera is mounted facing inward)
python3 main.py --flip

# Custom resolution
python3 main.py --width 1920 --height 1080
```

---

## Setting the Threshold Line (One-Time Setup)

This only needs to be done once. After the line is locked and saved, it will be automatically restored every time the program starts.

1. Run the program with `python3 main.py`
2. Have a person who represents the **minimum acceptable height** stand directly in front of the camera
3. Use the keyboard to adjust the line until it is positioned **just above the top of their head**:
   - `W` — move line up by 1 pixel
   - `S` — move line down by 1 pixel
   - `A` — move line up by 10 pixels
   - `D` — move line down by 10 pixels
4. Press `L` to lock the line — it will turn yellow and be saved automatically to `gate_line.json`
5. The system is now ready for operation

> **Important:** Once the line is locked and the camera is in its final position, do not move the camera. Any change in camera angle or position will invalidate the line setting and require you to redo this step.

---

## Hotkey Reference

| Key | Action |
|-----|--------|
| `W` | Move threshold line up 1 pixel |
| `S` | Move threshold line down 1 pixel |
| `A` | Move threshold line up 10 pixels |
| `D` | Move threshold line down 10 pixels |
| `L` | Toggle lock/unlock — saves line position when locking |
| `SPACE` | Log the current result to `gate_log.txt` |
| `Q` | Quit the program |

---

## Output Files

### `gate_line.json`
Created automatically when you press `L` to lock the line. Stores the line position so it can be restored on the next run.

```json
{
  "line_y": 215,
  "ratio": 0.298611,
  "frame_h": 720,
  "saved_at": "2024-01-15T10:30:00.123456"
}
```

### `gate_log.txt`
Created when you press `SPACE` to manually log a result. Each entry records the timestamp, result, head pixel position, and line pixel position.

```
2024-01-15 10:32:41  OK      head=198px  line=215px
2024-01-15 10:33:05  NOT_OK  head=248px  line=215px
2024-01-15 10:34:12  OK      head=201px  line=215px
```

---

## Camera Placement Tips

For the best detection accuracy, follow these placement guidelines:

- **Distance** — position the camera 2 to 4 metres from where the person will stand. Too close causes lens distortion; too far reduces landmark detection accuracy.
- **Height** — mount the camera at roughly chest height pointing straight ahead, or slightly angled upward. Avoid mounting too high as it creates a top-down perspective that makes height estimation unreliable.
- **Angle** — a direct front-facing view works well. A slight side angle is also acceptable.
- **Lighting** — ensure the area is well lit and avoid strong backlighting (e.g. a bright window directly behind the person), as this can reduce MediaPipe's detection confidence.
- **Background** — a plain, uncluttered background helps MediaPipe detect the person more reliably.

---

## Known Limitations

- **Single person only** — the system evaluates the first detected pose. If multiple people are in frame simultaneously, results may be unpredictable.
- **Monocular camera** — depth is not measured. The system only evaluates pixel position in the frame, so the person must stand at roughly the same distance from the camera each time for consistent results.
- **Facing the camera** — if a person is facing away or at a steep angle, the nose landmark visibility may drop below the threshold and no result will be shown.
- **Headwear** — hats, helmets, or large hairstyles may cause the head position estimate to be slightly off, since the detection is based on the nose landmark plus a fixed 4% offset.

---

## Project File Structure

```
height_system/
├── main.py            Main program — all logic in a single file
├── requirements.txt   Python dependencies (MediaPipe, NumPy)
├── setup.sh           Installation script for Jetson
├── README.md          This file
├── gate_line.json     Auto-generated when line is locked
└── gate_log.txt       Auto-generated when SPACE is pressed
```

---

## Quick Troubleshooting

**Camera not opening**
Run `ls /dev/video*` to see available camera devices. Use `--camera 1` or `--camera 2` if index 0 does not work.

**Low FPS**
Try lowering resolution with `--width 640 --height 480`. You can also set `model_complexity=0` in `main.py` for the fastest (but slightly less accurate) pose model.

**Pose not detected**
Check lighting conditions. Make sure the person's full body is visible in frame from head to feet. If only the upper body is visible, the ankle landmarks will be missing but head detection should still work.

**Line not saving**
Make sure the program has write permission in the directory where it is running. Run `chmod 755 .` in the project folder if needed.

**OpenCV import error after pip install**
If you accidentally installed `opencv-python` from pip, remove it with `pip3 uninstall opencv-python` and verify the JetPack version is still intact with `python3 -c "import cv2; print(cv2.__version__)"`.

