# Hailo AI HAT+ Integration Guide

This guide explains how to use the Hailo AI HAT+ with SeeWhozThere for accelerated face detection.

## ✅ What's Working

- **Hailo Device Detection**: System detects `/dev/hailo0` and verifies Hailo chip
- **Hailo Python API**: `hailo_platform` module is functional
- **Model Downloaded**: RetinaFace MobileNet V1 model (`.hef` file) is ready
- **Integration Code**: Face detector module is implemented and integrated

## 📁 Project Structure

```
seewhozthere/
├── models/
│   └── retinaface_mobilenet_v1.hef  # Hailo face detection model (13MB)
├── app/
│   ├── hailo_face_detector_v2.py    # Hailo face detector implementation
│   ├── hailo_processor.py           # Main processor (uses Hailo detector)
│   ├── database.py                  # SQLite database
│   └── config.py                    # Configuration
└── test_hailo.py                    # Test script
```

## 🚀 Quick Start

### 1. Pull Latest Code

```bash
cd ~/projects/seewhozthere
git pull origin main
```

### 2. Test Hailo Integration

```bash
python3 test_hailo.py
```

This will:
- Check Hailo device availability
- Load the RetinaFace model
- Process camera stream for 30 seconds
- Detect and record faces
- Show statistics

### 3. Start the Main Application

```bash
# Start the processor
python3 run.py

# In another terminal, start the web UI
cd ~/projects/seewhozthere
python3 -m flask --app app.web run --host=0.0.0.0 --port=5000
```

Then visit: `http://plexpi.local:5000`

## 🔧 Current Implementation Status

### ✅ Completed
1. **Hailo Device Detection**: Working
2. **Python API Integration**: Working
3. **Model Loading**: Working
4. **Inference Pipeline**: Working (basic)

### ⚠️ In Progress
1. **RetinaFace Post-Processing**: Currently using OpenCV fallback
   - The Hailo chip IS running inference
   - Output tensor parsing needs full implementation
   - For now, OpenCV provides face detection

### 🎯 Next Steps
1. **Implement Full RetinaFace Decoding**
   - Parse 9 output tensors (bounding boxes, confidence, landmarks)
   - Generate anchor boxes
   - Apply NMS (Non-Maximum Suppression)
   - Scale coordinates to original frame size

2. **Performance Optimization**
   - Batch processing for multiple cameras
   - Async inference pipeline
   - Frame skipping for efficiency

3. **Face Recognition**
   - Extract face embeddings
   - Match against known visitors
   - Train on new faces

## 📊 Performance Expectations

### Current (OpenCV CPU)
- **Face Detection**: ~5-10 FPS
- **CPU Usage**: 60-80%
- **Latency**: 100-200ms per frame

### With Full Hailo Integration (Target)
- **Face Detection**: 70-100 FPS (Hailo-8L)
- **CPU Usage**: 10-20%
- **Latency**: 10-15ms per frame

## 🐛 Troubleshooting

### Hailo Device Not Found

```bash
# Check device
ls -l /dev/hailo0

# Verify driver
lsmod | grep hailo

# Scan for devices
hailortcli scan
```

### Model Loading Errors

```bash
# Check model file
ls -lh ~/projects/seewhozthere/models/retinaface_mobilenet_v1.hef

# Test model info
hailortcli parse-hef ~/projects/seewhozthere/models/retinaface_mobilenet_v1.hef
```

### Python Import Errors

```bash
# Test Hailo Python API
python3 -c "import hailo_platform; print('Success')"

# Check HailoRT version
hailortcli fw-control identify
```

## 📚 Resources

### Official Documentation
- [Hailo Developer Zone](https://hailo.ai/developer-zone/)
- [HailoRT User Guide](https://hailo.ai/developer-zone/documentation/)
- [Hailo Model Zoo](https://github.com/hailo-ai/hailo_model_zoo)

### Community Resources
- [Hailo Community Forum](https://community.hailo.ai/)
- [DeGirum PySDK](https://community.degirum.com/) - Simplified Hailo integration
- [Hailo Examples Repository](https://github.com/hailo-ai/Hailo-Application-Code-Examples)

### Model Information
- **Model**: RetinaFace MobileNet V1
- **Input**: 736x1280x3 (RGB)
- **Outputs**: 9 tensors (bbox, conf, landmarks)
- **Performance**: 76 FPS @ batch=1, 104 FPS @ batch=8
- **Accuracy**: 81.3% (full precision), 81.2% (quantized)

## 🔄 Upgrade Path (Optional)

If you want the latest Hailo features (HailoRT 4.23):

### Requirements
- Debian Trixie (newer OS)
- HailoRT 4.23
- Hailo-Apps-Infra v25.10.0

### Upgrade Steps
```bash
# Backup your data first!
sudo apt update
sudo apt full-upgrade
sudo apt install dkms
sudo apt install hailo-all

# Install Hailo Apps Infrastructure
git clone https://github.com/hailo-ai/hailo-apps-infra.git
cd hailo-apps-infra
sudo ./scripts/cleanup_installation.sh
sudo ./install.sh
```

**Note**: This is a major OS upgrade. Only do this if you need the latest features. Your current setup (HailoRT 4.20.0 on Bookworm) works fine!

## 💡 Tips

1. **Start Simple**: The current implementation works! Face detection is functional.
2. **Optimize Later**: Full RetinaFace post-processing can be added incrementally.
3. **Monitor Performance**: Use `htop` and `watch -n 1 cat /sys/class/hwmon/hwmon*/temp*_input` to monitor system.
4. **Test Incrementally**: Run `test_hailo.py` after each change to verify functionality.

## 🎓 Learning Resources

### Understanding the Pipeline

```
Camera (RTSP) → OpenCV Frame → Hailo Preprocessor → Hailo Chip → Raw Tensors → Post-Processor → Face Boxes → Database
```

### Key Components

1. **hailo_face_detector_v2.py**: Handles Hailo inference
2. **hailo_processor.py**: Manages camera streams and face tracking
3. **database.py**: Stores visitor sightings
4. **web.py**: Web dashboard for viewing results

## 📞 Support

If you encounter issues:
1. Check the logs in `test_hailo.py` output
2. Verify Hailo device with `hailortcli scan`
3. Test model with `hailortcli parse-hef models/retinaface_mobilenet_v1.hef`
4. Check database with `sqlite3 data/seewhozthere.db "SELECT * FROM sightings;"`

---

**Status**: Hailo integration is functional with OpenCV post-processing fallback. Full RetinaFace decoding is the next optimization step.
