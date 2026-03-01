import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, LabelList } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

interface Props {
  known: number;
  unknown: number;
}

// Custom tooltip — explicit background + text so it's always readable in dark mode
function CustomTooltip({ active, payload }: {
  active?: boolean;
  payload?: { name: string; value: number; payload: { pct: string } }[];
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0];
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
      <p style={{ fontWeight: 700, marginBottom: 2 }}>{p.name}</p>
      <p>{p.value} detection{p.value !== 1 ? "s" : ""}</p>
      <p style={{ color: "hsl(var(--muted-foreground))" }}>{p.payload.pct} of today</p>
    </div>
  );
}

// Render count label directly on the pie segment (only when value > 0)
function PieLabel({ cx, cy, midAngle, innerRadius, outerRadius, value }: {
  cx: number; cy: number; midAngle: number;
  innerRadius: number; outerRadius: number; value: number;
}) {
  if (!value) return null;
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="#fff" textAnchor="middle" dominantBaseline="central" fontSize={12} fontWeight={700}>
      {value}
    </text>
  );
}

export function KnownUnknownChart({ known, unknown }: Props) {
  const total = known + unknown;
  const pct = (n: number) => (total > 0 ? `${Math.round((n / total) * 100)}%` : "0%");

  const data = [
    { name: "Identified", value: known, pct: pct(known) },
    { name: "Unknown", value: unknown, pct: pct(unknown) },
  ];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Identified vs Unknown — Today</CardTitle>
        <CardDescription>
          Breakdown of today's detections by recognition status. Hover a segment for details.
        </CardDescription>
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
                labelLine={false}
                label={PieLabel}
              >
                <Cell fill="hsl(var(--chart-known))" />
                <Cell fill="hsl(var(--chart-unknown))" />
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
          {/* Centre total */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-2xl font-bold">{total}</span>
            <span className="text-xs text-muted-foreground">today</span>
          </div>
        </div>

        {/* Legend with counts + percentages */}
        <div className="flex justify-center gap-6 text-sm mt-2">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: "hsl(var(--chart-known))" }} />
            <span>Identified — <strong>{known}</strong> <span className="text-muted-foreground">({pct(known)})</span></span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: "hsl(var(--chart-unknown))" }} />
            <span>Unknown — <strong>{unknown}</strong> <span className="text-muted-foreground">({pct(unknown)})</span></span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
