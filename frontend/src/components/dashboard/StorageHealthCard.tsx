import { useEffect, useState } from "react";
import { HardDrive, Image, Trash2, CalendarClock, Clock, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";

interface StorageHealth {
  total_snapshots: number;
  snapshots_this_week: number;
  disk_mb_used: number;
  oldest_snapshot: string | null;
  last_cleanup_date: string | null;
  last_cleanup_freed_mb: number;
  last_cleanup_deleted: number;
  total_cleanups: number;
}

const SOFT_LIMIT_MB = 500; // warn colour above this
const HARD_LIMIT_MB = 2048; // progress bar max

function formatDate(dt: string | null): string {
  if (!dt) return "Never";
  try {
    return new Date(dt).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return dt;
  }
}

function formatMB(mb: number): string {
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
  return `${mb.toFixed(1)} MB`;
}

interface MetricTileProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  accent?: "blue" | "amber" | "green" | "red" | "purple";
}

function MetricTile({ icon, label, value, sub, accent = "blue" }: MetricTileProps) {
  const accentMap = {
    blue: "bg-primary/10 text-primary",
    amber: "bg-amber-500/10 text-amber-500",
    green: "bg-emerald-500/10 text-emerald-500",
    red: "bg-red-500/10 text-red-500",
    purple: "bg-purple-500/10 text-purple-500",
  };
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/40 border border-border/50">
      <div className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${accentMap[accent]}`}>
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide leading-none mb-1">{label}</p>
        <p className="text-base font-bold leading-tight truncate">{value}</p>
        {sub && <p className="text-[11px] text-muted-foreground mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

export function StorageHealthCard() {
  const [data, setData] = useState<StorageHealth | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.getStorageHealth()
      .then((d) => setData(d as StorageHealth))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const diskPct = data ? Math.min(100, (data.disk_mb_used / HARD_LIMIT_MB) * 100) : 0;
  const diskWarning = data && data.disk_mb_used > SOFT_LIMIT_MB;

  return (
    <Card className="opacity-0 animate-fade-in-up" style={{ animationDelay: "320ms" }}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <HardDrive className="h-4 w-4 text-primary" />
              Storage Health
            </CardTitle>
            <CardDescription className="mt-0.5">
              Snapshot disk usage and automated cleanup status
            </CardDescription>
          </div>
          <button
            onClick={load}
            className="text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh"
            aria-label="Refresh storage stats"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Disk usage bar */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-muted-foreground">Snapshot Disk Usage</span>
            <span className={`font-bold ${diskWarning ? "text-amber-500" : "text-foreground"}`}>
              {data ? formatMB(data.disk_mb_used) : "—"}
            </span>
          </div>
          <Progress
            value={diskPct}
            className={`h-2 ${diskWarning ? "[&>div]:bg-amber-500" : "[&>div]:bg-primary"}`}
          />
          <p className="text-[10px] text-muted-foreground">
            {diskWarning
              ? "⚠ Consider running cleanup or reducing retention days"
              : `${data ? formatMB(HARD_LIMIT_MB - data.disk_mb_used) : "—"} remaining before 2 GB threshold`}
          </p>
        </div>

        {/* Metric tiles grid */}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <MetricTile
            icon={<Image className="h-4 w-4" />}
            label="This Week"
            value={data ? data.snapshots_this_week.toLocaleString() : "—"}
            sub="snapshots captured"
            accent="blue"
          />
          <MetricTile
            icon={<Image className="h-4 w-4" />}
            label="All-Time Total"
            value={data ? data.total_snapshots.toLocaleString() : "—"}
            sub="lifetime snapshots"
            accent="purple"
          />
          <MetricTile
            icon={<Trash2 className="h-4 w-4" />}
            label="Last Cleanup"
            value={data ? formatMB(data.last_cleanup_freed_mb) : "—"}
            sub={data?.last_cleanup_deleted ? `${data.last_cleanup_deleted} files removed` : "no files removed"}
            accent="green"
          />
          <MetricTile
            icon={<CalendarClock className="h-4 w-4" />}
            label="Cleanup Ran"
            value={data ? formatDate(data.last_cleanup_date) : "—"}
            sub={data?.total_cleanups ? `${data.total_cleanups} total runs` : "not yet scheduled"}
            accent="amber"
          />
          <MetricTile
            icon={<Clock className="h-4 w-4" />}
            label="Oldest Snapshot"
            value={data ? formatDate(data.oldest_snapshot) : "—"}
            sub="earliest on disk"
            accent="blue"
          />
          <MetricTile
            icon={<RefreshCw className="h-4 w-4" />}
            label="Cleanups Run"
            value={data ? data.total_cleanups.toLocaleString() : "—"}
            sub="total automated runs"
            accent="purple"
          />
        </div>
      </CardContent>
    </Card>
  );
}
