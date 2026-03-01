import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Label, LabelList } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import type { CameraActivity } from "@/lib/mock-data";

function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      backgroundColor: "hsl(var(--popover))",
      border: "1px solid hsl(var(--border))",
      borderRadius: 6,
      padding: "8px 12px",
      fontSize: 12,
      color: "hsl(var(--popover-foreground))",
      boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
    }}>
      <p style={{ fontWeight: 700, marginBottom: 2, textTransform: "capitalize" }}>
        {String(label).replace(/_/g, " ")}
      </p>
      <p>{payload[0].value} detection{payload[0].value !== 1 ? "s" : ""} today</p>
    </div>
  );
}

export function CameraActivityChart({ data }: { data: CameraActivity[] }) {
  // Capitalise camera names for display
  const displayData = data.map((d) => ({
    ...d,
    camera: d.camera.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
  }));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Activity by Camera — Today</CardTitle>
        <CardDescription>Total face detections per camera today</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={displayData} layout="vertical" margin={{ top: 4, right: 48, left: 0, bottom: 28 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} allowDecimals={false}>
                <Label
                  value="Detections"
                  offset={-14}
                  position="insideBottom"
                  style={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                />
              </XAxis>
              <YAxis
                dataKey="camera"
                type="category"
                tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                width={110}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="detections" fill="hsl(var(--primary))" radius={[0, 6, 6, 0]}>
                <LabelList
                  dataKey="detections"
                  position="right"
                  style={{ fontSize: 11, fill: "hsl(var(--foreground))", fontWeight: 600 }}
                  formatter={(v: number) => (v > 0 ? v : "")}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
