import { useEffect, useState, useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Search, UserCheck, UserX, Camera, Clock, Calendar,
  Plus, Tag, Trash2, RefreshCw, CheckSquare, Square,
  CheckCheck, X, Users, Video, Filter as FilterIcon, ZoomIn,
} from "lucide-react";
import { ImageLightbox, type LightboxImage } from "@/components/ImageLightbox";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { api } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Sighting {
  id: number;
  camera_name: string;
  timestamp: string | null;
  snapshot_url: string | null;
  visitor_id?: number | null;
  visitor_name?: string | null;
}

interface KnownVisitor {
  id: number;
  name: string;
  thumbnail_path?: string | null;
}

type Filter = "all" | "unknown" | "known";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDateTime(iso: string | null): { date: string; time: string } {
  if (!iso) return { date: "Unknown date", time: "" };
  const d = new Date(iso);
  return {
    date: d.toLocaleDateString(undefined, {
      weekday: "short", year: "numeric", month: "short", day: "numeric",
    }),
    time: d.toLocaleTimeString(undefined, {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    }),
  };
}

/** Return YYYY-MM-DD for a Date (or "today") */
function toIsoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

// ─── Name Dialog (single or bulk) ─────────────────────────────────────────────

interface NameDialogProps {
  sightingIds: number[];           // 1 = single, >1 = bulk
  previewSighting?: Sighting;      // show thumbnail for single
  knownVisitors: KnownVisitor[];
  isCorrection?: boolean;          // true when re-identifying an already-named sighting
  onClose: () => void;
  onNamed: (ids: number[], visitorName: string) => void;
}

