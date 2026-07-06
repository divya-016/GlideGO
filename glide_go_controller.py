# ============================================================
#  GLIDE GO — Python Final Controller
#  Hand registration + WiFi + Gesture recognition
#
#  INSTALL (run once):
#  pip install opencv-python mediapipe numpy
#
#  HOW TO RUN:
#  1. Turn on phone hotspot "divya's A14"
#  2. Connect laptop WiFi to "divya's A14"
#  3. Power ESP32 via battery, wait 6 seconds
#  4. Run: python glide_go_controller.py
#  5. FIRST TIME: press R to register your hand (10 seconds)
#  6. After registration: show hand to control motors!
#
#  GESTURES:
#  Open palm   = FORWARD
#  Fist        = BACKWARD
#  Index left  = TURN LEFT
#  Index right = TURN RIGHT
#  Thumb up    = STOP
#  Press R     = Re-register hand
#  Press Q     = Quit
# ============================================================

import cv2
import mediapipe as mp
import socket
import time
import numpy as np
import json
import os

# ============================================================
#  CONFIG — change ESP32_IP to your ESP32's IP from Serial Monitor
# ============================================================
ESP32_IP   = "192.168.43.200"   # <-- change this to your ESP32 IP
ESP32_PORT = 8888

# Hand profile saved here permanently
PROFILE_FILE    = "hand_profile.json"

# Registration settings
REGISTER_SECONDS = 10
REGISTER_FPS     = 10
REGISTER_FRAMES  = REGISTER_SECONDS * REGISTER_FPS  # 100 frames

# Match threshold — 0.82 is good balance (lower=looser, higher=stricter)
MATCH_THRESHOLD  = 0.82

# ============================================================
#  GLOBALS
# ============================================================
sock           = None
wifi_connected = False
last_command   = ''
last_distance  = 999.0
owner_profile  = None
is_owner       = False

mp_hands = mp.solutions.hands
mp_draw  = mp.solutions.drawing_utils

CMD_LABEL = {
    'F': 'FORWARD',
    'B': 'BACKWARD',
    'L': 'TURN LEFT',
    'R': 'TURN RIGHT',
    'S': 'STOP'
}
CMD_COLOR = {
    'F': (0, 200, 0),
    'B': (0, 100, 255),
    'L': (255, 180, 0),
    'R': (255, 180, 0),
    'S': (120, 120, 120)
}
GUIDE = [
    "Open palm   =  FORWARD",
    "Fist           =  BACKWARD",
    "Index left   =  TURN LEFT",
    "Index right  =  TURN RIGHT",
    "Thumb up   =  STOP",
]

# ============================================================
#  HAND SIGNATURE — extract unique hand fingerprint
# ============================================================
def extract_signature(hand_landmarks):
    pts = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark])
    wrist = pts[0]
    pts   = pts - wrist
    scale = np.linalg.norm(pts[9])
    if scale < 1e-6:
        return None
    pts = pts / scale
    return pts.flatten()

def average_signatures(signatures):
    return np.mean(signatures, axis=0)

def similarity(sig1, sig2):
    dot   = np.dot(sig1, sig2)
    norm1 = np.linalg.norm(sig1)
    norm2 = np.linalg.norm(sig2)
    if norm1 < 1e-6 or norm2 < 1e-6:
        return 0.0
    return dot / (norm1 * norm2)

# ============================================================
#  SAVE / LOAD PROFILE
# ============================================================
def save_profile(profile):
    with open(PROFILE_FILE, 'w') as f:
        json.dump(profile.tolist(), f)
    print(f"Hand profile saved to {PROFILE_FILE}")

def load_profile():
    if not os.path.exists(PROFILE_FILE):
        return None
    with open(PROFILE_FILE, 'r') as f:
        data = json.load(f)
    print("Hand profile loaded!")
    return np.array(data)

