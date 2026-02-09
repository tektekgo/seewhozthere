#!/usr/bin/env python3
"""
Test script for Hailo AI Processor

This script tests the Hailo processor with your configured cameras.
It will run for 30 seconds and detect faces in the camera streams.

Usage:
    python3 test_hailo.py
"""

import sys
import time
from app.hailo_processor import get_processor
from app.database import get_db


def main():
    print("=" * 60)
    print("SeeWhozThere - Hailo AI Processor Test")
    print("=" * 60)
    
    # Initialize processor
    processor = get_processor()
    
    # Check status
    status = processor.get_status()
    print(f"\n📊 Processor Status:")
    print(f"   Hailo Available: {'✅ Yes' if status['hailo_available'] else '❌ No (using OpenCV fallback)'}")
    
    if not status['hailo_available']:
        print("\n⚠️  Hailo device not detected. Face detection will use OpenCV (slower).")
        print("   Make sure:")
        print("   1. AI HAT+ is properly installed")
        print("   2. Hailo drivers are installed (hailo-all package)")
        print("   3. /dev/hailo0 device exists")
        print("   4. You've rebooted after installing drivers")
    
    # Start processing
    print("\n🚀 Starting face detection...")
    print("   Processing will run for 30 seconds")
    print("   Press Ctrl+C to stop early\n")
    
    processor.start()
    
    try:
        # Run for 30 seconds
        for i in range(30):
            time.sleep(1)
            if (i + 1) % 10 == 0:
                print(f"   [{i + 1}/30] Still processing...")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    
    finally:
        # Stop processing
        print("\n🛑 Stopping processor...")
        processor.stop()
    
    # Show results
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)
    
    db = get_db()
    stats = db.get_statistics()
    
    print(f"\n📊 Database Statistics:")
    print(f"   Total Sightings: {stats['total_sightings']}")
    print(f"   Today's Sightings: {stats['today_sightings']}")
    print(f"   Unknown Sightings: {stats['unknown_sightings']}")
    
    # Show recent sightings
    print(f"\n📸 Recent Sightings:")
    summary = db.get_today_summary()
    
    if summary:
        for visitor in summary:
            name = visitor['name'] if visitor['name'] else 'Unknown'
            count = visitor['sighting_count']
            print(f"   - {name}: {count} sighting(s)")
    else:
        print("   No sightings detected during test")
    
    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("\n💡 Next steps:")
    print("   1. Check snapshots in: data/snapshots/")
    print("   2. View dashboard: http://your_pi_ip:7222")
    print("   3. Run: python3 -m app.main (to start web server)")
    print("=" * 60)


if __name__ == "__main__":
    main()
