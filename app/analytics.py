"""
Analytics module for SeeWhozThere
Provides data aggregation and statistics for the dashboard
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


class Analytics:
    """Analytics engine for dashboard data"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(PROJECT_ROOT / "data" / "seewhozthere.db")
        self.db_path = db_path
    
    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_stats(self) -> Dict[str, int]:
        """Get overall statistics"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Total unique visitors (known people)
        cursor.execute("SELECT COUNT(*) as count FROM visitors")
        total_visitors = cursor.fetchone()['count']
        
        # Today's activity (all sightings today)
        today = datetime.now().date()
        cursor.execute("""
            SELECT COUNT(*) as count FROM sightings 
            WHERE DATE(timestamp) = ?
        """, (str(today),))
        today_activity = cursor.fetchone()['count']
        
        # Active cameras (from config or sightings)
        cursor.execute("""
            SELECT COUNT(DISTINCT camera_name) as count FROM sightings
        """)
        active_cameras = cursor.fetchone()['count']
        
        # Unknown visitors today
        cursor.execute("""
            SELECT COUNT(*) as count FROM sightings 
            WHERE DATE(timestamp) = ? AND visitor_id IS NULL
        """, (str(today),))
        unknown_today = cursor.fetchone()['count']
        
        conn.close()
        
        return {
            "totalVisitors": total_visitors,
            "todayActivity": today_activity,
            "activeCameras": active_cameras,
            "unknownToday": unknown_today
        }
    
    def get_hourly_activity(self) -> List[Dict[str, Any]]:
        """Get hourly activity for today"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        today = datetime.now().date()
        
        # Initialize all hours
        hourly_data = []
        for hour in range(24):
            hourly_data.append({
                "hour": f"{hour:02d}:00",
                "known": 0,
                "unknown": 0
            })
        
        # Get known visitors by hour
        cursor.execute("""
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
            FROM sightings
            WHERE DATE(timestamp) = ? AND visitor_id IS NOT NULL
            GROUP BY hour
        """, (str(today),))
        
        for row in cursor.fetchall():
            hour_idx = int(row['hour'])
            hourly_data[hour_idx]['known'] = row['count']
        
        # Get unknown visitors by hour
        cursor.execute("""
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
            FROM sightings
            WHERE DATE(timestamp) = ? AND visitor_id IS NULL
            GROUP BY hour
        """, (str(today),))
        
        for row in cursor.fetchall():
            hour_idx = int(row['hour'])
            hourly_data[hour_idx]['unknown'] = row['count']
        
        conn.close()
        return hourly_data
    
    def get_known_vs_unknown(self) -> Dict[str, int]:
        """Get known vs unknown count for today"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        today = datetime.now().date()
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM sightings 
            WHERE DATE(timestamp) = ? AND visitor_id IS NOT NULL
        """, (str(today),))
        known = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM sightings 
            WHERE DATE(timestamp) = ? AND visitor_id IS NULL
        """, (str(today),))
        unknown = cursor.fetchone()['count']
        
        conn.close()
        
        return {
            "known": known,
            "unknown": unknown
        }
    
    def get_weekly_trend(self) -> List[Dict[str, Any]]:
        """Get visitor trend for the past 7 days"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get data for last 7 days
        weekly_data = []
        for i in range(6, -1, -1):
            date = datetime.now().date() - timedelta(days=i)
            day_name = date.strftime('%a')  # Mon, Tue, etc.
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM sightings 
                WHERE DATE(timestamp) = ?
            """, (str(date),))
            
            count = cursor.fetchone()['count']
            
            weekly_data.append({
                "day": day_name,
                "visitors": count
            })
        
        conn.close()
        return weekly_data
    
    def get_camera_activity(self) -> List[Dict[str, Any]]:
        """Get activity breakdown by camera"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        today = datetime.now().date()
        
        cursor.execute("""
            SELECT camera_name, COUNT(*) as count
            FROM sightings
            WHERE DATE(timestamp) = ?
            GROUP BY camera_name
            ORDER BY count DESC
        """, (str(today),))
        
        camera_data = []
        for row in cursor.fetchall():
            camera_data.append({
                "camera": row['camera_name'] or 'Unknown',
                "detections": row['count']
            })
        
        conn.close()
        return camera_data
    
    def get_top_visitors(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top visitors by sighting count"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        today = datetime.now().date()
        
        cursor.execute("""
            SELECT 
                v.id,
                v.name,
                COUNT(s.id) as count,
                MAX(s.timestamp) as last_seen,
                v.thumbnail_path
            FROM visitors v
            LEFT JOIN sightings s ON v.id = s.visitor_id
            WHERE DATE(s.timestamp) = ?
            GROUP BY v.id
            ORDER BY count DESC
            LIMIT ?
        """, (str(today), limit))
        
        visitors = []
        for row in cursor.fetchall():
            visitors.append({
                "id": row['id'],
                "name": row['name'],
                "count": row['count'],
                "lastSeen": row['last_seen'],
                "thumbnail": row['thumbnail_path'],
                "isKnown": True
            })
        
        conn.close()
        return visitors
    
    def get_heatmap_data(self) -> List[Dict[str, Any]]:
        """Get heatmap data (hour x day of week)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get data for last 7 days
        start_date = datetime.now().date() - timedelta(days=6)
        
        cursor.execute("""
            SELECT 
                strftime('%w', timestamp) as day_of_week,
                strftime('%H', timestamp) as hour,
                COUNT(*) as count
            FROM sightings
            WHERE DATE(timestamp) >= ?
            GROUP BY day_of_week, hour
        """, (str(start_date),))
        
        heatmap = []
        for row in cursor.fetchall():
            heatmap.append({
                "day": int(row['day_of_week']),  # 0 = Sunday
                "hour": int(row['hour']),
                "value": row['count']
            })
        
        conn.close()
        return heatmap


# Singleton instance
_analytics = None

def get_analytics():
    """Get or create analytics instance"""
    global _analytics
    if _analytics is None:
        _analytics = Analytics()
    return _analytics
