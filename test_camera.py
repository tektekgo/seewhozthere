#!/usr/bin/env python3
"""
SeeWhozThere - Camera Connection Test Script

This script tests the RTSP connection to your Tapo C310 camera
and captures a test frame to verify everything is working.

Usage:
    python test_camera.py
"""

import cv2
import sys
from pathlib import Path
from configparser import ConfigParser

def load_config():
    """Load configuration from config.ini"""
    config = ConfigParser()
    config_path = Path(__file__).parent / 'config.ini'
    
    if not config_path.exists():
        print(f"❌ Error: config.ini not found at {config_path}")
        print("   Please make sure config.ini exists in the project root.")
        sys.exit(1)
    
    config.read(config_path)
    return config

def test_camera_connection(camera_name, rtsp_url):
    """Test connection to a camera and capture a frame"""
    print(f"\n{'='*60}")
    print(f"Testing camera: {camera_name}")
    print(f"RTSP URL: {rtsp_url[:30]}...{rtsp_url[-20:]}")  # Hide credentials in middle
    print(f"{'='*60}\n")
    
    # Try to open the video stream
    print("📹 Attempting to connect to camera...")
    cap = cv2.VideoCapture(rtsp_url)
    
    if not cap.isOpened():
        print("❌ Failed to connect to camera!")
        print("\nPossible issues:")
        print("  1. Check camera IP address is correct")
        print("  2. Verify RTSP username and password")
        print("  3. Ensure camera is powered on and connected to network")
        print("  4. Confirm RTSP is enabled in Tapo app")
        print("  5. Try pinging the camera: ping 192.168.9.130")
        return False
    
    print("✅ Successfully connected to camera!")
    
    # Try to read a frame
    print("📸 Attempting to capture a frame...")
    ret, frame = cap.read()
    
    if not ret or frame is None:
        print("❌ Failed to capture frame from camera!")
        cap.release()
        return False
    
    print("✅ Successfully captured frame!")
    
    # Get frame information
    height, width, channels = frame.shape
    print(f"\n📊 Frame Information:")
    print(f"   Resolution: {width}x{height}")
    print(f"   Channels: {channels}")
    print(f"   Size: {frame.nbytes / 1024:.2f} KB")
    
    # Save the test frame
    output_dir = Path(__file__).parent / 'test_output'
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / f'{camera_name}_test_frame.jpg'
    cv2.imwrite(str(output_path), frame)
    print(f"\n💾 Test frame saved to: {output_path}")
    
    # Test reading multiple frames to check stream stability
    print("\n🔄 Testing stream stability (reading 30 frames)...")
    success_count = 0
    for i in range(30):
        ret, frame = cap.read()
        if ret:
            success_count += 1
        
        # Print progress every 10 frames
        if (i + 1) % 10 == 0:
            print(f"   Frames {i-9}-{i+1}: {success_count}/{10} successful")
            success_count = 0
    
    cap.release()
    
    print("\n✅ Camera test completed successfully!")
    print(f"   Camera '{camera_name}' is working properly.")
    return True

def main():
    """Main test function"""
    print("\n" + "="*60)
    print("SeeWhozThere - Camera Connection Test")
    print("="*60)
    
    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        sys.exit(1)
    
    # Check if cameras are configured
    if 'CAMERAS' not in config:
        print("❌ Error: No [CAMERAS] section found in config.ini")
        sys.exit(1)
    
    cameras = dict(config['CAMERAS'])
    
    if not cameras:
        print("❌ Error: No cameras configured in config.ini")
        print("   Please add at least one camera in the [CAMERAS] section.")
        sys.exit(1)
    
    print(f"\n📹 Found {len(cameras)} camera(s) configured:")
    for name in cameras.keys():
        print(f"   - {name}")
    
    # Test each camera
    results = {}
    for camera_name, rtsp_url in cameras.items():
        # Skip commented lines
        if camera_name.startswith('#'):
            continue
        
        try:
            results[camera_name] = test_camera_connection(camera_name, rtsp_url)
        except Exception as e:
            print(f"❌ Error testing camera '{camera_name}': {e}")
            results[camera_name] = False
    
    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for camera_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {camera_name}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\nTotal: {passed}/{total} cameras working")
    
    if passed == total:
        print("\n🎉 All cameras are working! You're ready to run SeeWhozThere!")
        print("\nNext steps:")
        print("  1. Start the web server: python -m app.main")
        print("  2. Open http://localhost:7222 in your browser")
        print("  3. Wait for the AI HAT+ to arrive for face detection")
    else:
        print("\n⚠️  Some cameras failed. Please check the errors above.")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