function NameDialog({ sightingIds, previewSighting, knownVisitors, isCorrection, onClose, onNamed }: NameDialogProps) {
  const [mode, setMode] = useState<"select" | "new" | "unknown">("select");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [newName, setNewName] = useState("");
  const [newPhoto, setNewPhoto] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const isBulk = sightingIds.length > 1;

  const handleSave = async () => {
    setSaving(true);
    try {
      // Mark as Unknown
      if (mode === "unknown") {
        const results = await Promise.allSettled(
          sightingIds.map((id) => api.unidentifySighting(id))
        );
        const succeeded = results.filter((r) => r.status === "fulfilled").length;
        if (succeeded > 0) {
          toast.success(isBulk ? `${succeeded} detections marked as Unknown` : "Marked as Unknown");
          onNamed(sightingIds, "");
        } else {
          toast.error("Failed to update");
        }
        setSaving(false);
        onClose();
        return;
      }

      let visitorId: number | null = null;
      let visitorName = "";

      if (mode === "select" && selectedId !== null) {
        visitorId = selectedId;
        visitorName = knownVisitors.find((v) => v.id === selectedId)?.name ?? "Known";
      } else if (mode === "new" && newName.trim()) {
        const addRes = await api.addVisitor(newName.trim(), newPhoto ?? undefined);
        if (!addRes.id) {
          toast.error(addRes.detail ?? "Failed to add visitor");
          setSaving(false);
          return;
        }
        visitorId = addRes.id;
        visitorName = newName.trim();
      } else {
        setSaving(false);
        return;
      }

      // Identify each selected sighting
      const results = await Promise.allSettled(
        sightingIds.map((id) => api.identifySighting(id, visitorId!))
      );
      const succeeded = results.filter((r) => r.status === "fulfilled").length;

      if (succeeded === sightingIds.length) {
        toast.success(
          isBulk
            ? `${succeeded} detections identified as ${visitorName}`
            : `Identified as ${visitorName}`
        );
      } else {
        toast.warning(`${succeeded} of ${sightingIds.length} identified as ${visitorName}`);
      }

      onNamed(sightingIds, visitorName);
    } catch {
      toast.error("An error occurred");
    } finally {
      setSaving(false);
      onClose();
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            {isCorrection
              ? (isBulk ? `Correct ${sightingIds.length} Detections` : "Correct Identity")
              : (isBulk ? `Name ${sightingIds.length} Selected Detections` : "Name This Person")}
          </DialogTitle>
          <DialogDescription>
            {isCorrection
              ? "Select the correct person, or mark as Unknown if the identification was wrong."
              : (isBulk
                  ? `All ${sightingIds.length} selected detections will be assigned to the same person.`
                  : "Assign an identity so future appearances are recognised automatically.")}
          </DialogDescription>
        </DialogHeader>

        {/* Single sighting preview */}
        {!isBulk && previewSighting?.snapshot_url && (
          <div className="flex justify-center">
            <img
              src={previewSighting.snapshot_url}
              alt="Detected face"
              className="h-32 w-32 rounded-lg object-cover border-2 border-border shadow"
            />
          </div>
        )}

        {/* Bulk preview strip */}
        {isBulk && (
          <div className="flex gap-1.5 overflow-x-auto pb-1">
            {sightingIds.slice(0, 8).map((id) => (
              <div key={id} className="shrink-0 h-14 w-14 rounded bg-muted flex items-center justify-center text-xs text-muted-foreground border">
                #{id}
              </div>
            ))}
            {sightingIds.length > 8 && (
              <div className="shrink-0 h-14 w-14 rounded bg-muted flex items-center justify-center text-xs text-muted-foreground border">
                +{sightingIds.length - 8}
              </div>
            )}
          </div>
        )}

        {/* Mode toggle */}
        <div className="flex gap-2 flex-wrap">
          <Button variant={mode === "select" ? "default" : "outline"} size="sm" className="flex-1" onClick={() => setMode("select")}>
            <UserCheck className="h-3.5 w-3.5 mr-1.5" />Existing Person
          </Button>
          <Button variant={mode === "new" ? "default" : "outline"} size="sm" className="flex-1" onClick={() => setMode("new")}>
            <Plus className="h-3.5 w-3.5 mr-1.5" />New Person
          </Button>
          {isCorrection && (
            <Button variant={mode === "unknown" ? "destructive" : "outline"} size="sm" className="flex-1" onClick={() => setMode("unknown")}>
              <UserX className="h-3.5 w-3.5 mr-1.5" />Mark Unknown
            </Button>
          )}
        </div>

        {mode === "select" ? (
          <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
            {knownVisitors.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No known visitors yet. Switch to "New Person".
              </p>
            ) : (
              knownVisitors.map((v) => (
                <button
                  key={v.id}
                  onClick={() => setSelectedId(v.id)}
                  className={`w-full flex items-center gap-3 p-2.5 rounded-lg border text-left transition-colors ${
                    selectedId === v.id
                      ? "border-primary bg-primary/10"
                      : "border-border hover:bg-muted"
                  }`}
                >
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-bold text-primary shrink-0">
                    {v.name[0].toUpperCase()}
                  </div>
                  <span className="text-sm font-medium">{v.name}</span>
                </button>
              ))
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium mb-1 block">Full name</label>
              <Input
                placeholder="e.g. John Smith"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSave()}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">
                Reference photo{" "}
                <span className="text-muted-foreground font-normal">(optional — improves recognition)</span>
              </label>
              <Input type="file" accept="image/*" onChange={(e) => setNewPhoto(e.target.files?.[0] ?? null)} />
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button
            variant={mode === "unknown" ? "destructive" : "default"}
            onClick={handleSave}
            disabled={
              saving ||
              (mode === "select" && selectedId === null) ||
              (mode === "new" && !newName.trim())
            }
          >
            {saving
              ? "Saving…"
              : mode === "unknown"
              ? "Mark as Unknown"
              : isBulk
              ? `Identify ${sightingIds.length} Detections`
              : isCorrection
              ? "Update Identity"
              : "Confirm"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Add Visitor Dialog ────────────────────────────────────────────────────────

function AddVisitorDialog({
  open, onClose, onAdded,
}: { open: boolean; onClose: () => void; onAdded: () => void }) {
  const [name, setName] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      const res = await api.addVisitor(name.trim(), photo ?? undefined);
      if (res.id) {
        toast.success(`${name.trim()} added as a known visitor`);
        setName(""); setPhoto(null);
        onAdded(); onClose();
      } else {
        toast.error(res.detail ?? "Failed to add visitor");
      }
    } catch {
      toast.error("An error occurred");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Add Known Visitor</DialogTitle>
          <DialogDescription>Register a person so the system can recognise them in future detections.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium mb-1 block">Full name</label>
            <Input placeholder="e.g. Jane Doe" value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleSave()} />
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">Reference photo <span className="text-muted-foreground font-normal">(optional)</span></label>
            <Input type="file" accept="image/*" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving || !name.trim()}>
            {saving ? "Adding…" : "Add Visitor"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Sighting Card ─────────────────────────────────────────────────────────────

interface SightingCardProps {
  sighting: Sighting;
  selected: boolean;
  selectionMode: boolean;
  onToggleSelect: (id: number) => void;
  onName: (s: Sighting) => void;
  onDelete: (id: number) => void;
  onImageClick: (img: LightboxImage) => void;
}

function SightingCard({ sighting, selected, selectionMode, onToggleSelect, onName, onDelete, onImageClick }: SightingCardProps) {
  const { date, time } = formatDateTime(sighting.timestamp);
  const isKnown = !!sighting.visitor_name;

  return (
    <Card
      className={`cursor-pointer transition-all duration-150 ${
        selected
          ? "ring-2 ring-primary shadow-md"
          : "hover:shadow-md hover:ring-1 hover:ring-border"
      }`}
      onClick={() => onToggleSelect(sighting.id)}
    >
      <CardContent className="p-3 flex gap-3">
        {/* Snapshot / placeholder — click to enlarge */}
        <div className="relative shrink-0 group">
          {sighting.snapshot_url ? (
            <>
              <img
                src={sighting.snapshot_url}
                alt="Face snapshot"
                className="h-20 w-20 rounded-md object-contain border border-border bg-muted cursor-zoom-in"
                onClick={(e) => {
                  e.stopPropagation();
                  onImageClick({
                    src: sighting.snapshot_url!,
                    alt: sighting.visitor_name ?? "Unknown",
                    caption: `${sighting.visitor_name ?? "Unknown"} · ${sighting.camera_name} · ${date} ${time}`,
                    sightingId: sighting.id,
                  });
                }}
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                }}
              />
              {/* Zoom hint overlay */}
              <div
                className="absolute inset-0 rounded-md bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100 cursor-zoom-in"
                onClick={(e) => {
                  e.stopPropagation();
                  onImageClick({
                    src: sighting.snapshot_url!,
                    alt: sighting.visitor_name ?? "Unknown",
                    caption: `${sighting.visitor_name ?? "Unknown"} · ${sighting.camera_name} · ${date} ${time}`,
                    sightingId: sighting.id,
                  });
                }}
              >
                <ZoomIn className="h-5 w-5 text-white drop-shadow" />
              </div>
            </>
          ) : (
            <div className="h-20 w-20 rounded-md bg-muted border border-border flex items-center justify-center">
              <Camera className="h-6 w-6 text-muted-foreground/40" />
            </div>
          )}
          {/* Selection indicator */}
          <div className="absolute -top-1.5 -left-1.5">
            {selected
              ? <CheckSquare className="h-4 w-4 text-primary bg-background rounded" />
              : selectionMode
              ? <Square className="h-4 w-4 text-muted-foreground bg-background rounded" />
              : null}
          </div>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0 flex flex-col gap-1">
          <div className="flex items-start justify-between gap-1">
            <Badge variant={isKnown ? "default" : "secondary"} className="text-xs shrink-0">
              {isKnown ? <UserCheck className="h-3 w-3 mr-1" /> : <UserX className="h-3 w-3 mr-1" />}
              {sighting.visitor_name ?? "Unknown"}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground flex items-center gap-1 truncate">
            <Camera className="h-3 w-3 shrink-0" />
            {sighting.camera_name}
          </p>
          <p className="text-xs text-muted-foreground flex items-center gap-1">
            <Calendar className="h-3 w-3 shrink-0" />{date}
          </p>
          <p className="text-xs text-muted-foreground flex items-center gap-1">
            <Clock className="h-3 w-3 shrink-0" />{time}
          </p>
          {/* Action buttons */}
          <div className="flex gap-1.5 mt-auto pt-1" onClick={(e) => e.stopPropagation()}>
            <Button
              size="sm"
              variant={isKnown ? "ghost" : "outline"}
              className="h-6 text-xs px-2"
              onClick={() => onName(sighting)}
            >
              <Tag className="h-3 w-3 mr-1" />{isKnown ? "Rename" : "Name"}
            </Button>
            <Button size="sm" variant="ghost" className="h-6 text-xs px-2 text-destructive hover:text-destructive" onClick={() => onDelete(sighting.id)}>
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Active Filter Banner ─────────────────────────────────────────────────────

function ActiveFilterBanner({
  dateFilter, hourFilter, onClear,
}: { dateFilter: string | null; hourFilter: string | null; onClear: () => void }) {
  if (!dateFilter && !hourFilter) return null;

  const parts: string[] = [];
  if (dateFilter) {
    const label = dateFilter === toIsoDate(new Date()) ? "today" : dateFilter;
    parts.push(`Date: ${label}`);
  }
  if (hourFilter) parts.push(`Hour: ${hourFilter}:00`);

  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary/10 border border-primary/20 text-sm">
      <FilterIcon className="h-3.5 w-3.5 text-primary shrink-0" />
      <span className="text-primary font-medium">Filtered — {parts.join(", ")}</span>
      <Button variant="ghost" size="sm" className="h-5 px-1.5 ml-auto text-xs" onClick={onClear}>
        <X className="h-3 w-3 mr-0.5" />Clear
      </Button>
    </div>
  );
}

// ─── Main History Component ───────────────────────────────────────────────────

const History = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  // ── State ─────────────────────────────────────────────────────────────────
  const [sightings, setSightings] = useState<Sighting[]>([]);
  const [knownVisitors, setKnownVisitors] = useState<KnownVisitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>("all");
  const [cameraFilter, setCameraFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  // URL-driven filters (from dashboard drill-down)
  const [dateFilter, setDateFilter] = useState<string | null>(null);   // "YYYY-MM-DD"
  const [hourFilter, setHourFilter] = useState<string | null>(null);   // "14" (zero-padded)

  // Single-item dialogs
  const [namingSighting, setNamingSighting] = useState<Sighting | null>(null);
  const [showAddVisitor, setShowAddVisitor] = useState(false);

  // Multi-select state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [showBulkNameDialog, setShowBulkNameDialog] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);

  // Lightbox state
  const [lightbox, setLightbox] = useState<LightboxImage | null>(null);

  // ── Read URL params on mount ──────────────────────────────────────────────
  useEffect(() => {
    const status = searchParams.get("status");   // "unknown" | "known" | null
    const date   = searchParams.get("date");     // "today" | "YYYY-MM-DD" | null
    const hour   = searchParams.get("hour");     // "14" | null

    if (status === "unknown") setFilter("unknown");
    else if (status === "known") setFilter("known");

    if (date === "today") {
      setDateFilter(toIsoDate(new Date()));
    } else if (date) {
      setDateFilter(date);
    }

    if (hour) setHourFilter(hour.padStart(2, "0"));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // run once on mount

  // ── Data loading ──────────────────────────────────────────────────────────
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [sightingsRes, visitorsRes] = await Promise.all([
        api.getAllSightings(500),
        api.getVisitors(),
      ]);
      setSightings(sightingsRes.sightings ?? []);
      setKnownVisitors(visitorsRes.visitors ?? []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // ── Filtering ─────────────────────────────────────────────────────────────
  const cameraNames = useMemo(() => {
    const names = Array.from(new Set(sightings.map((s) => s.camera_name).filter(Boolean)));
    return names.sort();
  }, [sightings]);

  const filtered = useMemo(() => sightings.filter((s) => {
    const isKnown = !!s.visitor_name;
    if (filter === "known" && !isKnown) return false;
    if (filter === "unknown" && isKnown) return false;
    if (cameraFilter !== "all" && s.camera_name !== cameraFilter) return false;

    // Date filter
    if (dateFilter && s.timestamp) {
      const sDate = s.timestamp.slice(0, 10); // "YYYY-MM-DD"
      if (sDate !== dateFilter) return false;
    }

    // Hour filter (only meaningful when date is also set)
    if (hourFilter && s.timestamp) {
      const sHour = s.timestamp.slice(11, 13); // "HH"
      if (sHour !== hourFilter) return false;
    }

    if (search) {
      const q = search.toLowerCase();
      if (
        !(s.visitor_name ?? "unknown").toLowerCase().includes(q) &&
        !(s.camera_name ?? "").toLowerCase().includes(q)
      ) return false;
    }
    return true;
  }), [sightings, filter, cameraFilter, dateFilter, hourFilter, search]);

  const knownCount = sightings.filter((s) => !!s.visitor_name).length;
  const unknownCount = sightings.filter((s) => !s.visitor_name).length;

  // ── Selection helpers ─────────────────────────────────────────────────────
  const selectionMode = selectedIds.size > 0;
  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };
  const selectAll = () => setSelectedIds(new Set(filtered.map((s) => s.id)));
  const clearSelection = () => setSelectedIds(new Set());

  const selectedUnknownIds = filtered
    .filter((s) => selectedIds.has(s.id) && !s.visitor_name)
    .map((s) => s.id);

  const clearUrlFilters = () => {
    setDateFilter(null);
    setHourFilter(null);
    setSearchParams({});
  };

  // ── Actions ───────────────────────────────────────────────────────────────
  const handleNamed = (ids: number[], visitorName: string) => {
    setSightings((prev) =>
      prev.map((s) => ids.includes(s.id) ? { ...s, visitor_name: visitorName } : s)
    );
    clearSelection();
  };

  const handleDelete = async (id: number) => {
    await api.deleteSighting(id);
    setSightings((prev) => prev.filter((s) => s.id !== id));
    setSelectedIds((prev) => { const n = new Set(prev); n.delete(id); return n; });
    toast.success("Detection deleted");
  };

  const handleBulkDelete = async () => {
    const ids = Array.from(selectedIds);
    setBulkDeleting(true);
    try {
      const res = await api.bulkDeleteSightings(ids);
      setSightings((prev) => prev.filter((s) => !ids.includes(s.id)));
      clearSelection();
      toast.success(`${res.deleted ?? ids.length} detection${ids.length !== 1 ? "s" : ""} deleted`);
    } catch {
      toast.error("Bulk delete failed");
    } finally {
      setBulkDeleting(false);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <main className="container py-6 space-y-5">

      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Detection History</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            All face detections from your cameras — click a card to select, or use "Name" to identify someone
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button size="sm" onClick={() => setShowAddVisitor(true)}>
            <Plus className="h-3.5 w-3.5 mr-1.5" />Add Known Visitor
          </Button>
        </div>
      </div>

      {/* Active URL filter banner */}
      <ActiveFilterBanner
        dateFilter={dateFilter}
        hourFilter={hourFilter}
        onClear={clearUrlFilters}
      />

      {/* Search + filter bar */}
      <div className="flex flex-col sm:flex-row gap-3 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by name or camera…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        {/* Known / Unknown filter */}
        <div className="flex gap-2">
          {(["all", "known", "unknown"] as Filter[]).map((f) => (
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
        {/* Camera filter — only shown when more than one camera exists */}
        {cameraNames.length > 1 && (
          <div className="flex gap-2 flex-wrap">
            <Button
              variant={cameraFilter === "all" ? "secondary" : "outline"}
              size="sm"
              onClick={() => setCameraFilter("all")}
            >
              <Video className="h-3.5 w-3.5 mr-1" />
              All Cameras
            </Button>
            {cameraNames.map((cam) => (
              <Button
                key={cam}
                variant={cameraFilter === cam ? "secondary" : "outline"}
                size="sm"
                onClick={() => setCameraFilter(cameraFilter === cam ? "all" : cam)}
                className="capitalize"
              >
                <Camera className="h-3.5 w-3.5 mr-1" />
                {cam.replace(/_/g, " ")}
              </Button>
            ))}
          </div>
        )}
      </div>

      {/* Summary counts */}
      <div className="flex gap-4 text-sm text-muted-foreground">
        <span><strong className="text-foreground">{knownCount}</strong> identified</span>
        <span><strong className="text-amber-500">{unknownCount}</strong> unknown</span>
        <span><strong className="text-foreground">{sightings.length}</strong> total</span>
        {(dateFilter || hourFilter) && (
          <span className="text-primary font-medium">
            — showing <strong>{filtered.length}</strong> matching filter
          </span>
        )}
      </div>

      {/* ── Bulk action toolbar (appears when items are selected) ── */}
      {selectionMode && (
        <div className="sticky top-16 z-40 flex items-center gap-3 rounded-lg border bg-card/95 backdrop-blur px-4 py-2.5 shadow-lg">
          <div className="flex items-center gap-2 text-sm font-medium">
            <CheckSquare className="h-4 w-4 text-primary" />
            <span>{selectedIds.size} selected</span>
          </div>
          <div className="flex gap-2 ml-auto flex-wrap">
            <Button variant="outline" size="sm" onClick={selectAll} className="text-xs">
              <CheckCheck className="h-3.5 w-3.5 mr-1" />Select All ({filtered.length})
            </Button>
            {selectedUnknownIds.length > 0 && (
              <Button size="sm" variant="outline" className="text-xs" onClick={() => setShowBulkNameDialog(true)}>
                <Users className="h-3.5 w-3.5 mr-1" />
                Name {selectedUnknownIds.length} Unknown
              </Button>
            )}
            <Button
              size="sm"
              variant="destructive"
              className="text-xs"
              onClick={handleBulkDelete}
              disabled={bulkDeleting}
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" />
              {bulkDeleting ? "Deleting…" : `Delete ${selectedIds.size}`}
            </Button>
            <Button variant="ghost" size="sm" onClick={clearSelection} className="text-xs">
              <X className="h-3.5 w-3.5 mr-1" />Clear
            </Button>
          </div>
        </div>
      )}

      {/* ── Grid ── */}
      {loading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-28 rounded-lg bg-muted animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 space-y-3">
          <Camera className="h-14 w-14 mx-auto text-muted-foreground/30" />
          <p className="text-lg font-medium">No detections found</p>
          <p className="text-sm text-muted-foreground">
            {sightings.length === 0
              ? "The detection service hasn't captured any faces yet. Make sure it's running and the camera is in view."
              : (dateFilter || hourFilter)
              ? "No detections match the selected time filter. Try clearing the filter."
              : search
              ? "No results match your search."
              : `No ${filter} detections to show.`}
          </p>
          {(dateFilter || hourFilter) && (
            <Button variant="outline" size="sm" onClick={clearUrlFilters}>
              <X className="h-3.5 w-3.5 mr-1" />Clear Filter
            </Button>
          )}
          {sightings.length === 0 && (
            <p className="text-xs text-muted-foreground">
              Check Settings → Service tab to confirm the detection service is active.
            </p>
          )}
        </div>
      ) : (
        <>
          {/* Select-all hint when nothing is selected */}
          {!selectionMode && (
            <p className="text-xs text-muted-foreground -mt-2">
              Tip: click any card to select it, then use the bulk toolbar to name or delete multiple detections at once.
            </p>
          )}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((s) => (
              <SightingCard
                key={s.id}
                sighting={s}
                selected={selectedIds.has(s.id)}
                selectionMode={selectionMode}
                onToggleSelect={toggleSelect}
                onName={setNamingSighting}
                onDelete={handleDelete}
                onImageClick={setLightbox}
              />
            ))}
          </div>
        </>
      )}

      {/* Single-item Name dialog */}
      {namingSighting && (
        <NameDialog
          sightingIds={[namingSighting.id]}
          previewSighting={namingSighting}
          knownVisitors={knownVisitors}
          isCorrection={!!namingSighting.visitor_name}
          onClose={() => setNamingSighting(null)}
          onNamed={handleNamed}
        />
      )}

      {/* Bulk Name dialog */}
      {showBulkNameDialog && (
        <NameDialog
          sightingIds={selectedUnknownIds}
          knownVisitors={knownVisitors}
          onClose={() => setShowBulkNameDialog(false)}
          onNamed={handleNamed}
        />
      )}

      {/* Add Visitor dialog */}
      <AddVisitorDialog
        open={showAddVisitor}
        onClose={() => setShowAddVisitor(false)}
        onAdded={loadData}
      />

      {/* Image lightbox */}
      <ImageLightbox
        image={lightbox}
        onClose={() => setLightbox(null)}
        onChangeName={(sightingId) => {
          const s = sightings.find((x) => x.id === sightingId);
          if (s) setNamingSighting(s);
        }}
      />
    </main>
  );
};

export default History;
