import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { Visitor } from "@/lib/mock-data";

export function TopVisitors({ visitors }: { visitors: Visitor[] }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Top Visitors</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {visitors.map((v, i) => (
          <div key={v.id} className="flex items-center gap-3">
            <span className="w-5 text-sm font-bold text-muted-foreground">#{i + 1}</span>
            <Avatar className="h-8 w-8">
              <AvatarFallback className="bg-primary/10 text-primary text-xs">
                {v.name.split(" ").map((n) => n[0]).join("")}
              </AvatarFallback>
            </Avatar>
            <span className="flex-1 text-sm truncate">{v.name}</span>
            <span className="text-sm font-semibold text-muted-foreground">{v.sightings}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
