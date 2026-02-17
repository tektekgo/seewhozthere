import { useEffect, useState } from "react";
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
  mockStats,
  mockHourlyData,
  mockKnownVsUnknown,
  mockWeeklyTrend,
  mockCameraActivity,
  mockTopVisitors,
  mockTodayVisitors,
  mockHeatmapData,
  type HourlyActivity,
  type WeeklyTrend,
  type CameraActivity,
  type Visitor,
  type HeatmapCell,
} from "@/lib/mock-data";

const Index = () => {
  const [stats, setStats] = useState(mockStats);
  const [hourly, setHourly] = useState<HourlyActivity[]>(mockHourlyData);
  const [knownUnknown, setKnownUnknown] = useState(mockKnownVsUnknown);
  const [weekly, setWeekly] = useState<WeeklyTrend[]>(mockWeeklyTrend);
  const [cameras, setCameras] = useState<CameraActivity[]>(mockCameraActivity);
  const [topVisitors, setTopVisitors] = useState<Visitor[]>(mockTopVisitors);
  const [todayVisitors, setTodayVisitors] = useState<Visitor[]>(mockTodayVisitors);
  const [heatmap, setHeatmap] = useState<HeatmapCell[]>(mockHeatmapData);

  useEffect(() => {
    Promise.all([
      api.getStats().then(setStats),
      api.getHourlyActivity().then(setHourly),
      api.getKnownVsUnknown().then(setKnownUnknown),
      api.getWeeklyTrend().then(setWeekly),
      api.getCameraActivity().then(setCameras),
      api.getTopVisitors().then(setTopVisitors),
      api.getTodayVisitors().then(setTodayVisitors),
      api.getHeatmapData().then(setHeatmap),
    ]);
  }, []);

  return (
    <main className="container py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Real-time visitor monitoring</p>
      </div>

      <StatsCards
        totalVisitors={stats.totalVisitors}
        todayActivity={stats.todayActivity}
        activeCameras={stats.activeCameras}
        unknownToday={stats.unknownToday}
      />

      {/* Charts Row 1 */}
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <HourlyActivityChart data={hourly} />
        </div>
        <KnownUnknownChart known={knownUnknown.known} unknown={knownUnknown.unknown} />
      </div>

      {/* Charts Row 2 */}
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <WeeklyTrendChart data={weekly} />
        </div>
        <TopVisitors visitors={topVisitors} />
      </div>

      {/* Charts Row 3 */}
      <div className="grid gap-4 lg:grid-cols-2">
        <CameraActivityChart data={cameras} />
        <PeakHoursHeatmap data={heatmap} />
      </div>

      {/* Visitor Grid */}
      <VisitorGrid visitors={todayVisitors} />
    </main>
  );
};

export default Index;
