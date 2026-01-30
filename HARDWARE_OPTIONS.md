# SeeWhozThere - Hardware Options & Alternatives

## Current Status

The **Google Coral USB Accelerator** is experiencing global supply chain issues due to chip shortages. This document outlines alternative hardware options to ensure the project can proceed regardless of Coral availability.

---

## Option 1: Google Coral USB Accelerator (Recommended)

**Status:** Limited availability, higher prices due to chip shortage

### Specifications
- **Performance:** 4 TOPS (Tera Operations Per Second)
- **Interface:** USB 3.0 Type-C
- **Power:** 2 TOPS per watt (very efficient)
- **Compatibility:** Raspberry Pi, Linux, macOS, Windows
- **Framework:** TensorFlow Lite with Edge TPU compiler
- **Price:** $59.99 (MSRP) - Currently ~$110 on Amazon

### Pros
- Excellent performance for face detection (~400 FPS with MobileNet v2)
- Low power consumption (important for 24/7 operation)
- Well-documented with extensive community support
- Our code is already designed for Coral integration

### Cons
- Supply chain issues (hard to find in stock)
- Higher prices from third-party sellers
- Requires TensorFlow Lite models (not standard TensorFlow)

### Where to Buy
- Amazon (Seeed Studio Official): $110.99
- Mouser, Arrow, Seeed Direct: Out of stock
- eBay: Check for used units

---

## Option 2: CPU-Only Processing (No Accelerator)

**Status:** Available immediately (no additional hardware needed)

### Specifications
- **Hardware:** Raspberry Pi 5 CPU only
- **Performance:** ~5-10 FPS for face detection
- **Framework:** OpenCV + dlib (face_recognition library)

### Pros
- No additional hardware cost
- Works immediately
- Good for testing and development
- Sufficient for 1-2 cameras with motion detection

### Cons
- Lower frame rate (5-10 FPS vs 400 FPS)
- Higher CPU usage (may impact Plex server)
- Not ideal for multiple cameras

### Implementation
```python
# Install dependencies
sudo apt-get install python3-opencv
sudo pip3 install face-recognition dlib

# Use face_recognition library (built on dlib)
import face_recognition
image = face_recognition.load_image_file("photo.jpg")
face_locations = face_recognition.face_locations(image)
```

### Recommendation
**Good fallback option** while waiting for Coral. Can process 1-2 camera streams with motion-triggered recording instead of continuous processing.

---

## Option 3: Intel Neural Compute Stick 2

**Status:** More widely available than Coral

### Specifications
- **Performance:** ~100-200 FPS (less than Coral but still good)
- **Interface:** USB 3.0 Type-A
- **Framework:** OpenVINO toolkit
- **Price:** $70-100
- **Compatibility:** Raspberry Pi, Linux, Windows

### Pros
- Better availability than Coral
- Good performance for face detection
- Supports multiple model formats (TensorFlow, PyTorch, ONNX)
- Intel's OpenVINO has good documentation

### Cons
- Requires OpenVINO framework (different from TensorFlow Lite)
- Slightly lower performance than Coral
- Requires code modifications to integrate

### Where to Buy
- Amazon: Search "Intel Neural Compute Stick 2"
- Newegg, B&H Photo

### Implementation Effort
**Moderate** - Would need to convert models to OpenVINO format and update processor.py to use OpenVINO API instead of PyCoral.

---

## Option 4: Hailo-8 AI Accelerator

**Status:** Newer product with better availability

### Specifications
- **Performance:** 26 TOPS (6x faster than Coral!)
- **Interface:** M.2 or PCIe (requires Raspberry Pi 5 M.2 HAT)
- **Framework:** Hailo SDK (supports TensorFlow, PyTorch, ONNX)
- **Price:** ~$70 for M.2 version
- **Compatibility:** Raspberry Pi 5, x86 systems

### Pros
- Significantly better performance than Coral
- Newer product = better stock availability
- Supports multiple frameworks
- Future-proof (can handle more complex models)

