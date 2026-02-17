import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Visitor } from "@/lib/mock-data";

type Filter = "all" | "known" | "unknown";

export function VisitorGrid({ visitors }: { visitors: Visitor[] }) {
  const [filter, setFilter] = useState<Filter>("all");

  const filtered = visitors.filter((v) => {
    if (filter === "known") return v.known;
    if (filter === "unknown") return !v.known;
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Today's Visitors</h2>
        <div className="flex gap-1">
          {(["all", "known", "unknown"] as Filter[]).map((f) => (
            <Button key={f} variant={filter === f ? "secondary" : "ghost"} size="sm" onClick={() => setFilter(f)}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </Button>
          ))}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {filtered.map((v) => (
          <Card key={v.id} className="hover:border-primary/30 transition-colors">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <Avatar className="h-10 w-10">
                  <AvatarFallback className={v.known ? "bg-primary/10 text-primary" : "bg-accent/20 text-accent"}>
                    {v.known ? v.name.split(" ").map((n) => n[0]).join("") : "?"}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium truncate">{v.name}</p>
                    <Badge variant={v.known ? "default" : "secondary"} className="text-[10px] shrink-0">
                      {v.known ? "Known" : "Unknown"}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {v.firstSeen} — {v.lastSeen} · {v.sightings} sighting{v.sightings !== 1 ? "s" : ""}
                  </p>
                </div>
              </div>
              <div className="mt-3 flex gap-2">
                <Button variant="outline" size="sm" className="flex-1 text-xs h-7">
                  {v.known ? "History" : "Identify"}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
