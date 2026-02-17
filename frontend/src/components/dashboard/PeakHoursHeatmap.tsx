import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { HeatmapCell } from "@/lib/mock-data";

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const hours = Array.from({ length: 24 }, (_, i) => i);

function getColor(value: number, max: number) {
  if (value === 0) return "hsl(var(--muted))";
  const ratio = value / max;
  // Blend from primary (cool) to accent (hot)
  if (ratio < 0.5) return `hsl(var(--primary) / ${0.2 + ratio})`;
  return `hsl(var(--accent) / ${0.3 + ratio * 0.7})`;
}

export function PeakHoursHeatmap({ data }: { data: HeatmapCell[] }) {
  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <Card className="col-span-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Peak Hours Heatmap</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <div className="min-w-[600px]">
            {/* Hour labels */}
            <div className="flex ml-10 mb-1">
              {hours.filter((_, i) => i % 3 === 0).map((h) => (
                <span key={h} className="text-[10px] text-muted-foreground" style={{ width: `${(3 / 24) * 100}%` }}>
                  {h.toString().padStart(2, "0")}
                </span>
              ))}
            </div>
            {/* Rows */}
            {days.map((day) => (
              <div key={day} className="flex items-center gap-1 mb-[2px]">
                <span className="w-9 text-xs text-muted-foreground text-right pr-1">{day}</span>
                <div className="flex flex-1 gap-[2px]">
                  {hours.map((hour) => {
                    const cell = data.find((d) => d.day === day && d.hour === hour);
                    return (
                      <div
                        key={hour}
                        className="flex-1 aspect-square rounded-sm transition-colors"
                        style={{ backgroundColor: getColor(cell?.value || 0, max) }}
                        title={`${day} ${hour}:00 — ${cell?.value || 0} detections`}
                      />
                    );
                  })}
                </div>
              </div>
            ))}
            {/* Legend */}
            <div className="flex items-center justify-end gap-2 mt-2 text-[10px] text-muted-foreground">
              <span>Low</span>
              <div className="flex gap-[1px]">
                {[0, 2, 4, 6, 8, 10].map((v) => (
                  <div key={v} className="h-3 w-3 rounded-sm" style={{ backgroundColor: getColor(v, 10) }} />
                ))}
              </div>
              <span>High</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
