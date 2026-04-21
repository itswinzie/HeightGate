"""
Height Gate System — Edge AI
Jetson Orin NX | OpenCV + MediaPipe Pose
=========================================
Camera mounted in front of a door.
A virtual horizontal line is set as the height threshold.

Logic:
  Head ABOVE line  →  OK     (passes threshold)
  Head BELOW line  →  NOT OK (fails threshold)

Hotkeys:
  W / S       →  move line ±1px (up/down)
  A / D       →  move line ±10px
  L           →  lock / unlock line + auto-save
  SPACE       →  log current result to file
  Q           →  quit
"""

import cv2
import mediapipe as mp
import numpy as np
import argparse
import json
import os
import time
from datetime import datetime


# ─────────────────────────────────────────────
#  KONSTANT
# ─────────────────────────────────────────────
WINDOW_NAME = "Height Gate"
LINE_FILE   = "gate_line.json"
LOG_FILE    = "gate_log.txt"

# Warna (BGR)
C_WHITE  = (255, 255, 255)
C_GRAY   = (150, 150, 150)
C_DGRAY  = (55,  55,  55)
C_BLACK  = (0,   0,   0)
C_GREEN  = (50,  210, 80)
C_RED    = (50,  50,  220)
C_LINE   = (60,  210, 255)   # garis threshold — cyan
C_YELLOW = (30,  200, 220)   # garis locked

FONT = cv2.FONT_HERSHEY_SIMPLEX


# ─────────────────────────────────────────────
#  SIMPAN / LOAD POSISI GARIS
# ─────────────────────────────────────────────
def load_line(frame_h):
    """
    Load line position from file.
    Stored as ratio (0.0–1.0) so it remains correct if resolution changes.
    """
    if os.path.exists(LINE_FILE):
        with open(LINE_FILE) as f:
            d = json.load(f)
        y = int(d["ratio"] * frame_h)
        print(f"[INFO] Line loaded: y={y}px  (ratio={d['ratio']:.4f})")
        return y
    default = int(frame_h * 0.40)   # default 40% from top
    print(f"[INFO] New line: y={default}px (default)")
    return default


def save_line(line_y, frame_h):
    d = {
        "line_y":   line_y,
        "ratio":    round(line_y / frame_h, 6),
        "frame_h":  frame_h,
        "saved_at": datetime.now().isoformat()
    }
    with open(LINE_FILE, "w") as f:
        json.dump(d, f, indent=2)
    print(f"[SAVE] Line saved: y={line_y}px")


def log_result(passed, head_y, line_y):
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tag = "OK" if passed else "NOT_OK"
    row = f"{ts}  {tag}  head={head_y}px  line={line_y}px\n"
    with open(LOG_FILE, "a") as f:
        f.write(row)


# ─────────────────────────────────────────────
#  GET HEAD POSITION
# ─────────────────────────────────────────────
def get_head_y(landmarks, frame_h):
    """
    Nose landmark (index 0) shifted 4% upward = approximate top of head.
    Returns pixel Y, or None if visibility is too low.
    """
    nose = landmarks[0]
    if nose.visibility < 0.45:
        return None
    return int((nose.y - 0.04) * frame_h)


# ─────────────────────────────────────────────
#  DRAW UI
# ─────────────────────────────────────────────
def draw_threshold_line(frame, line_y, locked, w):
    color = C_YELLOW if locked else C_LINE

    # Main line
    cv2.line(frame, (0, line_y), (w, line_y), color, 2)

    # Label
    status = "LOCKED" if locked else "ADJUST: W/S  A/D"
    cv2.putText(frame, status, (10, line_y - 8),
                FONT, 0.45, color, 1)

    # Arrow markers on left & right edges
    pts_l = np.array([[0, line_y - 8], [0, line_y + 8], [12, line_y]], np.int32)
    pts_r = np.array([[w, line_y - 8], [w, line_y + 8], [w - 12, line_y]], np.int32)
    cv2.fillPoly(frame, [pts_l, pts_r], color)


def draw_result_overlay(frame, passed, h, w):
    """OK / NOT OK — large text, centre of frame."""
    if passed is None:
        return

    text  = "OK" if passed else "NOT OK"
    color = C_GREEN if passed else C_RED
    bg    = (0, 50, 15) if passed else (0, 0, 55)
    scale = 2.8 if passed else 2.0
    thick = 4

    (tw, th), _ = cv2.getTextSize(text, FONT, scale, thick)
    tx = (w - tw) // 2
    ty = (h + th) // 2

    # Semi-transparent background
    pad = 24
    ovl = frame.copy()
    cv2.rectangle(ovl,
                  (tx - pad, ty - th - pad),
                  (tx + tw + pad, ty + pad),
                  bg, -1)
    cv2.addWeighted(ovl, 0.55, frame, 0.45, 0, frame)

    cv2.putText(frame, text, (tx, ty), FONT, scale, color, thick)


def draw_head_marker(frame, head_y, w, passed):
    """Small dot at head position."""
    x   = w // 2
    col = C_GREEN if passed else C_RED
    cv2.circle(frame, (x, head_y), 9, col, -1)
    cv2.circle(frame, (x, head_y), 9, C_WHITE, 1)


