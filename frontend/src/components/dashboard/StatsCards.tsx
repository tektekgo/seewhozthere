import { Users, Activity, Camera, UserX } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface StatCardProps {
  title: string;
  subtitle: string;
  value: number;
  icon: React.ReactNode;
  delay: number;
  highlight?: boolean;
  onClick?: () => void;
  clickable?: boolean;
}

function StatCard({ title, subtitle, value, icon, delay, highlight, onClick, clickable }: StatCardProps) {
  return (
    <Card
      className={`opacity-0 animate-fade-in-up transition-all duration-150 ${
        clickable ? "cursor-pointer hover:shadow-md hover:ring-1 hover:ring-primary/40 active:scale-[0.98]" : ""
      }`}
      style={{ animationDelay: `${delay}ms` }}
      onClick={onClick}
    >
      <CardContent className="flex items-center gap-4 p-5">
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${highlight ? "bg-amber-500/10 text-amber-500" : "bg-primary/10 text-primary"}`}>
          {icon}
        </div>
        <div className="flex-1">
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold">{value.toLocaleString()}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
        </div>
        {clickable && (
          <div className="ml-auto text-muted-foreground/40 text-sm">›</div>
        )}
      </CardContent>
    </Card>
  );
}

interface StatsCardsProps {
  totalVisitors: number;
  todayActivity: number;
  activeCameras: number;
  unknownToday: number;
  onTotalClick?: () => void;
  onTodayClick?: () => void;
  onUnknownClick?: () => void;
  onCamerasClick?: () => void;
}

export function StatsCards({
  totalVisitors, todayActivity, activeCameras, unknownToday,
  onTotalClick, onTodayClick, onUnknownClick, onCamerasClick,
}: StatsCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Total Detections"
        subtitle="All-time — click to browse"
        value={totalVisitors}
        icon={<Users className="h-5 w-5" />}
        delay={0}
        onClick={onTotalClick}
        clickable={!!onTotalClick}
      />
      <StatCard
        title="Today's Detections"
        subtitle="Faces detected today"
        value={todayActivity}
        icon={<Activity className="h-5 w-5" />}
        delay={80}
        onClick={onTodayClick}
        clickable={!!onTodayClick}
      />
      <StatCard
        title="Active Cameras"
        subtitle="Currently streaming"
        value={activeCameras}
        icon={<Camera className="h-5 w-5" />}
        delay={160}
        onClick={onCamerasClick}
        clickable={!!onCamerasClick}
      />
      <StatCard
        title="Unidentified Today"
        subtitle="Unknown faces — needs naming"
        value={unknownToday}
        icon={<UserX className="h-5 w-5" />}
        delay={240}
        highlight={unknownToday > 0}
        onClick={onUnknownClick}
        clickable={!!onUnknownClick}
      />
    </div>
  );
}
