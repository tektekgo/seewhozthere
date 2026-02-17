// Mock data for the SeeWhozThere dashboard

export interface Visitor {
  id: string;
  name: string;
  known: boolean;
  thumbnail: string;
  firstSeen: string;
  lastSeen: string;
  sightings: number;
}

export interface HourlyActivity {
  hour: string;
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

export interface HeatmapCell {
  day: string;
  hour: number;
  value: number;
}

export const mockStats = {
  totalVisitors: 1247,
  todayActivity: 38,
  activeCameras: 3,
  unknownToday: 7,
};

export const mockHourlyData: HourlyActivity[] = Array.from({ length: 24 }, (_, i) => {
  const hour = i.toString().padStart(2, "0") + ":00";
  const base = i >= 7 && i <= 22 ? Math.floor(Math.random() * 8) + 1 : Math.floor(Math.random() * 2);
  const known = Math.floor(base * 0.7);
  return { hour, known, unknown: base - known };
});

export const mockKnownVsUnknown = {
  known: 31,
  unknown: 7,
};

export const mockWeeklyTrend: WeeklyTrend[] = [
  { day: "Mon", visitors: 32 },
  { day: "Tue", visitors: 28 },
  { day: "Wed", visitors: 45 },
  { day: "Thu", visitors: 39 },
  { day: "Fri", visitors: 52 },
  { day: "Sat", visitors: 18 },
  { day: "Sun", visitors: 12 },
];

export const mockCameraActivity: CameraActivity[] = [
  { camera: "Front Door", detections: 124 },
  { camera: "Backyard", detections: 67 },
  { camera: "Garage", detections: 43 },
  { camera: "Side Gate", detections: 21 },
].sort((a, b) => b.detections - a.detections);

export const mockTopVisitors: Visitor[] = [
  { id: "1", name: "Alice Johnson", known: true, thumbnail: "", firstSeen: "08:12", lastSeen: "17:45", sightings: 42 },
  { id: "2", name: "Bob Smith", known: true, thumbnail: "", firstSeen: "09:30", lastSeen: "16:20", sightings: 38 },
  { id: "3", name: "Carol Davis", known: true, thumbnail: "", firstSeen: "07:55", lastSeen: "18:10", sightings: 31 },
  { id: "4", name: "Dave Wilson", known: true, thumbnail: "", firstSeen: "10:00", lastSeen: "15:30", sightings: 27 },
  { id: "5", name: "Eve Martinez", known: true, thumbnail: "", firstSeen: "08:45", lastSeen: "17:00", sightings: 22 },
];

export const mockTodayVisitors: Visitor[] = [
  { id: "1", name: "Alice Johnson", known: true, thumbnail: "", firstSeen: "08:12", lastSeen: "14:30", sightings: 5 },
  { id: "2", name: "Bob Smith", known: true, thumbnail: "", firstSeen: "09:30", lastSeen: "12:15", sightings: 3 },
  { id: "6", name: "Unknown #1", known: false, thumbnail: "", firstSeen: "10:22", lastSeen: "10:22", sightings: 1 },
  { id: "3", name: "Carol Davis", known: true, thumbnail: "", firstSeen: "07:55", lastSeen: "15:40", sightings: 7 },
  { id: "7", name: "Unknown #2", known: false, thumbnail: "", firstSeen: "11:45", lastSeen: "11:50", sightings: 2 },
  { id: "4", name: "Dave Wilson", known: true, thumbnail: "", firstSeen: "10:00", lastSeen: "13:20", sightings: 4 },
  { id: "8", name: "Unknown #3", known: false, thumbnail: "", firstSeen: "13:10", lastSeen: "13:10", sightings: 1 },
  { id: "5", name: "Eve Martinez", known: true, thumbnail: "", firstSeen: "08:45", lastSeen: "16:00", sightings: 6 },
];

export const mockHeatmapData: HeatmapCell[] = (() => {
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const cells: HeatmapCell[] = [];
  for (const day of days) {
    for (let hour = 0; hour < 24; hour++) {
      const isWeekend = day === "Sat" || day === "Sun";
      const isDaytime = hour >= 7 && hour <= 21;
      const peak = hour >= 8 && hour <= 10 || hour >= 17 && hour <= 19;
      let value = 0;
      if (isDaytime) value = Math.floor(Math.random() * 5) + 1;
      if (peak && !isWeekend) value = Math.floor(Math.random() * 5) + 5;
      if (!isDaytime) value = Math.floor(Math.random() * 2);
      cells.push({ day, hour, value });
    }
  }
  return cells;
})();
