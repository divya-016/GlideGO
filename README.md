# GlideGo 🧳
### AI-Based Gesture-Controlled Smart Suitcase

GlideGo is a smart suitcase that autonomously follows its owner using real-time hand gesture recognition. Built as a final-year BCA project, it combines computer vision, embedded systems, and WiFi communication.

---

## 🎥 How It Works
- A laptop camera detects your hand gestures using MediaPipe
- Gestures are sent over WiFi to an ESP32 microcontroller
- ESP32 controls the motors to move the suitcase accordingly
- Owner-lock feature ensures only the registered owner can control it

---

## 🕹️ Gestures
| Gesture | Action |
|--------|--------|
| Open Palm | Forward |
| Fist | Backward |
| Index finger left | Turn Left |
| Index finger right | Turn Right |
| Thumb up | Stop |

---

## 🛠️ Tech Stack
- **Python** — Gesture detection & WiFi communication
- **MediaPipe** — Hand landmark recognition
- **OpenCV** — Camera feed processing
- **C++ / Arduino** — ESP32 motor control firmware
- **ESP32** — Microcontroller (WiFi + GPIO)
- **NEO-6M GPS** — Real-time location tracking
- **L298N Motor Driver** — DC motor control

---

## ✨ Features
- Real-time hand gesture recognition
- Owner-lock system using cosine similarity matching
- WiFi-based communication between laptop and ESP32
- GPS tracking
- Theft alert via wristband buzzer
- Works in demo mode even without ESP32 connected
