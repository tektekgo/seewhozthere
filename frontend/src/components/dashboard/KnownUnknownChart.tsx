import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

interface Props {
  known: number;
  unknown: number;
}

export function KnownUnknownChart({ known, unknown }: Props) {
  const total = known + unknown;
  const data = [
    { name: "Identified", value: known },
    { name: "Unknown", value: unknown },
  ];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Identified vs Unknown</CardTitle>
        <CardDescription>Breakdown of today's detections by recognition status</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="relative h-56 flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={82}
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
                  fontSize: 12,
                }}
                formatter={(value: number, name: string) => [`${value} (${total > 0 ? Math.round((value / total) * 100) : 0}%)`, name]}
              />
            </PieChart>
          </ResponsiveContainer>
          {/* Centre label */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-2xl font-bold">{total}</span>
            <span className="text-xs text-muted-foreground">total</span>
          </div>
        </div>
        <div className="flex justify-center gap-6 text-sm mt-2">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full" style={{ backgroundColor: "hsl(var(--chart-known))" }} />
            <span>Identified — <strong>{known}</strong> ({total > 0 ? Math.round((known / total) * 100) : 0}%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full" style={{ backgroundColor: "hsl(var(--chart-unknown))" }} />
            <span>Unknown — <strong>{unknown}</strong> ({total > 0 ? Math.round((unknown / total) * 100) : 0}%)</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
