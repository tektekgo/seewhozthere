import { Users, Activity, Camera, UserX } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface StatCardProps {
  title: string;
  subtitle: string;
  value: number;
  icon: React.ReactNode;
  delay: number;
  highlight?: boolean;
}

function StatCard({ title, subtitle, value, icon, delay, highlight }: StatCardProps) {
  return (
    <Card className="opacity-0 animate-fade-in-up" style={{ animationDelay: `${delay}ms` }}>
      <CardContent className="flex items-center gap-4 p-5">
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${highlight ? "bg-amber-500/10 text-amber-500" : "bg-primary/10 text-primary"}`}>
          {icon}
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold">{value.toLocaleString()}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
        </div>
      </CardContent>
    </Card>
  );
}

interface StatsCardsProps {
  totalVisitors: number;
  todayActivity: number;
  activeCameras: number;
  unknownToday: number;
}

export function StatsCards({ totalVisitors, todayActivity, activeCameras, unknownToday }: StatsCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Total Detections"
        subtitle="All-time face detections"
        value={totalVisitors}
        icon={<Users className="h-5 w-5" />}
        delay={0}
      />
      <StatCard
        title="Today's Detections"
        subtitle="Faces detected today"
        value={todayActivity}
        icon={<Activity className="h-5 w-5" />}
        delay={80}
      />
      <StatCard
        title="Active Cameras"
        subtitle="Currently streaming"
        value={activeCameras}
        icon={<Camera className="h-5 w-5" />}
        delay={160}
      />
      <StatCard
        title="Unidentified Today"
        subtitle="Unknown faces — needs naming"
        value={unknownToday}
        icon={<UserX className="h-5 w-5" />}
        delay={240}
        highlight={unknownToday > 0}
      />
    </div>
  );
}
