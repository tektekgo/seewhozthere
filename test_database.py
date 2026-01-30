"""
Test script for the database module.
This script creates some sample data to verify the database is working correctly.
"""

import os
import sys
from datetime import datetime, timedelta
import pytz

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.config import TIMEZONE

def test_database():
    """Run a series of tests on the database module"""
    
    print("=" * 60)
    print("SeeWhozThere Database Module Test")
    print("=" * 60)
    
    db = get_db()
    tz = pytz.timezone(TIMEZONE)
    
    # Test 1: Add some known visitors
    print("\n[Test 1] Adding known visitors...")
    try:
        bob_id = db.add_visitor("Bob", thumbnail_path="/static/mock_faces/ravi.jpg")
        print(f"✓ Added 'Bob' with ID: {bob_id}")
        
        alice_id = db.add_visitor("Alice", thumbnail_path="/static/mock_faces/sanju.jpg")
        print(f"✓ Added 'Alice' with ID: {alice_id}")
        
        charlie_id = db.add_visitor("Charlie")
        print(f"✓ Added 'Charlie' with ID: {charlie_id}")
    except Exception as e:
        print(f"✗ Error adding visitors: {e}")
        return False
    
    # Test 2: Retrieve visitors
    print("\n[Test 2] Retrieving visitors...")
    try:
        bob = db.get_visitor_by_name("Bob")
        print(f"✓ Retrieved Bob: {bob['name']}")
        
        all_visitors = db.get_all_visitors()
        print(f"✓ Total visitors in database: {len(all_visitors)}")
        for visitor in all_visitors:
            print(f"  - {visitor['name']} (ID: {visitor['id']})")
    except Exception as e:
        print(f"✗ Error retrieving visitors: {e}")
        return False
    
    # Test 3: Add sightings
    print("\n[Test 3] Adding sightings...")
    try:
        now = datetime.now(tz)
        
        # Bob's sightings
        db.add_sighting(bob_id, "Front Door", 
                       timestamp=now - timedelta(hours=5),
                       confidence=0.95,
                       snapshot_path="/static/mock_faces/ravi.jpg")
        db.add_sighting(bob_id, "Front Door",
                       timestamp=now - timedelta(hours=2),
                       confidence=0.92,
                       snapshot_path="/static/mock_faces/ravi.jpg")
        db.add_sighting(bob_id, "Driveway",
                       timestamp=now - timedelta(minutes=30),
                       confidence=0.89,
                       snapshot_path="/static/mock_faces/ravi.jpg")
        print(f"✓ Added 3 sightings for Bob")
        
        # Alice's sightings
        db.add_sighting(alice_id, "Front Door",
                       timestamp=now - timedelta(hours=3),
                       confidence=0.97,
                       snapshot_path="/static/mock_faces/sanju.jpg")
        print(f"✓ Added 1 sighting for Alice")
        
        # Unknown visitor
        db.add_sighting(None, "Backyard",
                       timestamp=now - timedelta(hours=1),
                       confidence=0.0,
                       snapshot_path="/static/mock_faces/unknown_1.jpg")
        print(f"✓ Added 1 unknown sighting")
    except Exception as e:
        print(f"✗ Error adding sightings: {e}")
        return False
    
    # Test 4: Get today's summary
    print("\n[Test 4] Getting today's summary...")
    try:
        summary = db.get_today_summary()
        print(f"✓ Today's summary:")
        for visitor in summary:
            print(f"  - {visitor['name']}: {visitor['sighting_count']} sighting(s)")
            print(f"    First seen: {visitor['first_seen']}")
            print(f"    Last seen: {visitor['last_seen']}")
    except Exception as e:
        print(f"✗ Error getting summary: {e}")
        return False
    
    # Test 5: Get unknown sightings
    print("\n[Test 5] Getting unknown sightings...")
    try:
        unknown = db.get_unknown_sightings()
        print(f"✓ Found {len(unknown)} unknown sighting(s)")
        for sighting in unknown:
            print(f"  - Camera: {sighting['camera_name']}, Time: {sighting['timestamp']}")
    except Exception as e:
        print(f"✗ Error getting unknown sightings: {e}")
        return False
    
    # Test 6: Get statistics
    print("\n[Test 6] Getting database statistics...")
    try:
        stats = db.get_statistics()
        print(f"✓ Database statistics:")
        print(f"  - Total visitors: {stats['total_visitors']}")
        print(f"  - Total sightings: {stats['total_sightings']}")
        print(f"  - Unknown sightings: {stats['unknown_sightings']}")
        print(f"  - Today's sightings: {stats['today_sightings']}")
    except Exception as e:
        print(f"✗ Error getting statistics: {e}")
        return False
    
    # Test 7: Identify an unknown sighting
    print("\n[Test 7] Identifying an unknown sighting...")
    try:
        unknown = db.get_unknown_sightings(limit=1)
        if unknown:
            sighting_id = unknown[0]['id']
            success = db.identify_sighting(sighting_id, charlie_id)
            if success:
                print(f"✓ Successfully identified sighting {sighting_id} as Charlie")
            else:
                print(f"✗ Failed to identify sighting")
        else:
            print("  (No unknown sightings to identify)")
    except Exception as e:
        print(f"✗ Error identifying sighting: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("All tests completed successfully! ✓")
    print("=" * 60)
    print(f"\nDatabase file location: {db.db_path}")
    print("You can now integrate this database with the web dashboard.")
    
    return True

if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)
