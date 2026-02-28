# BlindNav AI – Offline Intelligent Navigation System

BlindNav AI is an Android (Kotlin) application focused on assisting blind users with:

- Offline map-based navigation with OSMDroid and A* graph routing.
- Real-time obstacle detection via CameraX + TensorFlow Lite (YOLOv8n).
- Risk scoring with cooldown-aware hazard announcements.
- Voice + haptic safety alerts.
- Emergency SMS mode with GPS coordinates.

## Build prerequisites

- Android Studio Hedgehog or newer
- Android SDK 34
- JDK 17
- Physical Android device (camera + GPS + vibration + SMS)

## Required model asset

Place a **real YOLOv8 Nano TensorFlow Lite model** at:

`app/src/main/assets/yolov8n.tflite`

The project already loads this exact file at app startup.

## Build APK

1. Open project in Android Studio.
2. Sync Gradle dependencies.
3. Connect Android device and grant runtime permissions:
   - Camera
   - Fine location
   - SMS
   - Vibration
4. Build debug APK:
   - `Build > Build Bundle(s) / APK(s) > Build APK(s)`
5. Install and run.

## Offline routing graph

Navigation graph is loaded from `app/src/main/assets/osm_graph.json`.
For field deployment, generate this graph from local OSM extracts and replace the sample graph.

## Emergency mode

Long-press **Emergency (Long Press)** button in the app to send current coordinates via SMS.

