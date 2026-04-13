import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { UserX, Clock, ArrowRight, ZoomIn } from "lucide-react";
import type { Visitor } from "@/lib/mock-data";
import { ImageLightbox, type LightboxImage } from "@/components/ImageLightbox";

type Filter = "all" | "known" | "unknown";

interface VisitorGridProps {
  visitors: Visitor[];
}

export function VisitorGrid({ visitors }: VisitorGridProps) {
  const [filter, setFilter] = useState<Filter>("all");
  const [lightbox, setLightbox] = useState<LightboxImage | null>(null);

  const filtered = visitors.filter((v) => {
    if (filter === "known") return v.known;
    if (filter === "unknown") return !v.known;
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-lg font-semibold">Today's Visitors</h2>
          <p className="text-sm text-muted-foreground">People detected by your cameras today</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            {(["all", "known", "unknown"] as Filter[]).map((f) => (
              <Button
                key={f}
                variant={filter === f ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setFilter(f)}
                className="capitalize text-xs"
              >
                {f}
              </Button>
            ))}
          </div>
          <Link to="/history">
            <Button variant="outline" size="sm" className="text-xs">
              View All <ArrowRight className="h-3 w-3 ml-1" />
            </Button>
          </Link>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-12 space-y-2 border rounded-lg bg-muted/20">
          <UserX className="h-10 w-10 mx-auto text-muted-foreground/30" />
          <p className="text-sm font-medium text-muted-foreground">
            {visitors.length === 0
              ? "No visitors detected today yet"
              : `No ${filter} visitors today`}
          </p>
          {visitors.length === 0 && (
            <p className="text-xs text-muted-foreground">
              Detections will appear here once the camera captures faces
            </p>
          )}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filtered.map((v) => (
            <Card key={v.id} className="hover:shadow-md hover:border-primary/30 transition-all overflow-hidden">
              <CardContent className="p-0">
                <div className="flex">
                  {/* Face thumbnail — click to enlarge */}
                  <div className="shrink-0 w-20 h-20 bg-muted relative group">
                    {v.thumbnail ? (
                      <>
                        <img
                          src={v.thumbnail}
                          alt={v.name}
                          className="w-full h-full object-contain cursor-zoom-in"
                          onClick={() =>
                            setLightbox({
                              src: v.thumbnail!,
                              alt: v.name,
                              caption: `${v.name} · ${v.firstSeen}`,
                            })
                          }
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = "none";
                          }}
                        />
                        {/* Zoom hint overlay */}
                        <div
                          className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100 cursor-zoom-in"
                          onClick={() =>
                            setLightbox({
                              src: v.thumbnail!,
                              alt: v.name,
                              caption: `${v.name} · ${v.firstSeen}`,
                            })
                          }
                        >
                          <ZoomIn className="h-5 w-5 text-white drop-shadow" />
                        </div>
                      </>
                    ) : (
                      <div className={`w-full h-full flex items-center justify-center text-xl font-bold ${v.known ? "bg-primary/10 text-primary" : "bg-amber-500/10 text-amber-500"}`}>
                        {v.known ? v.name.split(" ").map((n) => n[0]).join("").slice(0, 2) : "?"}
                      </div>
                    )}
                    <div className="absolute bottom-1 left-1">
                      <Badge
                        variant={v.known ? "default" : "secondary"}
                        className={`text-[8px] px-1 py-0 ${v.known ? "" : "bg-amber-500/80 text-white border-0"}`}
                      >
                        {v.known ? "Known" : "Unknown"}
                      </Badge>
                    </div>
                  </div>

                  {/* Info */}
                  <div className="flex-1 p-3 flex flex-col justify-between min-w-0">
                    <div>
                      <p className="text-sm font-semibold truncate">{v.name}</p>
                      <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3 shrink-0" />
                        <span className="truncate">{v.firstSeen} – {v.lastSeen}</span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {v.sightings} detection{v.sightings !== 1 ? "s" : ""}
                      </p>
                    </div>
                    <Link to="/history">
                      <Button variant="ghost" size="sm" className="h-6 text-xs px-2 mt-1 w-full justify-start text-muted-foreground hover:text-foreground">
                        {v.known ? "View history →" : "Name this person →"}
                      </Button>
                    </Link>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <ImageLightbox image={lightbox} onClose={() => setLightbox(null)} />
    </div>
  );
}
