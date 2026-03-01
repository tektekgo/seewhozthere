import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { mockTodayVisitors, type Visitor } from "@/lib/mock-data";
import { Search, UserCheck, UserX, Clock } from "lucide-react";

const History = () => {
  const [visitors, setVisitors] = useState<Visitor[]>(mockTodayVisitors);
  const [filter, setFilter] = useState<"all" | "known" | "unknown">("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTodayVisitors()
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) setVisitors(data);
      })
      .finally(() => setLoading(false));
  }, []);

  const filtered = visitors.filter((v) => {
    const matchesFilter =
      filter === "all" ||
      (filter === "known" && v.known) ||
      (filter === "unknown" && !v.known);
    const matchesSearch =
      search === "" ||
      v.name.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <main className="container py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Visitor History</h1>
        <p className="text-sm text-muted-foreground">All detected visitors and activity logs</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search visitors..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2">
          {(["all", "known", "unknown"] as const).map((f) => (
            <Button
              key={f}
              variant={filter === f ? "default" : "outline"}
              size="sm"
              onClick={() => setFilter(f)}
              className="capitalize"
            >
              {f === "known" && <UserCheck className="h-3.5 w-3.5 mr-1" />}
              {f === "unknown" && <UserX className="h-3.5 w-3.5 mr-1" />}
              {f}
            </Button>
          ))}
        </div>
      </div>

      <div className="flex gap-4 text-sm text-muted-foreground">
        <span><strong className="text-foreground">{visitors.filter(v => v.known).length}</strong> known</span>
        <span><strong className="text-foreground">{visitors.filter(v => !v.known).length}</strong> unknown</span>
        <span><strong className="text-foreground">{visitors.length}</strong> total</span>
      </div>

      {loading ? (
        <div className="text-center py-12 text-muted-foreground">Loading history...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 space-y-2">
          <UserX className="h-12 w-12 mx-auto text-muted-foreground/40" />
          <p className="text-lg font-medium">No visitors found</p>
          <p className="text-sm text-muted-foreground">
            {search ? "Try a different search term." : "No activity recorded yet."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((visitor) => (
            <Card key={visitor.id} className="hover:shadow-md transition-shadow">
              <CardContent className="flex items-center gap-4 p-4">
                <div className="relative shrink-0">
                  {visitor.thumbnail ? (
                    <img
                      src={visitor.thumbnail}
                      alt={visitor.name}
                      className="h-12 w-12 rounded-full object-cover border-2 border-border"
                    />
                  ) : (
                    <div className={`h-12 w-12 rounded-full flex items-center justify-center text-lg font-bold border-2 ${
                      visitor.known
                        ? "bg-primary/10 border-primary/30 text-primary"
                        : "bg-accent/10 border-accent/30 text-accent"
                    }`}>
                      {visitor.known ? visitor.name[0].toUpperCase() : "?"}
                    </div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold truncate">{visitor.name}</span>
                    <Badge variant={visitor.known ? "default" : "secondary"} className="text-xs">
                      {visitor.known ? "Known" : "Unknown"}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground flex-wrap">
                    {visitor.lastSeen && (
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Last seen: {visitor.lastSeen}
                      </span>
                    )}
                    {visitor.firstSeen && (
                      <span>First seen: {visitor.firstSeen}</span>
                    )}
                    <span>{visitor.sightings} sighting{visitor.sightings !== 1 ? "s" : ""}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </main>
  );
};

export default History;