def draw_info_panel(frame, line_y, head_y, pose_ok, fps, h, w):
    """Small info panel — bottom left."""
    rows = [
        f"Line  : {line_y}px",
        f"Head  : {head_y}px" if head_y else "Head  : --",
        f"Pose  : {'detected' if pose_ok else 'none'}",
        f"FPS   : {fps:.0f}",
    ]
    ph   = len(rows) * 17 + 10
    px   = 8
    py   = h - ph - 8

    ovl = frame.copy()
    cv2.rectangle(ovl, (px - 4, py - 4), (px + 175, py + ph), C_BLACK, -1)
    cv2.addWeighted(ovl, 0.5, frame, 0.5, 0, frame)

    for i, r in enumerate(rows):
        col = C_GRAY if i < 2 else (C_GREEN if (i == 2 and pose_ok) else C_GRAY)
        cv2.putText(frame, r, (px, py + i * 17 + 13), FONT, 0.42, col, 1)

    # Hotkeys — bottom right
    keys = [
        "Q - Quit",
        "SPACE - Log",
        "L - Lock/Unlock",
        "A/D - ±10px",
        "W/S - ±1px",
    ]
    for i, k in enumerate(keys):
        cv2.putText(frame, k, (w - 175, h - 10 - i * 16),
                    FONT, 0.40, C_DGRAY, 1)
        col = C_GRAY if i < 2 else (C_GREEN if (i == 2 and pose_ok) else C_GRAY)
        cv2.putText(frame, r, (px, py + i * 17 + 13), FONT, 0.42, col, 1)

    # Hotkeys — kanan bawah
    keys = [
        "Q - Keluar",
        "SPACE - Log",
        "L - Lock/Unlock",
        "A/D - ±10px",
        "W/S - ±1px",
    ]
    for i, k in enumerate(keys):
        cv2.putText(frame, k, (w - 175, h - 10 - i * 16),
                    FONT, 0.40, C_DGRAY, 1)


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Height Gate — Edge AI")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width",  type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--flip",   action="store_true", help="Mirror camera horizontally")
    args = parser.parse_args()

    # Camera
    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print(f"[ERR] Cannot open camera {args.camera}.")
        return

    fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[INFO] Resolution: {fw}x{fh}")

    # MediaPipe Pose
    mp_pose = mp.solutions.pose
    mp_draw = mp.solutions.drawing_utils
    pose    = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,
        enable_segmentation=False,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.5,
    )

    # State
    line_y = load_line(fh)
    locked = False
    fps    = 0.0
    fps_t  = time.time()
    fps_n  = 0

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, fw, fh)

    print()
    print("  W / S     →  line ±1px")
    print("  A / D     →  line ±10px")
    print("  L         →  lock / unlock + save")
    print("  SPACE     →  log result")
    print("  Q         →  quit")
    print()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if args.flip:
            frame = cv2.flip(frame, 1)

        h, w = frame.shape[:2]

        # ── Pose detection
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = pose.process(rgb)
        rgb.flags.writeable = True

        head_y = None
        passed = None
        pose_ok = False

        if results.pose_landmarks:
            pose_ok = True
            lm = results.pose_landmarks.landmark

            # Subtle skeleton
            mp_draw.draw_landmarks(
                frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_draw.DrawingSpec(
                    color=C_DGRAY, thickness=1, circle_radius=2),
                connection_drawing_spec=mp_draw.DrawingSpec(
                    color=C_DGRAY, thickness=1)
            )

            head_y = get_head_y(lm, h)
            if head_y is not None:
                passed = head_y < line_y   # head ABOVE line = OK
                draw_head_marker(frame, head_y, w, passed)

        # ── Draw everything
        draw_result_overlay(frame, passed, h, w)
        draw_threshold_line(frame, line_y, locked, w)
        draw_info_panel(frame, line_y, head_y, pose_ok, fps, h, w)

        # ── FPS
        fps_n += 1
        now = time.time()
        if now - fps_t >= 1.0:
            fps   = fps_n / (now - fps_t)
            fps_n = 0
            fps_t = now

        cv2.imshow(WINDOW_NAME, frame)

        # ── Keyboard
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break

        elif not locked:
            if   key == ord('w'): line_y = max(10,     line_y - 1)
            elif key == ord('s'): line_y = min(h - 10, line_y + 1)
            elif key == ord('a'): line_y = max(10,     line_y - 10)
            elif key == ord('d'): line_y = min(h - 10, line_y + 10)

        if key == ord('l') or key == ord('L'):
            locked = not locked
            print(f"[INFO] Line {'LOCKED' if locked else 'UNLOCKED'} at y={line_y}px")
            if locked:
                save_line(line_y, h)

        elif key == ord(' '):
            if passed is not None and head_y is not None:
                log_result(passed, head_y, line_y)
                print(f"[LOG] {'OK' if passed else 'NOT OK'}  head={head_y}  line={line_y}")
            else:
                print("[WARN] No person detected in frame.")

    cap.release()
    pose.close()
    cv2.destroyAllWindows()
    print("[INFO] Program terminated.")


if __name__ == "__main__":
    main()

