import { Users, Activity, Camera, UserX } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface StatCardProps {
  title: string;
  subtitle: string;
  value: number;
  icon: React.ReactNode;
  delay: number;
  accentClass: string;
  iconBgClass: string;
  highlight?: boolean;
  onClick?: () => void;
  clickable?: boolean;
}

function StatCard({
  title, subtitle, value, icon, delay, accentClass, iconBgClass, onClick, clickable,
}: StatCardProps) {
  return (
    <Card
      className={`opacity-0 animate-fade-in-up overflow-hidden transition-all duration-150 ${
        clickable
          ? "cursor-pointer hover:shadow-[var(--card-shadow-hover)] hover:-translate-y-0.5 active:scale-[0.98]"
          : ""
      }`}
      style={{ animationDelay: `${delay}ms` }}
      onClick={onClick}
    >
      <div className={`h-1 w-full ${accentClass}`} />
      <CardContent className="flex items-center gap-4 px-5 py-4">
        <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${iconBgClass}`}>
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground leading-none mb-1">
            {title}
          </p>
          <p className="text-3xl font-extrabold leading-none tracking-tight">
            {value.toLocaleString()}
          </p>
          <p className="text-[11px] text-muted-foreground mt-1 leading-tight">{subtitle}</p>
        </div>
        {clickable && (
          <div className="ml-auto text-muted-foreground/30 text-lg font-light select-none">›</div>
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
        icon={<Users className="h-5 w-5 text-primary" />}
        delay={0}
        accentClass="bg-primary"
        iconBgClass="bg-primary/10"
        onClick={onTotalClick}
        clickable={!!onTotalClick}
      />
      <StatCard
        title="Today's Detections"
        subtitle="Faces detected today"
        value={todayActivity}
        icon={<Activity className="h-5 w-5 text-sky-500" />}
        delay={80}
        accentClass="bg-sky-500"
        iconBgClass="bg-sky-500/10"
        onClick={onTodayClick}
        clickable={!!onTodayClick}
      />
      <StatCard
        title="Active Cameras"
        subtitle="Currently streaming"
        value={activeCameras}
        icon={<Camera className="h-5 w-5 text-emerald-500" />}
        delay={160}
        accentClass="bg-emerald-500"
        iconBgClass="bg-emerald-500/10"
        onClick={onCamerasClick}
        clickable={!!onCamerasClick}
      />
      <StatCard
        title="Unidentified Today"
        subtitle="Unknown faces — needs naming"
        value={unknownToday}
        icon={<UserX className="h-5 w-5 text-amber-500" />}
        delay={240}
        accentClass={unknownToday > 0 ? "bg-amber-500" : "bg-muted"}
        iconBgClass="bg-amber-500/10"
        highlight={unknownToday > 0}
        onClick={onUnknownClick}
        clickable={!!onUnknownClick}
      />
    </div>
  );
}
