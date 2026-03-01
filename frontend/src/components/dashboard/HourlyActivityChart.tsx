import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Label } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import type { HourlyActivity } from "@/lib/mock-data";

export function HourlyActivityChart({ data }: { data: HourlyActivity[] }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Hourly Activity</CardTitle>
        <CardDescription>Number of face detections per hour of the day (today)</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} barGap={0} margin={{ top: 4, right: 8, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="hour" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} interval={2}>
                <Label value="Hour of Day" offset={-12} position="insideBottom" style={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              </XAxis>
              <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} allowDecimals={false}>
                <Label value="Detections" angle={-90} position="insideLeft" offset={12} style={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              </YAxis>
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                  color: "hsl(var(--foreground))",
                  fontSize: 12,
                }}
                formatter={(value: number, name: string) => [value, name === "known" ? "Identified" : "Unknown"]}
                labelFormatter={(label) => `${label}`}
              />
              <Legend formatter={(value) => value === "known" ? "Identified" : "Unknown"} wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
              <Bar dataKey="known" stackId="a" fill="hsl(var(--chart-known))" name="known" />
              <Bar dataKey="unknown" stackId="a" fill="hsl(var(--chart-unknown))" name="unknown" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
