import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { StatsCards } from "@/components/dashboard/StatsCards";
import { HourlyActivityChart } from "@/components/dashboard/HourlyActivityChart";
import { KnownUnknownChart } from "@/components/dashboard/KnownUnknownChart";
import { WeeklyTrendChart } from "@/components/dashboard/WeeklyTrendChart";
import { CameraActivityChart } from "@/components/dashboard/CameraActivityChart";
import { TopVisitors } from "@/components/dashboard/TopVisitors";
import { PeakHoursHeatmap } from "@/components/dashboard/PeakHoursHeatmap";
import { VisitorGrid } from "@/components/dashboard/VisitorGrid";
import { api } from "@/lib/api";
import {
  mockHourlyData,
  mockKnownVsUnknown,
  mockWeeklyTrend,
  mockCameraActivity,
  mockHeatmapData,
  type HourlyActivity,
  type WeeklyTrend,
  type CameraActivity,
  type HeatmapCell,
} from "@/lib/mock-data";

// Shape returned by /api/today-visitors
interface TodaySighting {
  id: number;
  visitor_id: number | null;
  visitor_name: string | null;
  camera_name: string;
  snapshot_path: string | null;
  detected_at: string;
}

// Shape returned by /api/stats
interface Stats {
  totalDetections: number;
  todayDetections: number;
  activeCameras: number;
  unknownToday: number;
}

// Shape returned by /api/top-visitors
interface TopVisitorItem {
  id: number;
  name: string;
  sighting_count: number;
  thumbnail_path: string | null;
}

// Convert a snapshot path to a URL the browser can fetch
function snapshotUrl(path: string | null): string {
  if (!path) return "";
  if (path.startsWith("data/")) return `/${path}`;
  if (path.startsWith("/")) return path;
  return `/data/snapshots/${path.split("/").pop()}`;
}

// Convert a datetime string to a short HH:MM display
function toTime(dt: string): string {
  try {
    return new Date(dt).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  } catch {
    return dt;
  }
}

const emptyStats: Stats = { totalDetections: 0, todayDetections: 0, activeCameras: 0, unknownToday: 0 };

const Index = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<Stats>(emptyStats);
  const [hourly, setHourly] = useState<HourlyActivity[]>(mockHourlyData);
  const [knownUnknown, setKnownUnknown] = useState(mockKnownVsUnknown);
  const [weekly, setWeekly] = useState<WeeklyTrend[]>(mockWeeklyTrend);
  const [cameras, setCameras] = useState<CameraActivity[]>(mockCameraActivity);
  const [topVisitors, setTopVisitors] = useState<TopVisitorItem[]>([]);
  const [todaySightings, setTodaySightings] = useState<TodaySighting[]>([]);
  const [heatmap, setHeatmap] = useState<HeatmapCell[]>(mockHeatmapData);

  useEffect(() => {
    // Stats
    api.getStats().then((data: Stats) => setStats(data)).catch(() => {});

    // Hourly
    api.getHourlyActivity().then((data) => {
      if (Array.isArray(data)) setHourly(data);
    }).catch(() => {});

    // Known vs Unknown
    api.getKnownVsUnknown().then((data) => {
      if (data && typeof data.known === "number") setKnownUnknown(data);
    }).catch(() => {});

    // Weekly
    api.getWeeklyTrend().then((data) => {
      const arr = Array.isArray(data) ? data : (data as { weekly?: WeeklyTrend[] }).weekly;
      if (Array.isArray(arr)) setWeekly(arr);
    }).catch(() => {});

    // Cameras
    api.getCameraActivity().then((data) => {
      const arr = Array.isArray(data) ? data : (data as { cameras?: CameraActivity[] }).cameras;
      if (Array.isArray(arr)) setCameras(arr);
    }).catch(() => {});

    // Top visitors
    api.getTopVisitors().then((data: { visitors?: TopVisitorItem[] }) => {
      if (Array.isArray(data?.visitors)) setTopVisitors(data.visitors);
    }).catch(() => {});

    // Today's sightings (real detections)
    api.getTodayVisitors().then((data: { sightings?: TodaySighting[] }) => {
      if (Array.isArray(data?.sightings)) setTodaySightings(data.sightings);
    }).catch(() => {});

    // Heatmap
    api.getHeatmapData().then((data) => {
      const arr = Array.isArray(data) ? data : (data as { heatmap?: HeatmapCell[] }).heatmap;
      if (Array.isArray(arr)) setHeatmap(arr);
    }).catch(() => {});
  }, []);

  // Transform today's sightings into the Visitor shape VisitorGrid expects
  const todayVisitors = todaySightings.map((s) => ({
    id: String(s.id),
    name: s.visitor_name ?? "Unknown",
    known: s.visitor_id !== null,
    thumbnail: snapshotUrl(s.snapshot_path),
    firstSeen: toTime(s.detected_at),
    lastSeen: toTime(s.detected_at),
    sightings: 1,
    camera: s.camera_name,
  }));

  // Transform top visitors for the TopVisitors component
  const topVisitorsMapped = topVisitors.map((v) => ({
    id: String(v.id),
    name: v.name,
    known: true,
    thumbnail: v.thumbnail_path ? snapshotUrl(v.thumbnail_path) : "",
    firstSeen: "",
    lastSeen: "",
    sightings: v.sighting_count,
  }));

  return (
    <main className="container py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Real-time visitor monitoring</p>
      </div>

      <StatsCards
        totalVisitors={stats.totalDetections}
        todayActivity={stats.todayDetections}
        activeCameras={stats.activeCameras}
        unknownToday={stats.unknownToday}
        onTotalClick={() => navigate("/history")}
        onTodayClick={() => navigate("/history?date=today")}
        onUnknownClick={() => navigate("/history?date=today&status=unknown")}
        onCamerasClick={() => navigate("/history?date=today")}
      />

      {/* Charts Row 1 */}
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <HourlyActivityChart
            data={hourly}
            onBarClick={(hour) => navigate(`/history?date=today&hour=${hour}`)}
          />
        </div>
        <KnownUnknownChart known={knownUnknown.known} unknown={knownUnknown.unknown} />
      </div>

      {/* Charts Row 2 */}
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <WeeklyTrendChart
            data={weekly}
            onPointClick={(date) => navigate(`/history?date=${date}`)}
          />
        </div>
        <TopVisitors visitors={topVisitorsMapped} />
      </div>

      {/* Charts Row 3 */}
      <div className="grid gap-4 lg:grid-cols-2">
        <CameraActivityChart data={cameras} />
        <PeakHoursHeatmap data={heatmap} />
      </div>

      {/* Today's Visitors — real sighting cards */}
      <VisitorGrid visitors={todayVisitors} />
    </main>
  );
};

export default Index;
