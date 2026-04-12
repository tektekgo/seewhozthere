import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, LabelList, Label,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import type { HourlyActivity } from "@/lib/mock-data";

// Format today's date for the title
const todayLabel = new Date().toLocaleDateString(undefined, {
  weekday: "long", year: "numeric", month: "long", day: "numeric",
});

// Only show labels on bars with value > 0
function SmartLabel(props: { x?: number; y?: number; width?: number; value?: number }) {
  const { x = 0, y = 0, width = 0, value = 0 } = props;
  if (!value || value === 0) return null;
  return (
    <text
      x={x + width / 2}
      y={y - 3}
      fill="hsl(var(--foreground))"
      textAnchor="middle"
      fontSize={9}
      fontWeight={600}
    >
      {value}
    </text>
  );
}

// Custom tooltip with explicit text color
function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const total = payload.reduce((s, p) => s + (p.value ?? 0), 0);
  return (
    <div
      style={{
        backgroundColor: "hsl(var(--card))",
        border: "1px solid hsl(var(--border))",
        borderRadius: 6,
        padding: "8px 12px",
        fontSize: 12,
        color: "hsl(var(--foreground))",
      }}
    >
      <p style={{ fontWeight: 600, marginBottom: 4 }}>{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name === "known" ? "Identified" : "Unknown"}: {p.value}
        </p>
      ))}
      {total > 0 && (
        <p style={{ borderTop: "1px solid hsl(var(--border))", marginTop: 4, paddingTop: 4, fontWeight: 600 }}>
          Total: {total}
        </p>
      )}
    </div>
  );
}

export function HourlyActivityChart({
  data,
  onBarClick,
}: {
  data: HourlyActivity[];
  onBarClick?: (hour: string) => void;
}) {
  // Only show tick labels every 3 hours to avoid crowding
  const tickFormatter = (value: string) => {
    const hour = parseInt(value.split(":")[0], 10);
    return hour % 3 === 0 ? value : "";
  };

  const handleClick = (barData: { activePayload?: { payload: HourlyActivity }[] }) => {
    if (!onBarClick || !barData?.activePayload?.[0]) return;
    const hour = barData.activePayload[0].payload.hour; // e.g. "14:00"
    const hourNum = hour.split(":")[0]; // "14"
    onBarClick(hourNum);
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Hourly Activity — {todayLabel}</CardTitle>
        <CardDescription>
          Number of face detections per hour today — click a bar to drill into that hour
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Legend sits above the chart so it never overlaps the X-axis title */}
        <div className="flex items-center gap-4 mb-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-sm" style={{ background: "hsl(var(--chart-known))" }} />
            Identified
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-sm" style={{ background: "hsl(var(--chart-unknown))" }} />
            Unknown
          </span>
          {onBarClick && (
            <span className="ml-auto text-xs text-muted-foreground/60 italic">Click a bar to filter History</span>
          )}
        </div>
        <div className="h-60">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              barGap={0}
              margin={{ top: 8, right: 8, left: 8, bottom: 28 }}
              onClick={onBarClick ? handleClick : undefined}
              style={onBarClick ? { cursor: "pointer" } : undefined}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="hour"
                tickFormatter={tickFormatter}
                tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                interval={0}
              >
                <Label
                  value="Hour of Day"
                  offset={-14}
                  position="insideBottom"
                  style={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                />
              </XAxis>
              <YAxis
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                allowDecimals={false}
                width={40}
              >
                <Label
                  value="Detections"
                  angle={-90}
                  position="insideLeft"
                  offset={14}
                  style={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                />
              </YAxis>
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="known" stackId="a" fill="hsl(var(--chart-known))" name="known" />
              <Bar dataKey="unknown" stackId="a" fill="hsl(var(--chart-unknown))" name="unknown" radius={[3, 3, 0, 0]}>
                <LabelList content={<SmartLabel />} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
