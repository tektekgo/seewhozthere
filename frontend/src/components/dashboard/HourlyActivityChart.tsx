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

export function HourlyActivityChart({ data }: { data: HourlyActivity[] }) {
  // Only show tick labels every 3 hours to avoid crowding
  const tickFormatter = (value: string) => {
    const hour = parseInt(value.split(":")[0], 10);
    return hour % 3 === 0 ? value : "";
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Hourly Activity — {todayLabel}</CardTitle>
        <CardDescription>
          Number of face detections per hour today, split by identified vs unknown visitors
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} barGap={0} margin={{ top: 16, right: 8, left: 8, bottom: 28 }}>
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
              <Legend
                formatter={(value) => (value === "known" ? "Identified" : "Unknown")}
                wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
              />
              <Bar dataKey="known" stackId="a" fill="hsl(var(--chart-known))" name="known">
                {/* No label on middle of stacked bar — label on top bar only */}
              </Bar>
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
