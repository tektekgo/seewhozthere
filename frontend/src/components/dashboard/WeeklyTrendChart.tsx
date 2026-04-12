import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Label, LabelList,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import type { WeeklyTrend } from "@/lib/mock-data";

function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      backgroundColor: "hsl(var(--card))",
      border: "1px solid hsl(var(--border))",
      borderRadius: 6,
      padding: "8px 12px",
      fontSize: 12,
      color: "hsl(var(--foreground))",
    }}>
      <p style={{ fontWeight: 600 }}>{label}</p>
      <p style={{ color: "hsl(var(--primary))" }}>
        {payload[0].value} detection{payload[0].value !== 1 ? "s" : ""}
      </p>
    </div>
  );
}

export function WeeklyTrendChart({
  data,
  onPointClick,
}: {
  data: WeeklyTrend[];
  onPointClick?: (date: string) => void;
}) {
  const handleClick = (chartData: { activePayload?: { payload: WeeklyTrend & { date?: string } }[] }) => {
    if (!onPointClick || !chartData?.activePayload?.[0]) return;
    const entry = chartData.activePayload[0].payload;
    if (entry.date) onPointClick(entry.date);
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Weekly Trend — Last 7 Days</CardTitle>
        <CardDescription>
          Total face detections per day — click a point to drill into that day
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data}
              margin={{ top: 20, right: 16, left: 8, bottom: 28 }}
              onClick={onPointClick ? handleClick : undefined}
              style={onPointClick ? { cursor: "pointer" } : undefined}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="day" tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}>
                <Label
                  value="Day of Week — click to filter"
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
              <Line
                type="monotone"
                dataKey="visitors"
                stroke="hsl(var(--primary))"
                strokeWidth={2.5}
                dot={{ r: 4, fill: "hsl(var(--primary))", strokeWidth: 0 }}
                activeDot={{ r: 7, strokeWidth: 2, stroke: "hsl(var(--primary))", fill: "hsl(var(--background))" }}
              >
                <LabelList
                  dataKey="visitors"
                  position="top"
                  style={{ fontSize: 10, fill: "hsl(var(--foreground))", fontWeight: 600 }}
                  formatter={(v: number) => (v > 0 ? v : "")}
                />
              </Line>
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