### Cons
- Requires Raspberry Pi 5 M.2 HAT (~$10-15 additional)
- Less community support (newer product)
- Requires code modifications

### Where to Buy
- Raspberry Pi official store
- Seeed Studio
- Pimoroni

### Implementation Effort
**Moderate to High** - Would need to learn Hailo SDK and update processor.py. However, performance gains could be worth it.

---

## Option 5: Cloud-Based Processing (Fallback)

**Status:** Always available

### Services
- **AWS Rekognition:** Face detection and recognition API
- **Azure Face API:** Microsoft's face recognition service
- **Google Cloud Vision:** Face detection API

### Pros
- No hardware needed
- Highly accurate
- Scalable
- Easy to integrate

### Cons
- **Privacy concerns** (defeats the "local-first" goal)
- Ongoing costs (pay per API call)
- Requires internet connection
- Latency (slower than local processing)

### Cost Estimate
- AWS Rekognition: $1 per 1,000 images
- For 3 cameras @ 1 FPS = 259,200 images/day = $259/day ❌ **Too expensive**
- With motion detection (10 events/day): ~$0.01/day ✅ **Affordable**

### Recommendation
**Emergency fallback only** - Use only if no local hardware option works. Implement motion detection to minimize API calls.

---

## Recommended Strategy

### Phase 1: Start with CPU-Only (Now)
- Use Raspberry Pi 5 CPU for initial testing
- Implement motion detection to reduce processing load
- Process 1-2 cameras at lower frame rates
- **Cost:** $0 (already have the hardware)

### Phase 2: Monitor Coral Stock (Next 2-4 weeks)
- Set up stock alerts at Mouser, Arrow, Seeed
- Check eBay for used units
- Consider $110 Amazon price if urgent

### Phase 3: Evaluate Alternatives (If Coral unavailable after 1 month)
- **Best alternative:** Hailo-8 M.2 Accelerator (better performance, better availability)
- **Budget alternative:** Intel Neural Compute Stick 2 (easier to find)
- **Last resort:** Cloud API with motion detection

---

## Code Flexibility

The good news: Our `processor.py` module is designed to be modular. We can easily swap out the AI backend:

```python
# Current design allows for multiple processor implementations
class BaseProcessor:
    def process_frame(self, camera_name, frame):
        pass

class CoralProcessor(BaseProcessor):
    # Uses Google Coral TPU
    pass

class OpenVINOProcessor(BaseProcessor):
    # Uses Intel Neural Compute Stick
    pass

class HailoProcessor(BaseProcessor):
    # Uses Hailo-8 accelerator
    pass

class CPUProcessor(BaseProcessor):
    # Uses CPU-only processing
    pass
```

**Bottom line:** The project is NOT dependent on Coral. We have multiple viable paths forward.

---

## Decision Matrix

| Option | Performance | Cost | Availability | Ease of Integration | Privacy |
|--------|-------------|------|--------------|---------------------|---------|
| **Coral USB** | ⭐⭐⭐⭐⭐ | $110 | ⚠️ Low | ⭐⭐⭐⭐⭐ | ✅ Local |
| **CPU Only** | ⭐⭐ | $0 | ✅ Now | ⭐⭐⭐⭐⭐ | ✅ Local |
| **Intel NCS2** | ⭐⭐⭐⭐ | $80 | ✅ Good | ⭐⭐⭐ | ✅ Local |
| **Hailo-8** | ⭐⭐⭐⭐⭐⭐ | $85 | ✅ Good | ⭐⭐ | ✅ Local |
| **Cloud API** | ⭐⭐⭐⭐⭐ | $$$ | ✅ Always | ⭐⭐⭐⭐ | ❌ Cloud |

---

## Next Steps

1. **Continue development** with CPU-only processing (no waiting needed)
2. **Monitor Coral stock** at official retailers
3. **Research Hailo-8** as a potentially better long-term solution
4. **Keep Intel NCS2** as backup plan

The project can proceed regardless of hardware availability! 🚀
