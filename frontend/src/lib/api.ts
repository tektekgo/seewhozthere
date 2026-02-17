// SeeWhozThere API Client
// This connects the React frontend to the FastAPI backend

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export interface Stats {
  totalVisitors: number;
  todayActivity: number;
  activeCameras: number;
  unknownToday: number;
}

export interface HourlyActivity {
  hour: string;
  known: number;
  unknown: number;
}

export interface KnownVsUnknown {
  known: number;
  unknown: number;
}

export interface WeeklyTrend {
  day: string;
  visitors: number;
}

export interface CameraActivity {
  camera: string;
  detections: number;
}

export interface Visitor {
  id: number;
  name: string;
  count: number;
  lastSeen: string;
  thumbnail?: string;
  isKnown: boolean;
}

export interface HeatmapCell {
  hour: number;
  day: number;
  value: number;
}

export interface SystemStatus {
  running: boolean;
  hailo_available: boolean;
  active_cameras: number;
  camera_names: string[];
  known_people: number;
  stats?: {
    total_detections: number;
    total_recognitions: number;
    uptime_seconds: number;
  };
}

class API {
  private async fetch<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`);
    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }
    return response.json();
  }

  async getStats(): Promise<Stats> {
    const data = await this.fetch<any>('/api/analytics/stats');
    return data;
  }

  async getHourlyActivity(): Promise<HourlyActivity[]> {
    const data = await this.fetch<any>('/api/analytics/hourly');
    return data.hourly || [];
  }

  async getKnownVsUnknown(): Promise<KnownVsUnknown> {
    const data = await this.fetch<any>('/api/analytics/known-unknown');
    return data;
  }

  async getWeeklyTrend(): Promise<WeeklyTrend[]> {
    const data = await this.fetch<any>('/api/analytics/weekly');
    return data.weekly || [];
  }

  async getCameraActivity(): Promise<CameraActivity[]> {
    const data = await this.fetch<any>('/api/analytics/cameras');
    return data.cameras || [];
  }

  async getTopVisitors(): Promise<Visitor[]> {
    const data = await this.fetch<any>('/api/analytics/top-visitors');
    return data.visitors || [];
  }

  async getTodayVisitors(): Promise<Visitor[]> {
    const data = await this.fetch<any>('/api/sightings?filter=all');
    const sightings = data.sightings || [];
    
    // Transform sightings to visitors
    const visitorMap = new Map<string, Visitor>();
    
    sightings.forEach((sighting: any) => {
      const name = sighting.visitor_name || 'Unknown';
      const key = `${name}_${sighting.visitor_id || 'unknown'}`;
      
      if (visitorMap.has(key)) {
        const visitor = visitorMap.get(key)!;
        visitor.count++;
        if (new Date(sighting.timestamp) > new Date(visitor.lastSeen)) {
          visitor.lastSeen = sighting.timestamp;
        }
      } else {
        visitorMap.set(key, {
          id: sighting.visitor_id || 0,
          name: name,
          count: 1,
          lastSeen: sighting.timestamp,
          thumbnail: sighting.thumbnail_path ? `${API_BASE_URL}/${sighting.thumbnail_path}` : undefined,
          isKnown: !!sighting.visitor_id
        });
      }
    });
    
    return Array.from(visitorMap.values());
  }

  async getHeatmapData(): Promise<HeatmapCell[]> {
    const data = await this.fetch<any>('/api/analytics/heatmap');
    return data.heatmap || [];
  }

  async getSystemStatus(): Promise<SystemStatus> {
    return this.fetch<SystemStatus>('/api/status');
  }

  async addPerson(name: string, photo?: File): Promise<any> {
    const formData = new FormData();
    formData.append('name', name);
    if (photo) {
      formData.append('photo', photo);
    }

    const response = await fetch(`${API_BASE_URL}/api/visitors`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Failed to add person: ${response.statusText}`);
    }

    return response.json();
  }

  async deletePerson(visitorId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/visitors/${visitorId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Failed to delete person: ${response.statusText}`);
    }
  }

  async deleteSighting(sightingId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/sightings/${sightingId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Failed to delete sighting: ${response.statusText}`);
    }
  }

  async getAllPeople(): Promise<any[]> {
    const data = await this.fetch<any>('/api/visitors');
    return data.visitors || [];
  }
}

export const api = new API();
