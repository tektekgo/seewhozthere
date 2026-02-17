import { Users, Activity, Camera, UserX } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface StatCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  delay: number;
}

function StatCard({ title, value, icon, delay }: StatCardProps) {
  return (
    <Card className="opacity-0 animate-fade-in-up" style={{ animationDelay: `${delay}ms` }}>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold">{value.toLocaleString()}</p>
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
      <StatCard title="Total Visitors" value={totalVisitors} icon={<Users className="h-5 w-5" />} delay={0} />
      <StatCard title="Today's Activity" value={todayActivity} icon={<Activity className="h-5 w-5" />} delay={80} />
      <StatCard title="Active Cameras" value={activeCameras} icon={<Camera className="h-5 w-5" />} delay={160} />
      <StatCard title="Unknown Today" value={unknownToday} icon={<UserX className="h-5 w-5" />} delay={240} />
    </div>
  );
}