# ============================================================
#  HAND REGISTRATION — 10 second scan
# ============================================================
def register_hand(cap, hands):
    print("\n" + "="*50)
    print("HAND REGISTRATION — hold open palm steady")
    print(f"Scanning for {REGISTER_SECONDS} seconds...")
    print("="*50 + "\n")

    signatures   = []
    start_time   = time.time()
    last_capture = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame   = cv2.flip(frame, 1)
        rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result  = hands.process(rgb)
        elapsed = time.time() - start_time
        remaining = max(0, REGISTER_SECONDS - int(elapsed))

        h, w = frame.shape[:2]

        # Dark overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0,0), (w,h), (0,0,0), -1)
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)

        # Progress bar
        progress = min(elapsed / REGISTER_SECONDS, 1.0)
        bar_w    = int((w-60) * progress)
        cv2.rectangle(frame, (30, h-60), (w-30, h-30), (60,60,60), -1)
        cv2.rectangle(frame, (30, h-60), (30+bar_w, h-30), (0,200,0), -1)
        cv2.putText(frame, f"{int(progress*100)}%", (w//2-20, h-38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        cv2.putText(frame, f"REGISTERING: {remaining}s left", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,220,255), 2)
        cv2.putText(frame, f"Frames: {len(signatures)}/{REGISTER_FRAMES}",
                    (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200,200,200), 1)

        if result.multi_hand_landmarks:
            for hand_lm in result.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_lm, mp_hands.HAND_CONNECTIONS)
                if time.time() - last_capture >= (1.0 / REGISTER_FPS):
                    sig = extract_signature(hand_lm)
                    if sig is not None:
                        signatures.append(sig)
                        last_capture = time.time()
            cv2.putText(frame, "HAND DETECTED", (30,130),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        else:
            cv2.putText(frame, "NO HAND — show your open palm!", (30,130),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

        cv2.imshow("GLIDE GO", frame)
        cv2.waitKey(1)

        if elapsed >= REGISTER_SECONDS:
            break

    if len(signatures) < 10:
        print("[ERROR] Not enough frames — try again in better lighting.")
        return None

    profile = average_signatures(signatures)
    save_profile(profile)
    print(f"Done! Captured {len(signatures)} frames.")
    print("Suitcase is now locked to your hand!\n")
    return profile

# ============================================================
#  WIFI CONNECT
# ============================================================
def connect_wifi():
    global sock, wifi_connected
    print(f"Connecting to ESP32 at {ESP32_IP}:{ESP32_PORT}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((ESP32_IP, ESP32_PORT))
        sock.settimeout(0)
        wifi_connected = True
        print("WiFi connected to ESP32!\n")
    except Exception as e:
        print(f"[WARNING] WiFi failed: {e}")
        print("DEMO MODE — gestures work but no motor commands sent\n")
        wifi_connected = False

# ============================================================
#  SEND COMMAND
# ============================================================
def send_command(cmd):
    global last_command, sock, wifi_connected
    if cmd == last_command:
        return
    last_command = cmd
    print(f"[GESTURE -> CMD] {cmd}")
    if wifi_connected and sock:
        try:
            sock.send(cmd.encode())
        except Exception as e:
            print(f"[Send error] {e}")
            wifi_connected = False

# ============================================================
#  READ ESP32 RESPONSE
# ============================================================
def read_esp32():
    global last_distance, wifi_connected, sock
    if not wifi_connected or not sock:
        return
    try:
        data = sock.recv(128).decode('utf-8', errors='ignore').strip()
        if data:
            for line in data.split('\n'):
                line = line.strip()
                if line.startswith("DIST:"):
                    try:
                        last_distance = float(line.split(":")[1])
                    except:
                        pass
                elif line:
                    print(f"[ESP32] {line}")
    except BlockingIOError:
        pass
    except Exception as e:
        print(f"[Read error] {e}")

# ============================================================
#  GESTURE DETECTION
# ============================================================
def fingers_up(lm):
    tips = [4, 8, 12, 16, 20]
    pip  = [2, 6, 10, 14, 18]
    f    = []
    f.append(1 if lm.landmark[4].x < lm.landmark[3].x else 0)
    for i in range(1, 5):
        f.append(1 if lm.landmark[tips[i]].y < lm.landmark[pip[i]].y else 0)
    return f

def get_gesture(lm):
    f       = fingers_up(lm)
    total   = sum(f)
    tip_x   = lm.landmark[8].x
    wrist_x = lm.landmark[0].x
    if f == [1, 0, 0, 0, 0]: return 'S'
    if total == 5:             return 'F'
    if total == 0:             return 'B'
    if f == [0, 1, 0, 0, 0]:
        return 'L' if tip_x < wrist_x else 'R'
    return 'S'

# ============================================================
#  HUD OVERLAY
# ============================================================
def draw_hud(frame, cmd, dist, owner_detected, profile_loaded):
    h, w  = frame.shape[:2]
    col   = CMD_COLOR.get(cmd, (255,255,255))
    label = CMD_LABEL.get(cmd, '?')

    # Command box
    cv2.rectangle(frame, (10,10), (320,70), (0,0,0), -1)
    cv2.rectangle(frame, (10,10), (320,70), col, 2)
    cv2.putText(frame, f"CMD: {label}", (20,52),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, col, 2)

    # Distance box
    dcol = (0,220,0) if dist > 20 else (0,0,255)
    cv2.rectangle(frame, (10,78), (320,118), (0,0,0), -1)
    cv2.putText(frame, f"Dist: {dist:.1f} cm", (18,108),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, dcol, 2)

    # Owner status box
    if not profile_loaded:
        own_col = (0,100,255)
        own_txt = "NO PROFILE — Press R to register"
    elif owner_detected:
        own_col = (0,220,0)
        own_txt = "OWNER DETECTED"
    else:
        own_col = (0,0,200)
        own_txt = "UNKNOWN HAND — IGNORED"

    cv2.rectangle(frame, (10,126), (420,166), (0,0,0), -1)
    cv2.rectangle(frame, (10,126), (420,166), own_col, 2)
    cv2.putText(frame, own_txt, (18,152),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, own_col, 2)

    # WiFi status
    wf_col = (0,220,0) if wifi_connected else (0,0,200)
    wf_txt = "WiFi: Connected" if wifi_connected else "WiFi: DEMO MODE"
    cv2.putText(frame, wf_txt, (18, h-40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, wf_col, 1)

    # Hint
    cv2.putText(frame, "R = re-register  |  Q = quit", (18, h-18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150,150,150), 1)

    # Gesture guide bottom right
    for i, g in enumerate(GUIDE):
        cv2.putText(frame, g, (w-310, h-120+i*22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200,200,200), 1)
    return frame

# ============================================================
#  CAMERA OPEN
# ============================================================
def open_camera():
    for idx in [0, 1, 2]:
        print(f"Trying camera index {idx}...")
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            continue
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        print("Warming up camera...")
        for _ in range(20):
            cap.read()
            time.sleep(0.05)
        ret, frame = cap.read()
        if ret and frame is not None and np.mean(frame) > 5:
            print(f"Camera ready on index {idx}!\n")
            return cap
        cap.release()
    return None

# ============================================================
#  MAIN
# ============================================================
def main():
    global owner_profile, is_owner

    # 1. Connect WiFi
    connect_wifi()

    # 2. Open camera
    cap = open_camera()
    if cap is None:
        print("[ERROR] No camera found! Close Phone Link and retry.")
        if sock: sock.close()
        return

    # 3. MediaPipe
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.6
    )

    # 4. Load hand profile
    owner_profile = load_profile()
    if owner_profile is None:
        print("No hand profile found! Press R on camera window to register.\n")
    else:
        print("Owner profile loaded — you're good to go!\n")

    # 5. Create window
    cv2.namedWindow("GLIDE GO", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("GLIDE GO", 800, 600)
    cv2.moveWindow("GLIDE GO", 50, 50)

    print("Show your hand to control the motors.")
    print("Press R to register/re-register your hand.")
    print("Press Q to quit.\n")

    # ---- MAIN LOOP ----
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("[ERROR] Camera lost!")
            break

        frame  = cv2.flip(frame, 1)
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        cmd      = 'S'
        is_owner = False

        if result.multi_hand_landmarks:
            for hand_lm in result.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_lm, mp_hands.HAND_CONNECTIONS)

                if owner_profile is not None:
                    sig = extract_signature(hand_lm)
                    if sig is not None:
                        score = similarity(sig, owner_profile)

                        # Show match score on screen
                        cv2.putText(frame, f"Match: {score:.2f}", (10,195),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,0), 1)

                        if score >= MATCH_THRESHOLD:
                            is_owner = True
                            cmd = get_gesture(hand_lm)
                        else:
                            is_owner = False
                            cmd = 'S'   # unknown hand — ignore
                else:
                    cmd = 'S'   # no profile yet — don't move

        send_command(cmd)
        read_esp32()

        frame = draw_hud(frame, cmd, last_distance, is_owner, owner_profile is not None)
        cv2.imshow("GLIDE GO", frame)

        key = cv2.waitKey(10) & 0xFF

        if key == ord('q'):
            print("Quitting...")
            break

        if key == ord('r') or key == ord('R'):
            print("\nStarting hand registration...")
            send_command('S')
            new_profile = register_hand(cap, hands)
            if new_profile is not None:
                owner_profile = new_profile
            print("Back to control mode.\n")

    # Cleanup
    send_command('S')
    cap.release()
    cv2.destroyAllWindows()
    if sock:
        try:
            sock.close()
        except:
            pass
    print("GLIDE GO stopped.")

if __name__ == "__main__":
    main()
