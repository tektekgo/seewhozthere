import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  known: number;
  unknown: number;
}

export function KnownUnknownChart({ known, unknown }: Props) {
  const total = known + unknown;
  const data = [
    { name: "Known", value: known },
    { name: "Unknown", value: unknown },
  ];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Known vs Unknown</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64 flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={85}
                paddingAngle={4}
                dataKey="value"
                stroke="none"
              >
                <Cell fill="hsl(var(--chart-known))" />
                <Cell fill="hsl(var(--chart-unknown))" />
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                  color: "hsl(var(--foreground))",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="flex justify-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-chart-known" />
            <span>Known {total > 0 ? Math.round((known / total) * 100) : 0}%</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-chart-unknown" />
            <span>Unknown {total > 0 ? Math.round((unknown / total) * 100) : 0}%</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
