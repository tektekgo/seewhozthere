"""
SeeWhozThere Database Module

This module handles all database operations for storing and retrieving visitor data.
It uses SQLite for local, privacy-first storage.

Database Schema:
- visitors: Stores known people with their assigned names
- sightings: Stores each detection event with timestamp and metadata
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import pytz

from app.config import TIMEZONE, DATABASE_PATH


class Database:
    """Manages all database operations for SeeWhozThere"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        """
        Initialize the database connection and create tables if they don't exist.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_db()
    
    def _ensure_db_directory(self):
        """Ensure the directory for the database file exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row
        return conn
    
    def _parse_datetime_fields(self, row_dict: Dict) -> Dict:
        for key in ['first_seen', 'last_seen', 'timestamp', 'created_at', 'updated_at']:
            if key in row_dict and row_dict[key] and isinstance(row_dict[key], str):
                try:
                    row_dict[key] = datetime.fromisoformat(row_dict[key].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass
        return row_dict
    
    def _init_db(self):
        """Create the database tables if they don't exist"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create visitors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                face_encoding BLOB,
                thumbnail_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create sightings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sightings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_id INTEGER,
                camera_name TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confidence REAL,
                snapshot_path TEXT,
                FOREIGN KEY (visitor_id) REFERENCES visitors(id) ON DELETE CASCADE
            )
        """)
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sightings_timestamp 
            ON sightings(timestamp DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sightings_visitor 
            ON sightings(visitor_id, timestamp DESC)
        """)
        
        conn.commit()
        conn.close()
    
    def add_visitor(self, name: str, face_encoding: Optional[bytes] = None, 
                   thumbnail_path: Optional[str] = None) -> int:
        """
        Add a new known visitor to the database.
        
        Args:
            name: The person's name
            face_encoding: Binary representation of the face encoding (optional)
            thumbnail_path: Path to the person's thumbnail image (optional)
            
        Returns:
            The ID of the newly created visitor
            
        Raises:
            sqlite3.IntegrityError: If a visitor with this name already exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO visitors (name, face_encoding, thumbnail_path)
            VALUES (?, ?, ?)
        """, (name, face_encoding, thumbnail_path))
        
        visitor_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return visitor_id
    
    def get_visitor_by_name(self, name: str) -> Optional[Dict]:
        """
        Retrieve a visitor by their name.
        
        Args:
            name: The person's name
            
        Returns:
            Dictionary with visitor data, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, face_encoding, thumbnail_path, created_at, updated_at
            FROM visitors
            WHERE name = ?
        """, (name,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_visitor_by_id(self, visitor_id: int) -> Optional[Dict]:
        """
        Retrieve a visitor by their ID.
        
        Args:
            visitor_id: The visitor's database ID
            
        Returns:
            Dictionary with visitor data, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, face_encoding, thumbnail_path, created_at, updated_at
            FROM visitors
            WHERE id = ?
        """, (visitor_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_visitor(self, visitor_id: int) -> Optional[Dict]:
        """Alias for get_visitor_by_id for compatibility"""
        return self.get_visitor_by_id(visitor_id)
    
    def get_all_visitors(self) -> List[Dict]:
        """
        Get all known visitors.
        
        Returns:
            List of dictionaries with visitor data
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, face_encoding, thumbnail_path, created_at, updated_at
            FROM visitors
            ORDER BY name
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def update_visitor(self, visitor_id: int, name: Optional[str] = None,
                      face_encoding: Optional[bytes] = None,
                      thumbnail_path: Optional[str] = None) -> bool:
        """
        Update a visitor's information.
        
        Args:
            visitor_id: The visitor's database ID
            name: New name (optional)
            face_encoding: New face encoding (optional)
            thumbnail_path: New thumbnail path (optional)
            
        Returns:
            True if the update was successful, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if face_encoding is not None:
            updates.append("face_encoding = ?")
            params.append(face_encoding)
        if thumbnail_path is not None:
            updates.append("thumbnail_path = ?")
            params.append(thumbnail_path)
        
        if not updates:
            conn.close()
            return False
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(visitor_id)
        
        query = f"UPDATE visitors SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def delete_visitor(self, visitor_id: int) -> bool:
        """
        Delete a visitor and all their sightings.
        
        Args:
            visitor_id: The visitor's database ID
            
        Returns:
            True if the deletion was successful, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM visitors WHERE id = ?", (visitor_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def add_sighting(self, visitor_id: Optional[int], camera_name: str,
                    timestamp: Optional[datetime] = None, confidence: Optional[float] = None,
                    snapshot_path: Optional[str] = None) -> int:
        """
        Record a new sighting event.
        
        Args:
            visitor_id: The ID of the recognized visitor (None for unknown)
            camera_name: Name of the camera that captured the sighting
            timestamp: When the sighting occurred (defaults to now)
            confidence: Recognition confidence score (0.0 to 1.0)
            snapshot_path: Path to the snapshot image
            
        Returns:
            The ID of the newly created sighting
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if timestamp is None:
            timestamp = datetime.now(pytz.timezone(TIMEZONE))
        
        cursor.execute("""
            INSERT INTO sightings (visitor_id, camera_name, timestamp, confidence, snapshot_path)
            VALUES (?, ?, ?, ?, ?)
        """, (visitor_id, camera_name, timestamp, confidence, snapshot_path))
        
        sighting_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return sighting_id
    
    def get_sightings_by_date(self, date: datetime) -> List[Dict]:
        """
        Get all sightings for a specific date.
        
        Args:
            date: The date to query (time component is ignored)
            
        Returns:
            List of dictionaries with sighting data
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get start and end of the day
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        cursor.execute("""
            SELECT s.id, s.visitor_id, s.camera_name, s.timestamp, s.confidence, s.snapshot_path,
                   v.name as visitor_name, v.thumbnail_path
            FROM sightings s
            LEFT JOIN visitors v ON s.visitor_id = v.id
            WHERE s.timestamp >= ? AND s.timestamp < ?
            ORDER BY s.timestamp DESC
        """, (start_of_day, end_of_day))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_today_summary(self) -> List[Dict]:
        """
        Get a summary of today's visitors with their sighting counts.
        
        Returns:
            List of dictionaries with visitor info and sighting statistics
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get today's date range
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        cursor.execute("""
            SELECT 
                COALESCE(v.id, 0) as visitor_id,
                COALESCE(v.name, 'Unknown') as name,
                v.thumbnail_path,
                COUNT(s.id) as sighting_count,
                MIN(s.timestamp) as first_seen,
                MAX(s.timestamp) as last_seen,
                s.snapshot_path as latest_snapshot
            FROM sightings s
            LEFT JOIN visitors v ON s.visitor_id = v.id
            WHERE s.timestamp >= ?
            GROUP BY COALESCE(v.id, s.id)
            ORDER BY last_seen DESC
        """, (start_of_day,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._parse_datetime_fields(dict(row)) for row in rows]
    
    def get_visitor_history(self, visitor_id: int, days: int = 7) -> List[Dict]:
        """
        Get the sighting history for a specific visitor.
        
        Args:
            visitor_id: The visitor's database ID
            days: Number of days to look back (default: 7)
            
        Returns:
            List of dictionaries with sighting data
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        start_date = now - timedelta(days=days)
        
        cursor.execute("""
            SELECT id, visitor_id, camera_name, timestamp, confidence, snapshot_path
            FROM sightings
            WHERE visitor_id = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        """, (visitor_id, start_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._parse_datetime_fields(dict(row)) for row in rows]
    
    def get_unknown_sightings(self, limit: int = 50) -> List[Dict]:
        """
        Get recent sightings of unknown visitors.
        
        Args:
            limit: Maximum number of sightings to return
            
        Returns:
            List of dictionaries with sighting data
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, camera_name, timestamp, confidence, snapshot_path
            FROM sightings
            WHERE visitor_id IS NULL
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._parse_datetime_fields(dict(row)) for row in rows]
    
    def identify_sighting(self, sighting_id: int, visitor_id: int) -> bool:
        """
        Associate an unknown sighting with a known visitor.
        
        Args:
            sighting_id: The sighting's database ID
            visitor_id: The visitor's database ID
            
        Returns:
            True if the update was successful, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE sightings
            SET visitor_id = ?
            WHERE id = ?
        """, (visitor_id, sighting_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success

    def delete_sighting(self, sighting_id: int) -> bool:
        """
        Permanently delete a sighting record and its snapshot file.

        Args:
            sighting_id: The sighting's database ID

        Returns:
            True if the deletion was successful, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        # Fetch snapshot path before deleting so we can remove the file
        cursor.execute("SELECT snapshot_path FROM sightings WHERE id = ?", (sighting_id,))
        row = cursor.fetchone()
        snapshot_path = dict(row)["snapshot_path"] if row else None
        cursor.execute("DELETE FROM sightings WHERE id = ?", (sighting_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        # Remove the snapshot file if it exists
        if success and snapshot_path:
            try:
                import os as _os
                if _os.path.exists(snapshot_path):
                    _os.remove(snapshot_path)
            except Exception:
                pass
        return success

    def unlink_sighting(self, sighting_id: int) -> bool:
        """
        Remove the visitor association from a sighting, marking it as Unknown.
        The sighting record and snapshot are kept; only visitor_id is cleared.

        Args:
            sighting_id: The sighting's database ID

        Returns:
            True if the update was successful, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sightings SET visitor_id = NULL WHERE id = ?",
            (sighting_id,),
        )
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_statistics(self) -> Dict:
        """
        Get overall statistics about the database.
        
        Returns:
            Dictionary with various statistics
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Total visitors
        cursor.execute("SELECT COUNT(*) as count FROM visitors")
        total_visitors = cursor.fetchone()["count"]
        
        # Total sightings
        cursor.execute("SELECT COUNT(*) as count FROM sightings")
        total_sightings = cursor.fetchone()["count"]
        
        # Unknown sightings
        cursor.execute("SELECT COUNT(*) as count FROM sightings WHERE visitor_id IS NULL")
        unknown_sightings = cursor.fetchone()["count"]
        
        # Today's sightings
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        cursor.execute("SELECT COUNT(*) as count FROM sightings WHERE timestamp >= ?", (start_of_day,))
        today_sightings = cursor.fetchone()["count"]
        
        conn.close()
        
        return {
            "total_visitors": total_visitors,
            "total_sightings": total_sightings,
            "unknown_sightings": unknown_sightings,
            "today_sightings": today_sightings
        }


# Create a singleton instance
_db_instance = None

def get_db() -> Database:
    """
    Get the singleton database instance.
    
    Returns:
        The Database instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
